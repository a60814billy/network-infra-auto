from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

@router.get("/{id}")
def get_result(id: str, request: Request):
    """
    取得 ticket 狀態和結果
    如果任務還在執行中，立即回復 false (running 狀態)
    如果任務已完成，回復 true 和結果
    """
    ticket_manager = request.app.state.ticket_manager
    ticket = ticket_manager.get_ticket(id)
    if not ticket:
        return HTTPException(status_code=404, detail=f"Ticket {id} not found")

    # 取得佇列狀態
    queue_status = ticket_manager.get_queue_status()
    position = queue_status["queue_position"].get(id, 0)

    response = {
        "id": ticket.id,
        "status": ticket.status,
        "vendor": ticket.vendor,
        "model": ticket.model,
        "version": ticket.version,
        "enqueued_at": ticket.enqueued_at,
        "started_at": ticket.started_at,
        "completed_at": ticket.completed_at,
        "machine": {
            "serial": ticket.machine.serial,
            "ip": ticket.machine.ip,
            "port": ticket.machine.port
        } if ticket.machine else None,
        "completed": False,  # 預設為 False
    }

    if ticket.status == "queued":
        response["message"] = f"Ticket is in queue at position {position}"
        response["position"] = position
        response["completed"] = False

    elif ticket.status == "running":
        response["message"] = f"Ticket is running on {ticket.machine.serial if ticket.machine else 'unknown machine'}"
        response["completed"] = False  # 還在執行中，立即回復 False

    elif ticket.status == "completed":
        response["message"] = "Ticket completed successfully"
        response["result_data"] = ticket.result_data
        response["completed"] = True  # 任務完成，回復 True
        ticket_manager.delete_ticket(id)  # 自動刪除已完成的 ticket

    elif ticket.status == "failed":
        response["message"] = "Ticket processing failed"
        response["result_data"] = ticket.result_data
        response["completed"] = True  # 任務結束（雖然失敗），回復 True
        ticket_manager.delete_ticket(id)  # 自動刪除已完成的 ticket

    return response


@router.get("/")
def get_queue_info(request: Request):
    """取得整體佇列狀態"""
    ticket_manager = request.app.state.ticket_manager
    return ticket_manager.get_queue_status()
