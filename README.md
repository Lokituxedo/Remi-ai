# Remi-ai

Servidor ligero de IA para Elena/Remi. Expone endpoints para chat, inferencia y embeddings con Ollama y permite cambiar el modelo en desarrollo, manteniendo el control centralizado del core.

## Qué incluye
- FastAPI
- endpoints de salud y modelos
- inferencia con Ollama
- embeddings con Ollama
- validación de modelos por entorno
- arquitectura modular para crecer sin mezclar lógica de negocio

## Variables de entorno

```bash
cp .env.example .env
```

Variables principales:

- `OLLAMA_URL`: base URL de Ollama, por ejemplo `http://127.0.0.1:11434`
- `DEFAULT_MODEL`: modelo por defecto para chat, ejemplo `qwen2.5:3b-instruct-q4_K_M`
- `DEFAULT_EMBED_MODEL`: modelo para embeddings, ejemplo `nomic-embed-text`
- `ALLOW_MODEL_OVERRIDE`: `true` para permitir override en desarrollo; `false` para producción
- `ALLOWED_MODELS`: lista separada por comas de modelos permitidos

## Ejecutar

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

### GET /

```json
{"service": "Remi-ai", "status": "ok"}
```

### GET /health

```json
{
  "ok": true,
  "ollama": true,
  "default_model": "qwen2.5:3b-instruct-q4_K_M",
  "allow_model_override": true
}
```

### GET /models

Devuelve modelos detectados por Ollama y permitidos por configuración.

### POST /infer

```json
{
  "model": "qwen2.5:3b-instruct-q4_K_M",
  "prompt": "Hola",
  "system": "Eres un asistente útil."
}
```

### POST /chat

Alias de `/infer`.

### POST /embed

```json
{
  "model": "nomic-embed-text",
  "text": "texto para convertir a vector"
}
```

## Seguridad

En producción conviene dejar esto:

```bash
ALLOW_MODEL_OVERRIDE=false
ALLOWED_MODELS=qwen2.5:3b-instruct-q4_K_M
```

Esto evita que un cliente cambie arbitrariamente el modelo de inferencia.
