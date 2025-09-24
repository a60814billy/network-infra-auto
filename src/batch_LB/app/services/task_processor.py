import asyncio
import threading
from typing import Callable, Optional

from app.models.ticket import Ticket
from app.models.machine import Machine

class TaskProcessor:
    def __init__(self, completion_callback: Callable[[Ticket, Optional[str], bool], None]):
        """
        初始化 TaskProcessor
        
        Args:
            completion_callback: 任務完成時的回調函數，參數為 (ticket, result_data, success)
        """
        self.completion_callback = completion_callback

    async def _execute_task(self, ticket: Ticket) -> None:
        """
        執行任務的核心邏輯
        
        Args:
            ticket: 票據物件

        """
        try:
            machine = ticket.machine
            if not machine:
                raise ValueError(f"Ticket {ticket.id} has no machine allocated")
            reset_success = await self.reset_machine(machine)  # 重置機器
            if not reset_success:
                raise RuntimeError(f"Failed to reset machine {machine.serial} for ticket {ticket.id}")
            # 模擬任務處理時間（實際上這裡會是真正的業務邏輯）
            await asyncio.sleep(5)  # 模擬耗時任務
            success = True
            result_data = f"Processed {ticket.vendor} - {ticket.model}"
            # 通知 TicketManager 任務完成
            self.completion_callback(ticket, result_data, success)

        except Exception as e:
            print(f"[TaskProcessor] Error in task {ticket}: {str(e)}")
            # 通知 TicketManager 任務失敗
            self.completion_callback(ticket, f"Error: {str(e)}", False)


    async def reset_machine(self, machine: Machine) -> bool:
        """
        將機器重置為初始狀態

        Args:
            machine: 機器物件
        """
        # Open connection to the machine
        # add lock for thread safety if needed
        await asyncio.sleep(1)  # Simulate reset delay
        
        print(f"[TaskProcessor] Machine {machine.serial} reset complete.")
        return True

    def start_background_task(self, ticket: Ticket):
        """在背景啟動任務"""
        def run_task():
            asyncio.run(self._execute_task(ticket))
        
        threading.Thread(target=run_task, daemon=True).start()
        print(f"[TaskProcessor] Started background task for {ticket.id}")