from fastapi import APIRouter, HTTPException, UploadFile, File
from uuid import uuid4

from app.models.ticket import Ticket, TicketStatus
from app.services.queue import save_ticket, process_queue
from app.config import UPLOAD_DIR, MAX_UPLOAD_SIZE

router = APIRouter()


@router.post("/{version}/{vendor}/{module}", summary="Create request (file upload)")
async def create_request(version: str, vendor: str, module: str, file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="file is empty")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413, detail=f"file too large (>{MAX_UPLOAD_SIZE} bytes)")

    # Construct ticket_id
    ticket_id = str(uuid4())
    t = Ticket(
        ticket_id=ticket_id,
        version=version,
        vendor=vendor,
        module=module,
        testing_config_path=f"{UPLOAD_DIR}/{vendor}/{module}/{ticket_id}.txt",
        status=TicketStatus.queued,
    )

    # 儲存 ticket 並加入佇列
    save_ticket(t, data)

    # 嘗試處理佇列（分配空閒機器）
    processed = process_queue()
    if ticket_id in processed:
        t.status = TicketStatus.running

    return {
        "ticket_id": t.ticket_id,
        "status": t.status,
        "message": f"Request accepted and {'started processing' if t.status == TicketStatus.running else 'queued'}."
    }
