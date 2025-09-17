from fastapi import FastAPI
from app.api.routes_request import router as request_router
from app.api.routes_result import router as result_router

app = FastAPI(title="Batch Load Balancer API", version="1.0.0")

app.include_router(request_router, prefix="/request", tags=["request"])
app.include_router(result_router, prefix="/result", tags=["result"])


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
