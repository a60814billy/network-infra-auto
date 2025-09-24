from fastapi import APIRouter, HTTPException, UploadFile, File, Request

from app.models.ticket import TicketStatus
from app.utils import load_device

router = APIRouter()

def get_valid_machines() -> dict:
    config = load_device()
    valid_machines = {}
    for vendor, models in config.items():
        if not isinstance(models, dict):
            continue
        for model, versions in models.items():
            if not isinstance(versions, dict):
                continue
            for version in versions.keys():
                if vendor not in valid_machines:
                    valid_machines[vendor] = {}
                if model not in valid_machines[vendor]:
                    valid_machines[vendor][model] = []
                if version not in valid_machines[vendor][model]:
                    valid_machines[vendor][model].append(version)
    return valid_machines

def check_machine_supported(vendor: str, model: str, version: str) -> bool:
    valid_machines = get_valid_machines()
    return (vendor in valid_machines and
            model in valid_machines[vendor] and
            version in valid_machines[vendor][model])

@router.post("/{vendor}/{model}/{version}", summary="Create request (file upload)")
async def create_request(vendor: str, model: str, version: str, request: Request, file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        return HTTPException(status_code=400, detail="file is empty")

    if not check_machine_supported(vendor, model, version):
        return HTTPException(status_code=400, detail="The specified vendor/model/version is not supported")
    
    ticket_manager = request.app.state.ticket_manager
    
    ticket = ticket_manager.process_ticket(version, vendor, model, data)
    if not ticket:
        return HTTPException(status_code=500, detail="Failed when processing the ticket")
    
    response = {
        "id": ticket.id,
        "status": ticket.status,
        "message": f"Request accepted and {'started processing' if ticket.status == TicketStatus.running else 'queued'}."
    }

    return response