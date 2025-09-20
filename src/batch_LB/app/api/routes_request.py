from fastapi import APIRouter, HTTPException, UploadFile, File, Request
import yaml
from pathlib import Path

from app.models.ticket import TicketStatus
from app.utils import load_config

router = APIRouter()

def _get_valid_machines() -> dict:
    """從配置中提取 VALID_MACHINES 格式"""
    config = load_config()
    valid_machines = {}
    
    for vendor, models in config.items():
        valid_machines[vendor] = list(models.keys())
    
    return valid_machines

# 配置常量
MAX_UPLOAD_SIZE = 2 * 1024 * 1024
VALID_MACHINES = _get_valid_machines()

@router.post("/{version}/{vendor}/{model}", summary="Create request (file upload)")
async def create_request(version: str, vendor: str, model: str, request: Request, file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="file is empty")

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413, detail=f"file too large (>{MAX_UPLOAD_SIZE} bytes)")

    if vendor not in VALID_MACHINES or model not in VALID_MACHINES[vendor]:
        raise HTTPException(
            status_code=400, detail=f"Unsupported vendor/model combination: {vendor}/{model}")
    
    ticket_manager = request.app.state.ticket_manager
    
    ticket = ticket_manager.process_ticket(version, vendor, model, data)
    if not ticket:
        raise HTTPException(status_code=500, detail="Failed when processing the ticket")
    
    response = {
        "id": ticket.id,
        "status": ticket.status,
        "message": f"Request accepted and {'started processing' if ticket.status == TicketStatus.running else 'queued'}."
    }

    return response