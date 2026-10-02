from __future__ import annotations

from dataclasses import dataclass
import os
from typing import List


def _parse_csv(value: str | None, fallback: str) -> List[str]:
    items = [item.strip() for item in (value or fallback).split(',') if item and item.strip()]
    seen: List[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    if not seen:
        return [fallback]
    if fallback not in seen:
        seen.insert(0, fallback)
    return seen


@dataclass(frozen=True)
class Settings:
    ollama_url: str = (os.getenv("OLLAMA_URL") or "http://127.0.0.1:11434").rstrip("/")
    default_model: str = os.getenv("DEFAULT_MODEL", "qwen2.5:3b-instruct-q4_K_M")
    default_embed_model: str = os.getenv("DEFAULT_EMBED_MODEL", "nomic-embed-text")
    allow_model_override: bool = os.getenv("ALLOW_MODEL_OVERRIDE", "true").strip().lower() in {"1", "true", "yes", "on"}
    allowed_models: List[str] = None

    def __post_init__(self):
        object.__setattr__(self, "allowed_models", _parse_csv(os.getenv("ALLOWED_MODELS"), f"{self.default_model},{self.default_embed_model}"))
        if self.default_model not in self.allowed_models:
            self.allowed_models.insert(0, self.default_model)
        if self.default_embed_model not in self.allowed_models:
            self.allowed_models.insert(0, self.default_embed_model)


settings = Settings()
