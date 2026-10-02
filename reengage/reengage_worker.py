# reengage_worker.py
import os
import time
import json
import requests
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
IDLE_THRESHOLD = int(os.getenv("IDLE_THRESHOLD", "60"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))
REENGAGE_ENDPOINT = os.getenv("REENGAGE_ENDPOINT", "http://127.0.0.1:9001/internal/send_reengage")
MAX_PER_DAY = int(os.getenv("REENGAGE_MAX_PER_DAY", "5"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "remiassistant")

r = redis.from_url(REDIS_URL, decode_responses=True)


def safe_generate_reengage(context_text: str) -> str | None:
    """Try model-based reengage generation before falling back to template."""
    if not OLLAMA_URL or not OLLAMA_MODEL:
        return None

    system = """
    Eres un asistente de reengage. Debes devolver un único mensaje corto para retomar la conversación.
    Reglas:
    - Máximo 90 caracteres.
    - Tono amable, neutral, empático.
    - No sexual, no romántico, no invasivo.
    - No pidas datos personales.
    - Devuelve SOLO JSON con formato: {"text":"..."}
    """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"Contexto del usuario: {context_text}",
        "system": system,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 64},
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=20)
        if not resp.ok:
            return None
        raw = (resp.json().get("response") or "").strip()
        if not raw:
            return None
        try:
            obj = json.loads(raw)
            txt = str(obj.get("text", "")).strip()
            if txt and len(txt) <= 90:
                return txt
        except Exception:
            pass
        if len(raw) <= 90 and raw.startswith("{") is False:
            return raw
    except Exception:
        return None

    return None


def current_count(session_id: str) -> int:
    return int(r.get(f"reengage_count:{session_id}") or 0)


def increment_count(session_id: str):
    key = f"reengage_count:{session_id}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, 60 * 60 * 24)
    pipe.execute()


def should_send(session_id: str) -> bool:
    opt_in = r.hget(f"meta:{session_id}", "opt_in")
    if opt_in is not None:
        try:
            if json.loads(opt_in) is False:
                return False
        except Exception:
            pass

    if current_count(session_id) >= MAX_PER_DAY:
        return False

    last_msg = (r.hget(f"meta:{session_id}", "last_user_msg") or "").strip()
    if not last_msg:
        return False

    if last_msg.endswith("?") or len(last_msg.split()) < 12:
        return True
    return False


def send_reengage(session_id: str, template_index: int = 0):
    last_msg = (r.hget(f"meta:{session_id}", "last_user_msg") or "").strip()
    candidate = safe_generate_reengage(last_msg) if last_msg else None
    if candidate:
        text = candidate
    else:
        text = {
            0: "¿Seguimos? Si querés, sigo desde lo último que pediste.",
            1: "Te estaba pensando — ¿querés retomar lo que estabas haciendo?",
            2: "Si estás ocupado, puedo esperar. ¿Prefieres seguir ahora o en 5 minutos?",
        }.get(template_index, "¿Seguimos? Si querés, sigo desde lo último que pediste.")

    payload = {
        "session_id": session_id,
        "reason": "idle_after_question",
        "template_index": template_index,
        "text": text,
    }
    try:
        res = requests.post(REENGAGE_ENDPOINT, json=payload, timeout=5)
        if res.ok:
            data = res.json()
            if data.get("ok"):
                increment_count(session_id)
                print(f"[reengage] sent for {session_id}: {text}")
                return True
    except Exception as e:
        print(f"[reengage] error: {e}")
    return False


def main_loop():
    print("Worker started.")
    while True:
        now = time.time()
        presence = r.hgetall("presence") or {}
        for session_id, last_ts_raw in presence.items():
            try:
                last_ts = float(last_ts_raw)
            except Exception:
                continue
            if (now - last_ts) > IDLE_THRESHOLD and should_send(session_id):
                send_reengage(session_id, template_index=0)
                r.hset("presence", session_id, now + (IDLE_THRESHOLD / 2))
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main_loop()
