from pathlib import Path

UPLOAD_DIR = Path("./data/tickets")
MAX_UPLOAD_SIZE = 2 * 1024 * 1024 
VALID_MACHINES = {
    "cisco": ["c8k", "n9k", "xrv"],
    "hp": ["5140"],
}