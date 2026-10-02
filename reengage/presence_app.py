# presence_app.py
import os
import time
import json
from typing import Dict
import uvicorn
import redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
IDLE_THRESHOLD = int(os.getenv("IDLE_THRESHOLD", "60"))
REENGAGE_MAX_PER_DAY = int(os.getenv("REENGAGE_MAX_PER_DAY", "5"))

r = redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(title="Remi Reengage (presence)")

connections: Dict[str, WebSocket] = {}

TEMPLATES = [
    "¿Seguimos? Si querés, sigo desde lo último que pediste.",
    "Te estaba pensando — ¿querés retomar lo que estabas haciendo?",
    "Si estás ocupado, puedo esperar. ¿Prefieres seguir ahora o en 5 minutos?",
]

def render_template(template_index: int = 0, context: dict | None = None) -> str:
    text = TEMPLATES[template_index % len(TEMPLATES)]
    if context and context.get("user_name"):
        text = f"{context['user_name']}, " + text
    return text

def record_presence(session_id: str):
    now = time.time()
    r.hset("presence", session_id, now)
    r.set(f"last_seen:{session_id}", now)

def set_meta(session_id: str, key: str, val):
    r.hset(f"meta:{session_id}", key, json.dumps(val))

def get_meta(session_id: str, key: str):
    v = r.hget(f"meta:{session_id}", key)
    return json.loads(v) if v else None

def increment_counter(name: str):
    r.incr(name)

def is_safe_text(text: str) -> bool:
    blocked = ["porn", "sex", "suicide", "bomb"]
    t = text.lower()
    return not any(b in t for b in blocked)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    qs = dict(ws.query_params)
    session_id = qs.get("session")
    role = qs.get("role", "user")
    if not session_id:
        await ws.close()
        return

    connections[session_id] = ws
    record_presence(session_id)
    set_meta(session_id, "role", role)
    set_meta(session_id, "opt_in", True)
    try:
        await ws.send_json({"system": "connected", "session": session_id, "role": role})
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                msg = {"type": "raw", "text": data}
            msg_type = msg.get("type", "raw")
            if msg_type in ("heartbeat", "hb"):
                record_presence(session_id)
            elif msg_type == "user_msg":
                record_presence(session_id)
                set_meta(session_id, "last_user_msg", msg.get("text", "")[:1000])
                set_meta(session_id, "last_user_ts", time.time())
            elif msg_type == "agent_msg":
                record_presence(session_id)
            await ws.send_json({"ack": msg_type, "ts": time.time()})
    except WebSocketDisconnect:
        connections.pop(session_id, None)
    except Exception:
        connections.pop(session_id, None)

@app.post("/internal/send_reengage")
async def send_reengage(request: Request):
    body = await request.json()
    session_id = body.get("session_id")
    reason = body.get("reason", "idle")
    template_index = body.get("template_index", 0)

    if not session_id:
        return JSONResponse({"error": "missing session_id"}, status_code=400)

    opt_in = get_meta(session_id, "opt_in")
    if opt_in is False:
        return JSONResponse({"ok": False, "reason": "opted_out"}, status_code=200)

    text = render_template(template_index, context={"user_name": get_meta(session_id, "user_name")})
    if not is_safe_text(text):
        return JSONResponse({"ok": False, "reason": "blocked_by_moderation"}, status_code=200)

    increment_counter("reengage:sent")
    increment_counter(f"reengage:sent:tpl:{template_index}")
    payload = {"type": "reengage", "text": text, "reason": reason, "ts": time.time()}

    ws = connections.get(session_id)
    if ws:
        import asyncio
        try:
            asyncio.create_task(ws.send_json(payload))
            return {"ok": True, "queued": True}
        except Exception:
            pass

    r.rpush(f"inbox:{session_id}", json.dumps(payload))
    return {"ok": True, "queued": True}

@app.get("/inbox/{session_id}")
def inbox(session_id: str):
    items = []
    while True:
        item = r.lpop(f"inbox:{session_id}")
        if not item:
            break
        items.append(json.loads(item))
    return {"inbox": items}

@app.get("/stats")
def stats():
    sent = int(r.get("reengage:sent") or 0)
    replies = int(r.get("reengage:replies") or 0)
    return {"reengage_sent": sent, "reengage_replies": replies}

if __name__ == "__main__":
    uvicorn.run("reengage.presence_app:app", host="0.0.0.0", port=9001, reload=False)
