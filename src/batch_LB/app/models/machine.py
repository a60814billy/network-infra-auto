from dataclasses import dataclass
from typing import Optional

@dataclass
class Machine:
    vendor: str
    model: str
    version: str
    ip: str
    port: str
    serial: str
    ticket_id: Optional[str] = None