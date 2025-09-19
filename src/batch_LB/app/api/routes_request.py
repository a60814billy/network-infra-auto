from fastapi import APIRouter, HTTPException, UploadFile, File, Request

from app.models.ticket import TicketStatus
from app.config import MAX_UPLOAD_SIZE, VALID_MACHINES

router = APIRouter()

@router.post("/{version}/{vendor}/{module}", summary="Create request (file upload)")
async def create_request(version: str, vendor: str, module: str, request: Request, file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="file is empty")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413, detail=f"file too large (>{MAX_UPLOAD_SIZE} bytes)")

    if vendor not in VALID_MACHINES or module not in VALID_MACHINES[vendor]:
        raise HTTPException(
            status_code=400, detail=f"Unsupported vendor/module combination: {vendor}/{module}")
    
    ticket_manager = request.app.state.ticket_manager
    # 創建票據並加入佇列
    ticket = ticket_manager.create_ticket(version, vendor, module, data)
    ticket_manager.enqueue_ticket(ticket)

    # 嘗試處理佇列（分配空閒機器）
    is_processed = ticket_manager.consume_ticket()
    if is_processed:
        ticket.status = TicketStatus.running

    return {
        "id": ticket.id,
        "status": ticket.status,
        "message": f"Request accepted and {'started processing' if ticket.status == TicketStatus.running else 'queued'}."
    }
