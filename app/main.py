from __future__ import annotations

from fastapi import FastAPI

from app.routes.chat import router as chat_router

app = FastAPI(title="Remi-ai", version="0.1.0")
app.include_router(chat_router)
