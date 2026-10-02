from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

OLLAMA_URL = (os.getenv("OLLAMA_URL") or "http://127.0.0.1:11434").rstrip("/")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5:3b-instruct-q4_K_M")
DEFAULT_EMBED_MODEL = os.getenv("DEFAULT_EMBED_MODEL", "nomic-embed-text")
ALLOW_MODEL_OVERRIDE = os.getenv("ALLOW_MODEL_OVERRIDE", "true").strip().lower() in {"1", "true", "yes", "on"}
ALLOWED_MODELS = [
    item.strip()
    for item in (os.getenv("ALLOWED_MODELS") or f"{DEFAULT_MODEL},{DEFAULT_EMBED_MODEL}").split(",")
    if item and item.strip()
]
if DEFAULT_MODEL not in ALLOWED_MODELS:
    ALLOWED_MODELS.insert(0, DEFAULT_MODEL)
if DEFAULT_EMBED_MODEL not in ALLOWED_MODELS:
    ALLOWED_MODELS.insert(0, DEFAULT_EMBED_MODEL)

app = FastAPI(title="Remi-ai", version="0.1.0")


async def fetch_ollama_models() -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = []
            for item in data.get("models", []):
                name = item.get("name") or item.get("model")
                if isinstance(name, str) and name.strip():
                    models.append(name.strip())
            return models
    except Exception:
        return []


async def _normalize_allowed_models() -> List[str]:
    detected = await fetch_ollama_models()
    merged = ALLOWED_MODELS[:]
    for model in detected:
        if model not in merged:
            merged.append(model)
    return merged


async def call_ollama_chat(model: str, messages: List[Dict[str, str]], system: Optional[str] = None) -> str:
    payload: Dict[str, Any] = {
        "model": model,
        "stream": False,
        "messages": messages,
    }
    if system:
        payload["messages"] = [{"role": "system", "content": system}] + messages
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
    return (data.get("message") or {}).get("content", "").strip()


async def call_ollama_embed(model: str, text: str) -> List[float]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": model, "prompt": text[:1500]},
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("embedding") or []


async def validate_model(requested_model: Optional[str], *, embed: bool = False) -> str:
    allowed = await _normalize_allowed_models()
    chosen = requested_model or (DEFAULT_EMBED_MODEL if embed else DEFAULT_MODEL)
    if not ALLOW_MODEL_OVERRIDE and chosen != (DEFAULT_EMBED_MODEL if embed else DEFAULT_MODEL):
        chosen = DEFAULT_EMBED_MODEL if embed else DEFAULT_MODEL
    if chosen not in allowed:
        raise HTTPException(status_code=400, detail={"error": "modelo no permitido", "permitidos": allowed})
    return chosen


class InferRequest(BaseModel):
    model: Optional[str] = Field(default=None)
    prompt: Optional[str] = Field(default=None)
    text: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)
    messages: Optional[List[Dict[str, str]]] = Field(default=None)


class EmbedRequest(BaseModel):
    model: Optional[str] = Field(default=None)
    text: str = Field(..., min_length=1)


@app.get("/health")
async def health() -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False

    return {
        "ok": True,
        "ollama": ollama_ok,
        "default_model": DEFAULT_MODEL,
        "default_embed_model": DEFAULT_EMBED_MODEL,
        "allowed_models": await _normalize_allowed_models(),
        "allow_model_override": ALLOW_MODEL_OVERRIDE,
    }


@app.get("/models")
async def models() -> Dict[str, Any]:
    detected = await fetch_ollama_models()
    allowed = await _normalize_allowed_models()
    return {
        "default_model": DEFAULT_MODEL,
        "default_embed_model": DEFAULT_EMBED_MODEL,
        "detected": detected,
        "allowed": allowed,
        "override": ALLOW_MODEL_OVERRIDE,
    }


@app.post("/infer")
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


@app.post("/chat")
async def chat(req: InferRequest) -> Dict[str, Any]:
    return await infer(req)


@app.post("/embed")
async def embed_text(req: EmbedRequest) -> Dict[str, Any]:
    model = await validate_model(req.model, embed=True)
    embedding = await call_ollama_embed(model=model, text=req.text)
    return {"ok": True, "model": model, "embedding": embedding}


@app.get("/")
async def root() -> Dict[str, str]:
    return {"service": "Remi-ai", "status": "ok"}
