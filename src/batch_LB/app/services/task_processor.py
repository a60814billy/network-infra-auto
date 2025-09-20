import asyncio
import threading
from typing import Callable, Optional
from app.models.ticket import Ticket

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

    def start_background_task(self, ticket: Ticket):
        """
        在背景啟動任務
        
        Args:
            ticket_id: 票據ID
            vendor: 廠商
            model: 模組
            config_path: 配置檔案路徑
        """
        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self._execute_task(ticket))
            finally:
                loop.close()

        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
        print(f"[TaskProcessor] Started background task for {ticket.id}")