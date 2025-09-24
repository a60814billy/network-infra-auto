import os
import yaml
from typing import Dict, Optional, Deque
from collections import deque
from datetime import datetime
from uuid import uuid4
from pathlib import Path

from app.models.ticket import Ticket, TicketStatus
from app.services.task_processor import TaskProcessor
from app.services.machine_manager import MachineManager
from app.utils import load_device


class TicketManager:
    """管理票據的類別 - 負責票據的CRUD操作和處理邏輯"""

    def __init__(self):
        """
        初始化 TicketManager
        """
        # 載入配置
        self.CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

        self.TICKET_PATH = Path(yaml.safe_load(open(self.CONFIG_PATH, 'r'))["TICKET_PATH"])
        
        self._ticket_queue: Deque[Ticket] = deque()
        
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
        重新載入所有在檔案中未處理的票據
        """
        ticket_list = list[Ticket]()
        valid_machines = load_device()
        if not valid_machines:
            print("[TicketManager] No valid machines found in config, skipping ticket reload.")
            return ticket_list
        for vendor, models in valid_machines.items():
            if not isinstance(models, dict):
                continue
            for model, versions in models.items():
                if not isinstance(versions, dict):
                    continue
                for version in versions.keys():
                    ticket_folder = self.TICKET_PATH / vendor / model / version
                    for ticket_file in ticket_folder.glob("*.txt"):
                        print(f"[TicketManager] Reloading ticket from {ticket_file}")
                        ticket_id = ticket_file.stem
                        with open(ticket_file, "r") as f:
                            ticket = Ticket(
                                id=ticket_id,
                                version=version,
                                vendor=vendor,
                                model=model,
                                testing_config_path=f"{self.TICKET_PATH}/{vendor}/{model}/{version}/{ticket_id}.txt",
                                status=TicketStatus.queued,
                            )
                        self._tickets_db[ticket_id] = ticket
                        ticket_list.append(ticket)
        return ticket_list
                        
    # ===== 票據 CRUD 操作 =====

    def _create_ticket(self, version: str, vendor: str, model: str, data: bytes) -> Ticket:
        """
        創建票據，寫入檔案，並加入票據資料庫
        
        Args:
            version: 版本
            vendor: 廠商
            model: 模組
            data: 檔案資料
        """
        id = str(uuid4())
        ticket = Ticket(
            id=id,
            version=version,
            vendor=vendor,
            model=model,
            testing_config_path=f"{self.TICKET_PATH}/{vendor}/{model}/{version}/{id}.txt",
            status=TicketStatus.queued,
        )

        # 儲存檔案和票據資料
        ticket_dir = self.TICKET_PATH / ticket.vendor / ticket.model / ticket.version
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
            ticket: 票據物件

        Returns:
            bool: 是否成功加入佇列
        """
        if not ticket:
            print(f"[TicketManager] Invalid ticket provided for enqueue")
            return False
        if ticket.status != TicketStatus.queued:
            print(f"[TicketManager] Ticket {ticket.id} is not in queued status")
            return False

        self._ticket_queue.append(ticket)
        print(f"[TicketManager] Enqueued ticket: {ticket.id}")
        return True

    def _update_ticket(self, ticket: Ticket, **kwargs) -> bool:
        """
        更新票據資訊
        
        Args:
            ticket: 票據物件
            **kwargs: 要更新的欄位
            
        Returns:
            bool: 是否更新成功
        """
        if not ticket:
            print(f"[TicketManager] Invalid ticket provided for update")
            return False
        
        for key, value in kwargs.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        
        return True
    
    def _complete_ticket(self, ticket: Ticket, result_data: Optional[str] = None, success: bool = True) -> None:
        """
        完成票據處理
        
        Args:
            ticket: 票據物件
            result_data: 結果資料
            success: 是否成功
        """
        if not ticket:
            print(f"[TicketManager] Ticket {ticket.id} not found for completion")
            return
        
        if not ticket.machine:
            print(f"[TicketManager] Ticket {ticket.id} has no machine allocated")
            return
        
        # 確認機器確實被分配給這個票據
        if not self.machine_manager.validate_ticket_machine(ticket.id, ticket.machine.serial):
            print(f"[TicketManager] Machine {ticket.machine.serial} is not allocated to ticket {ticket.id}")
            return

        # 釋放機器
        self.machine_manager.release_machine(ticket.machine)

        # 更新狀態
        status = TicketStatus.completed if success else TicketStatus.failed
        self._update_ticket(
            ticket=ticket,
            status=status,
            completed_at=datetime.utcnow(),
            result_data=result_data
        )

        print(f"curl \"http://127.0.0.1:8000/result/{ticket.id}\" | jq .")
        
        self._consume_ticket()  # 嘗試處理下一個票據
    
    # ===== 佇列處理邏輯 =====
    
    def _consume_ticket(self) -> bool:
        """
        處理佇列中的票據
        """
        if not len(self._ticket_queue):
            # print(f"[TicketManager] No tickets in the queue to process.")
            return False
        
        # 使用機器管理器分配機器
        ticket = self._ticket_queue.popleft()
        allocated_machine = self.machine_manager.allocate_machine(ticket.id, ticket.vendor, ticket.model, ticket.version)
        
        if not allocated_machine:
            # 如果沒有可用機器，將票據放回佇列前端
            self._ticket_queue.appendleft(ticket)
            # print(f"[TicketManager] No available machines to process ticket {ticket.id}")
            return False
        
        # 更新票據狀態
        self._update_ticket(
            ticket=ticket,
            status=TicketStatus.running,
            started_at=datetime.utcnow(),
            machine=allocated_machine
        )

        # 使用 TaskProcessor 啟動背景任務
        self.task_processor.start_background_task(ticket)
        return True
    
    # ===== 公開方法 =====
    def get_ticket(self, id: str) -> Optional[Ticket]:
        """
        取得票據
        
        Args:
            id: 票據ID
            
        Returns:
            Optional[Ticket]: 票據物件，如果不存在則返回 None
        """
        return self._tickets_db.get(id)
    
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
    
    def process_ticket(self, version: str, vendor: str, model: str, data: bytes) -> Optional[Ticket]:
        ticket = self._create_ticket(version, vendor, model, data)
        
        if not self._enqueue_ticket(ticket):
            return None
        
        self._consume_ticket()
        return ticket
    
    # ===== 狀態查詢 =====
    
    def get_queue_status(self) -> Dict:
        """
        取得佇列和機器狀態
        
        Returns:
            Dict: 包含佇列狀態的字典
        """
        queue_tickets = list(self._ticket_queue)
        
        return {
            "queued_count": len(self._ticket_queue),
            "running_count": self.machine_manager.get_running_count(),
            "machines": self.machine_manager.get_machine_status(),
            "queue_position": {
                ticket.id: idx + 1
                for idx, ticket in enumerate(queue_tickets)
            }
        }