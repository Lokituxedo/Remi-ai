from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.ollama import call_ollama_chat, call_ollama_embed, fetch_ollama_models, normalize_allowed_models

router = APIRouter()


class InferRequest(BaseModel):
    model: Optional[str] = Field(default=None)
    prompt: Optional[str] = Field(default=None)
    text: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)
    messages: Optional[List[Dict[str, str]]] = Field(default=None)


class EmbedRequest(BaseModel):
    model: Optional[str] = Field(default=None)
    text: str = Field(..., min_length=1)


async def validate_model(requested_model: Optional[str], *, embed: bool = False) -> str:
    allowed = await normalize_allowed_models()
    chosen = requested_model or (settings.default_embed_model if embed else settings.default_model)
    if not settings.allow_model_override and chosen != (settings.default_embed_model if embed else settings.default_model):
        chosen = settings.default_embed_model if embed else settings.default_model
    if chosen not in allowed:
        raise HTTPException(status_code=400, detail={"error": "modelo no permitido", "permitidos": allowed})
    return chosen


@router.get("/health")
async def health() -> Dict[str, Any]:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.ollama_url}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False

    return {
        "ok": True,
        "ollama": ollama_ok,
        "default_model": settings.default_model,
        "default_embed_model": settings.default_embed_model,
        "allowed_models": await normalize_allowed_models(),
        "allow_model_override": settings.allow_model_override,
    }


@router.get("/models")
async def models() -> Dict[str, Any]:
    return {
        "default_model": settings.default_model,
        "default_embed_model": settings.default_embed_model,
        "detected": await fetch_ollama_models(),
        "allowed": await normalize_allowed_models(),
        "override": settings.allow_model_override,
    }


@router.post("/infer")
async def infer(req: InferRequest) -> Dict[str, Any]:
    if req.prompt is None and req.text is None and not req.messages:
        raise HTTPException(status_code=400, detail="Debe enviar prompt, text o messages")

    model = await validate_model(req.model, embed=False)
    messages: List[Dict[str, str]] = []

    if req.messages:
        messages = req.messages
    else:
        text = (req.prompt or req.text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Texto vacío")
        messages = [{"role": "user", "content": text}]

    output = await call_ollama_chat(model=model, messages=messages, system=req.system)
    return {"ok": True, "model": model, "output": output}


@router.post("/chat")
async def chat(req: InferRequest) -> Dict[str, Any]:
    return await infer(req)


@router.post("/embed")
async def embed_text(req: EmbedRequest) -> Dict[str, Any]:
    model = await validate_model(req.model, embed=True)
    embedding = await call_ollama_embed(model=model, text=req.text)
    return {"ok": True, "model": model, "embedding": embedding}


@router.get("/")
async def root() -> Dict[str, str]:
    return {"service": "Remi-ai", "status": "ok"}
