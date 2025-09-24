from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

from app.models.machine import Machine

class TicketStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Ticket(BaseModel):
    id: str
    version: str
    vendor: str
    model: str
    status: TicketStatus = TicketStatus.queued
    testing_config_path: str = ""
    enqueued_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    machine: Optional[Machine] = None  # 分配到的機器
    result_data: Optional[str] = None  # 執行結果
