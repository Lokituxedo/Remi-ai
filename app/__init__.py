from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings


async def fetch_ollama_models() -> List[str]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.ollama_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            names: List[str] = []
            for item in data.get("models", []):
                name = item.get("name") or item.get("model")
                if isinstance(name, str) and name.strip():
                    names.append(name.strip())
            return names
    except Exception:
        return []


async def normalize_allowed_models() -> List[str]:
    merged = settings.allowed_models[:]
    for model in await fetch_ollama_models():
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
        resp = await client.post(f"{settings.ollama_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()

    return (data.get("message") or {}).get("content", "").strip()


async def call_ollama_embed(model: str, text: str) -> List[float]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": model, "prompt": text[:1500]},
        )
        resp.raise_for_status()
        data = resp.json()
    return data.get("embedding") or []
