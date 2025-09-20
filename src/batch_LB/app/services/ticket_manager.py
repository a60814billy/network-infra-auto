import os
from typing import Dict, Optional, Deque
from collections import deque
from datetime import datetime
from uuid import uuid4

from app.config import UPLOAD_DIR, VALID_MACHINES
from app.models.ticket import Ticket, TicketStatus
from app.services.task_processor import TaskProcessor
from app.services.machine_manager import MachineManager


class TicketManager:
    """管理票據的類別 - 負責票據的CRUD操作和處理邏輯"""

    def __init__(self):
        """
        初始化 TicketManager
        """
        self.ticket_queue: Deque[Ticket] = deque()
        
        # 在記憶體中的票據資料庫
        self._tickets_db: Dict[str, Ticket] = {}
        
        # 機器管理器
        self.machine_manager = MachineManager()
        
        # 初始化 TaskProcessor，傳入完成回調函數
        self.task_processor = TaskProcessor(completion_callback=self._complete_ticket)
        
        unprocess_tickets = self._reload_tickets()
        if not unprocess_tickets:
            return
        
        for ticket in unprocess_tickets:
            self._enqueue_ticket(ticket)
            self._consume_ticket()
        print(f"[TicketManager] Reloaded {len(unprocess_tickets)} unprocessed tickets from storage.")

    def _reload_tickets(self) -> list[Ticket]:
        """
        重新載入所有未處理的票據（queued 狀態）
        """
        ticket_list = list[Ticket]()
        for vendor in VALID_MACHINES:
            for module in VALID_MACHINES[vendor]:
                ticket_folder = UPLOAD_DIR / vendor / module
                for ticket_file in ticket_folder.glob("*.txt"):
                    print(f"[TicketManager] Reloading ticket from {ticket_file}")
                    ticket_id = ticket_file.stem
                    with open(ticket_file, "r") as f:
                        ticket = Ticket(
                            id=ticket_id,
                            version="v1",
                            vendor=vendor,
                            module=module,
                            testing_config_path=f"{UPLOAD_DIR}/{vendor}/{module}/{ticket_id}.txt",
                            status=TicketStatus.queued,
                        )
                    self._tickets_db[ticket_id] = ticket
                    ticket_list.append(ticket)
        return ticket_list
                        
    # ===== 票據 CRUD 操作 =====

    def _create_ticket(self, version: str, vendor: str, module: str, data: bytes) -> Ticket:
        """
        創建票據並加入佇列
        
        Args:
            vendor: 廠商
            module: 模組
            data: 檔案資料
        """
        id = str(uuid4())
        ticket = Ticket(
            id=id,
            version=version,
            vendor=vendor,
            module=module,
            testing_config_path=f"{UPLOAD_DIR}/{vendor}/{module}/{id}.txt",
            status=TicketStatus.queued,
        )

        # 儲存檔案和票據資料
        ticket_dir = UPLOAD_DIR / ticket.vendor / ticket.module
        ticket_dir.mkdir(parents=True, exist_ok=True)

        with open(ticket.testing_config_path, "wb") as f:
            f.write(data)
            
        self._tickets_db[id] = ticket
        
        print(f"[TicketManager] Created ticket: {ticket.id}")
        return ticket
    
    def _enqueue_ticket(self, ticket: Ticket) -> bool:
        """
        將票據加入佇列
        
        Args:
            id: 票據ID
            
        Returns:
            bool: 是否成功加入佇列
        """
        if not ticket:
            print(f"[TicketManager] Invalid ticket provided for enqueue")
            return False
        if ticket.status != TicketStatus.queued:
            print(f"[TicketManager] Ticket {ticket.id} is not in queued status")
            return False

        self.ticket_queue.append(ticket)
        print(f"[TicketManager] Enqueued ticket: {ticket.id}")
        return True
    
    def get_ticket(self, id: str) -> Optional[Ticket]:
        """
        取得票據
        
        Args:
            id: 票據ID
            
        Returns:
            Optional[Ticket]: 票據物件，如果不存在則返回 None
        """
        return self._tickets_db.get(id)
    
    def _update_ticket(self, id: str, **kwargs) -> bool:
        """
        更新票據資訊
        
        Args:
            id: 票據ID
            **kwargs: 要更新的欄位
            
        Returns:
            bool: 是否更新成功
        """
        ticket = self.get_ticket(id)
        if not ticket:
            return False
        
        for key, value in kwargs.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        
        return True
    
    def delete_ticket(self, id: str) -> None:
        """
        刪除票據和相關檔案
        
        Args:
            id: 票據ID
        """
        ticket = self.get_ticket(id)
        if not ticket:
            print(f"[TicketManager] Ticket {id} not found for deletion")
            return

        print(f"[TicketManager] Deleting ticket {id}")
        
        # 刪除檔案
        if os.path.exists(ticket.testing_config_path):
            os.remove(ticket.testing_config_path)

        # 從記憶體中移除
        self._tickets_db.pop(id, None)
    
    def _complete_ticket(self, id: str, result_data: Optional[str] = None, success: bool = True) -> None:
        """
        完成票據處理
        
        Args:
            id: 票據ID
            result_data: 結果資料
            success: 是否成功
        """
        ticket = self.get_ticket(id)
        if not ticket:
            print(f"[TicketManager] Ticket {id} not found in the database for completion")
            return
        
        # 檢查票據是否正在執行中
        if not ticket.machine_id:
            print(f"[TicketManager] Ticket {id} has no machine allocated")
            return
        
        # 確認機器確實被分配給這個票據
        if not self.machine_manager.validate_ticket_machine(id, ticket.machine_id):
            print(f"[TicketManager] Machine {ticket.machine_id} is not allocated to ticket {id}")
            return

        # 釋放機器
        self.machine_manager.release_machine(ticket.machine_id)

        # 更新狀態
        status = TicketStatus.completed if success else TicketStatus.failed
        self._update_ticket(
            id,
            status=status,
            completed_at=datetime.utcnow(),
            result_data=result_data
        )

        print(f"curl \"http://127.0.0.1:8000/result/{id}\" | jq .")
        
        self._consume_ticket()  # 嘗試處理下一個票據
    
    # ===== 佇列處理邏輯 =====
    
    def _consume_ticket(self) -> bool:
        """
        處理佇列中的票據
        """
        if not len(self.ticket_queue):
            print(f"[TicketManager] No tickets in the queue to process.")
            return False
        
        # 使用機器管理器分配機器
        ticket = self.ticket_queue.popleft()
        allocated_machine = self.machine_manager.allocate_machine(ticket.id)
        
        if not allocated_machine:
            # 如果沒有可用機器，將票據放回佇列前端
            self.ticket_queue.appendleft(ticket)
            print(f"[TicketManager] No available machines to process ticket {ticket.id}")
            return False
        
        # 更新票據狀態
        self._update_ticket(
            ticket.id,
            status=TicketStatus.running,
            started_at=datetime.utcnow(),
            machine_id=allocated_machine
        )

        # 使用 TaskProcessor 啟動背景任務
        self.task_processor.start_background_task(ticket)
        return True
    
    def process_ticket(self, version: str, vendor: str, module: str, data: bytes) -> Optional[Ticket]:
        ticket = self._create_ticket(version, vendor, module, data)
        
        if not self._enqueue_ticket(ticket):
            return None
        
        if not self._consume_ticket():
            return None
        return ticket
    
    # ===== 狀態查詢 =====
    
    def get_queue_status(self) -> Dict:
        """
        取得佇列和機器狀態
        
        Returns:
            Dict: 包含佇列狀態的字典
        """
        queue_tickets = list(self.ticket_queue)
        
        return {
            "queued_count": len(self.ticket_queue),
            "running_count": self.machine_manager.get_running_count(),
            "machines": self.machine_manager.get_machine_status(),
            "queue_position": {
                ticket.id: idx + 1
                for idx, ticket in enumerate(queue_tickets)
            }
        }