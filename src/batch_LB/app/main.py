from fastapi import FastAPI
from app.api.routes_request import router as request_router
from app.api.routes_result import router as result_router
from app.api.routes_reset import router as reset_router
from app.services.ticket_manager import TicketManager

ticket_manager = TicketManager()

app = FastAPI(title="Batch Load Balancer API", version="1.0.0")

app.state.ticket_manager = ticket_manager

app.include_router(request_router, prefix="/request", tags=["request"])
app.include_router(result_router, prefix="/result", tags=["result"])
app.include_router(reset_router, prefix="/reset", tags=["reset"])


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
