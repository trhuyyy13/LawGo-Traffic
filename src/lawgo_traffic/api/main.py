from fastapi import FastAPI

from lawgo_traffic.api.routes_chat import router as chat_router
from lawgo_traffic.api.routes_chat import rag_router
from lawgo_traffic.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI Legal Advisory Agent for Vietnam Traffic Law",
)

app.include_router(chat_router)
app.include_router(rag_router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name, "env": settings.app_env}
