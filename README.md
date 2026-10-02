# Remi-ai

Servidor ligero de IA para Elena/Remi. Expone endpoints para chat, inferencia y embeddings con Ollama y permite cambiar el modelo en desarrollo sin comprometer la seguridad del core.

## Qué incluye
- FastAPI
- Health checks
- Lista de modelos disponibles
- Inferencia con Ollama
- Generación de embeddings
- Validación de modelos permitidos por entorno

## Variables de entorno

Copia el ejemplo:

```bash
cp .env.example .env
```

Variables principales:

- `OLLAMA_URL` — base URL de Ollama, por ejemplo `http://127.0.0.1:11434`
- `DEFAULT_MODEL` — modelo por defecto para chat, por ejemplo `qwen2.5:3b-instruct-q4_K_M`
- `DEFAULT_EMBED_MODEL` — modelo por defecto para embeddings, por ejemplo `nomic-embed-text`
- `ALLOWED_MODELS` — lista opcional de modelos permitidos, ejemplo: `qwen2.5:3b-instruct-q4_K_M,qwen2.5-coder:3b,qwen3-embedding:0.6b,nomic-embed-text`
- `ALLOW_MODEL_OVERRIDE` — `true` para permitir cambiar modelos desde la UI o desde llamadas externas; `false` para bloquearlo

## Ejecutar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

### GET /health

```json
{
  "ok": true,
  "ollama": true,
  "default_model": "qwen2.5:3b-instruct-q4_K_M",
  "allowed_models": ["..."]
}
```

### GET /models

Devuelve la lista de modelos permitidos y los detectados por Ollama.

### POST /infer

```json
{
  "model": "qwen2.5:3b-instruct-q4_K_M",
  "prompt": "Hola",
  "system": "Eres un asistente útil."
}
```

### POST /embed

```json
{
  "model": "nomic-embed-text",
  "text": "texto para embeddar"
}
```

### POST /chat

Alias de `/infer`.

## Seguridad

En producción conviene dejar:

```bash
ALLOW_MODEL_OVERRIDE=false
ALLOWED_MODELS=qwen2.5:3b-instruct-q4_K_M
```

Esto evita que un cliente cambie arbitrariamente el modelo que se está usando.
