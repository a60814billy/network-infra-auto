import os
import asyncio
from collections import deque
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
import threading

from app.config import UPLOAD_DIR
from app.models.ticket import Ticket, TicketStatus

# 機器管理
_MACHINES: Dict[str, bool] = {
    "machine_1": True,  # True = 空閒, False = 忙碌
    "machine_2": True,
    "machine_3": True,
}

# 在記憶體中的 ticket 佇列和狀態追蹤
_TICKET_QUEUE: deque = deque()  # 等待中的 tickets
_RUNNING_TICKETS: Dict[str, Ticket] = {}  # 執行中的 tickets
_TICKETS_DB: Dict[str, Ticket] = {}  # 所有 tickets 的狀態

# 票據儲存路徑
TICKET_DIR = Path("data/tickets")


async def run_task(ticket_id: str, vendor: str, module: str, config_path: str) -> bool:
    """
    模擬真實的任務執行 - 這是會派送到後端機器的任務
    這個函數會在背景執行，不會阻塞 request 回應
    """
    try:
        print(f"[run_task] Starting task {ticket_id} for {vendor}/{module}")

        # 模擬任務處理時間（實際上這裡會是真正的業務邏輯）
        await asyncio.sleep(10)  # 模擬 10 秒的處理時間

        # 模擬 80% 成功率
        import random
        success = random.random() < 0.8

        if success:
            result_data = f"Task {ticket_id} completed successfully on {vendor}/{module}"
            print(f"[run_task] Task {ticket_id} completed successfully")
        else:
            result_data = f"Task {ticket_id} failed during processing"
            print(f"[run_task] Task {ticket_id} failed")

        # 更新 ticket 狀態
        complete_ticket(ticket_id, result_data, success)

        return success

    except Exception as e:
        print(f"[run_task] Error in task {ticket_id}: {str(e)}")
        complete_ticket(ticket_id, f"Error: {str(e)}", False)
        return False


def start_background_task(ticket_id: str, vendor: str, module: str, config_path: str):
    """
    在背景啟動任務，不會阻塞主線程
    """
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                run_task(ticket_id, vendor, module, config_path))
        finally:
            loop.close()

    thread = threading.Thread(target=run_in_thread, daemon=True)
    thread.start()
    print(f"[start_background_task] Started background task for {ticket_id}")


def save_ticket_to_file(ticket: Ticket, data: bytes) -> None:
    """將 ticket 檔案儲存到 data/tickets/{vendor}/{module}/{ticket_id}.txt"""
    ticket_dir = UPLOAD_DIR / ticket.vendor / ticket.module
    ticket_dir.mkdir(parents=True, exist_ok=True)

    with open(ticket.testing_config_path, "wb") as f:
        f.write(data)


def save_ticket(ticket: Ticket, data: bytes) -> None:
    """儲存 ticket 並加入佇列"""
    save_ticket_to_file(ticket, data)

    _TICKETS_DB[ticket.ticket_id] = ticket
    _TICKET_QUEUE.append(ticket.ticket_id)


def get_ticket(ticket_id: str) -> Optional[Ticket]:
    """取得 ticket 狀態"""
    return _TICKETS_DB.get(ticket_id)


def delete_ticket(ticket_id: str) -> None:
    """刪除 ticket 和相關檔案"""
    ticket = _TICKETS_DB.get(ticket_id)
    print(f"[delete_ticket] Deleting ticket {ticket_id}")
    if ticket:
        # 刪除檔案
        if os.path.exists(ticket.testing_config_path):
            os.remove(ticket.testing_config_path)

        # 從記憶體中移除
        _TICKETS_DB.pop(ticket_id, None)
        _RUNNING_TICKETS.pop(ticket_id, None)

        # 從佇列中移除（如果存在）
        try:
            _TICKET_QUEUE.remove(ticket_id)
        except ValueError:
            pass


def get_available_machines() -> List[str]:
    """取得空閒的機器列表"""
    return [machine_id for machine_id, is_free in _MACHINES.items() if is_free]


def allocate_machine(machine_id: str) -> bool:
    """分配機器（設為忙碌）"""
    if machine_id in _MACHINES and _MACHINES[machine_id]:
        _MACHINES[machine_id] = False
        return True
    return False


def release_machine(machine_id: str) -> None:
    """釋放機器（設為空閒）"""
    if machine_id in _MACHINES:
        _MACHINES[machine_id] = True


def process_queue() -> List[str]:
    """
    處理佇列：將等待中的任務分配給空閒機器並啟動背景任務
    這個函數會立即回傳，不會等待任務完成
    """
    processed_tickets = []
    available_machines = get_available_machines()

    while _TICKET_QUEUE and available_machines:
        ticket_id = _TICKET_QUEUE.popleft()
        machine_id = available_machines.pop(0)

        ticket = _TICKETS_DB.get(ticket_id)
        if ticket:
            # 分配機器並更新狀態
            allocate_machine(machine_id)
            ticket.status = TicketStatus.running
            ticket.started_at = datetime.utcnow()
            ticket.machine_id = machine_id

            _RUNNING_TICKETS[ticket_id] = ticket
            processed_tickets.append(ticket_id)

            # 啟動背景任務（非阻塞）
            start_background_task(
                ticket_id,
                ticket.vendor,
                ticket.module,
                ticket.testing_config_path
            )

            print(
                f"[process_queue] Started background task {ticket_id} on {machine_id}")

    return processed_tickets


def complete_ticket(ticket_id: str, result_data: Optional[str] = None, success: bool = True) -> bool:
    """完成 ticket 處理"""
    ticket = _RUNNING_TICKETS.get(ticket_id)
    if not ticket:
        # 也檢查一般 tickets DB 中的 ticket
        ticket = _TICKETS_DB.get(ticket_id)
        if not ticket:
            return False

    # 釋放機器
    if ticket.machine_id:
        release_machine(ticket.machine_id)

    # 更新狀態
    ticket.status = TicketStatus.completed if success else TicketStatus.failed
    ticket.completed_at = datetime.utcnow()
    ticket.result_data = result_data

    # 從執行中移除
    _RUNNING_TICKETS.pop(ticket_id, None)

    print(
        f"[complete_ticket] Ticket {ticket_id} marked as {'completed' if success else 'failed'}")

    return True


def get_queue_status() -> Dict:
    """取得佇列和機器狀態"""
    return {
        "queued_count": len(_TICKET_QUEUE),
        "running_count": len(_RUNNING_TICKETS),
        "machines": _MACHINES.copy(),
        "queue_position": {
            ticket_id: idx + 1
            for idx, ticket_id in enumerate(_TICKET_QUEUE)
        }
    }


def is_task_completed(ticket_id: str) -> bool:
    """
    檢查任務是否已完成
    如果任務還在執行中，回傳 False
    如果任務已完成（成功或失敗），回傳 True
    """
    ticket = get_ticket(ticket_id)
    if not ticket:
        return False

    return ticket.status in [TicketStatus.completed, TicketStatus.failed]
