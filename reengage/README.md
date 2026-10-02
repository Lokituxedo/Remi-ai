# Reengage Proactive (Minimal)

Objetivo:
- detectar inactividad
- disparar un mensaje de reengage
- probar con 1 usuario y 2 agentes
- mantener seguridad + métricas mínimas

## Requisitos
- Redis
- Python 3.11+
- fastapi, uvicorn, redis, requests

## Instalación
```bash
cd /home/mpeadmin/karukren/remi-ai/reengage
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn redis requests
```

## Arranque
Terminal 1:
```bash
cd /home/mpeadmin/karukren/remi-ai/reengage
source .venv/bin/activate
uvicorn presence_app:app --host 0.0.0.0 --port 9001
```

Terminal 2:
```bash
cd /home/mpeadmin/karukren/remi-ai/reengage
source .venv/bin/activate
python reengage_worker.py
```

## Pruebas rápidas
- Conectar cliente WS:
  - session: user-dev-1, role: user
  - session: agent-a, role: agent
  - session: agent-b, role: agent

- Enviar:
```json
{"type":"user_msg","text":"¿Me ayudas con X?"}
```

- Esperar `IDLE_THRESHOLD` segundos (default 60) y ver reengage.

- Endpoint:
```bash
curl http://127.0.0.1:9001/stats
```

## Plantillas de reengage
1. "¿Seguimos? Si querés, sigo desde lo último que pediste."
2. "Te estaba pensando — ¿querés retomar lo que estabas haciendo?"
3. "Si estás ocupado, puedo esperar. ¿Prefieres seguir ahora o en 5 minutos?"

## Recomendación
Esto es el mínimo viable. Para producción:
- añadir opt-in/opt-out
- filtrar con moderación
- limitar rate
- medir reengage replies
- mover eventos a Redis Streams / Celery / worker más serio
