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

r = redis.from_url(REDIS_URL, decode_responses=True)

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
    payload = {
        "session_id": session_id,
        "reason": "idle_after_question",
        "template_index": template_index,
    }
    try:
        res = requests.post(REENGAGE_ENDPOINT, json=payload, timeout=5)
        if res.ok:
            data = res.json()
            if data.get("ok"):
                increment_count(session_id)
                print(f"[reengage] sent for {session_id}")
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
