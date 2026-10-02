"""
Agent Skill: local agent helper for Elena/Remi reengage prototype

This module implements a small "skill" class to run a local agent process
that:
- connects to the presence/reengage backend (WebSocket or HTTP)
- exposes a simple API to produce proactive messages, follow-up messages,
  and interact with the model endpoint (Elena/Remi) when available
- enforces safety checks and logging to Redis
- provides templates, prompt patterns and hooks for future integration

Usage:
- configure MODEL_API_URL (optional) to point to your model serving endpoint
- instantiate AgentSkill and call `handle_idle(session_id)` or
  `respond_to_message(session_id, user_text)`

This is intentionally minimal and local: the agent does not call external
third-party services by default. Replace `generate_via_model` with your
model call when ready.

"""

from __future__ import annotations
import os
import time
import json
import redis
import random
from typing import Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
MODEL_API_URL = os.getenv("MODEL_API_URL", "")  # optional model endpoint for Elena/Remi

r = redis.from_url(REDIS_URL, decode_responses=True)

# --- Templates / prompt patterns ---
REENGAGE_TEMPLATES = [
    "¿Seguimos? Si querés, sigo desde lo último que pediste.",
    "Te estaba pensando — ¿querés retomar lo que estabas haciendo?",
    "Si estás ocupado, puedo esperar. ¿Prefieres seguir ahora o en 5 minutos?",
]

FOLLOWUP_PROMPTS = {
    "clarify": "Pregunta: {user_text}\n\nResumen corto y pregunta de clarificación:",
    "suggest": "Usuario preguntó: {user_text}\n\nSugiere 3 pasos breves para continuar:",
}

# --- Safety / moderation ---
BLOCKLIST = ["porn", "sex", "suicide", "bomb"]

def is_safe(text: str) -> bool:
    t = (text or "").lower()
    return not any(b in t for b in BLOCKLIST)

# --- Agent skill ---
class AgentSkill:
    """Small local agent skill to produce safe proactive messages and
    interact with a local model endpoint.

    Responsibilities:
    - render reengage templates (or generate via model)
    - run a moderation check
    - write metrics to Redis
    - provide hooks to call model for personalized variants
    """

    def __init__(self, name: str = "local-agent", model_url: Optional[str] = None):
        self.name = name
        self.model_url = model_url or MODEL_API_URL

    def choose_template(self, context: Optional[dict] = None) -> str:
        idx = random.randint(0, len(REENGAGE_TEMPLATES)-1)
        text = REENGAGE_TEMPLATES[idx]
        if context and context.get("user_name"):
            return f"{context['user_name']}, {text}"
        return text

    def generate_via_model(self, prompt: str, max_tokens: int = 64) -> Optional[str]:
        # Placeholder: call your Elena/Remi model API here (synchronous HTTP)
        if not self.model_url:
            return None
        try:
            import requests
            resp = requests.post(self.model_url, json={"prompt": prompt, "max_tokens": max_tokens}, timeout=6)
            if resp.ok:
                data = resp.json()
                # adapt based on your model API response shape
                return data.get("text") or data.get("result") or None
        except Exception:
            return None
        return None

    def render_reengage(self, session_id: str, prefer_model: bool = False) -> str:
        ctx = self._fetch_context(session_id)
        if prefer_model and self.model_url:
            prompt = f"Genera un mensaje corto (<=90 chars) para reenganchar al usuario. Contexto: {ctx.get('snippet','')}."
            candidate = self.generate_via_model(prompt)
            if candidate and is_safe(candidate):
                self._metric_inc("reengage:generated:model")
                return candidate
        tpl = self.choose_template(ctx)
        self._metric_inc("reengage:generated:template")
        return tpl

    def handle_idle(self, session_id: str, prefer_model: bool = False) -> Optional[dict]:
        # Decide and return a payload ready to be sent to the reengage API
        text = self.render_reengage(session_id, prefer_model=prefer_model)
        if not is_safe(text):
            self._metric_inc("reengage:block:safety")
            return None
        payload = {"type": "reengage", "text": text, "from": self.name, "ts": time.time()}
        # store last reengage for traceability
        r.hset(f"meta:{session_id}", "last_reengage", json.dumps(payload))
        self._metric_inc("reengage:sent")
        return payload

    def respond_to_message(self, session_id: str, user_text: str, mode: str = "suggest") -> Optional[str]:
        # Generate a short assistant reply (clarify or suggest)
        prompt_t = FOLLOWUP_PROMPTS.get(mode, FOLLOWUP_PROMPTS['suggest'])
        prompt = prompt_t.format(user_text=user_text)
        # try model then fallback to template
        reply = None
        if self.model_url:
            reply = self.generate_via_model(prompt)
        if not reply:
            # quick template fallback
            if mode == 'clarify':
                reply = "¿Podrías darme un poco más de detalle sobre eso?"
            else:
                reply = "Aquí tienes tres ideas breves: 1) ... 2) ... 3) ..."
        if not is_safe(reply):
            self._metric_inc("reply:block:safety")
            return None
        self._metric_inc("reply:sent")
        # store conversation snippet for personalization
        r.hset(f"meta:{session_id}", "last_agent_reply", json.dumps({"text": reply, "ts": time.time()}))
        return reply

    def _fetch_context(self, session_id: str) -> dict:
        # minimal context: last_user_msg and user_name
        last = r.hget(f"meta:{session_id}", "last_user_msg") or ""
        name = r.hget(f"meta:{session_id}", "user_name")
        snippet = (last[:200] + "...") if len(last) > 200 else last
        return {"last_user_msg": last, "user_name": name, "snippet": snippet}

    def _metric_inc(self, key: str):
        r.incr(key)


# --- CLI minimal runner to act as a local agent process ---
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', '-s', default='user-dev-1')
    parser.add_argument('--model', '-m', default='')
    parser.add_argument('--mode', default='idle', choices=['idle','respond'])
    args = parser.parse_args()

    agent = AgentSkill(name='local-expert', model_url=args.model or None)
    if args.mode == 'idle':
        payload = agent.handle_idle(args.session, prefer_model=False)
        print('REENGAGE PAYLOAD:\n', json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print('Simulated reply:\n', agent.respond_to_message(args.session, '¿Me ayudas con X?', mode='clarify'))
