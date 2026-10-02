#!/usr/bin/env bash
set -euo pipefail

# setup_and_bundle.sh
# Full local installation + bundle script for the Reengage prototype
# - clones required repos (Remi-ai, Elena-Remi) into a workspace
# - creates virtualenvs and installs python deps
# - ensures Redis is running (attempts to install if sudo+apt available)
# - creates a zip backup including code, Modelfile and a session_history.json
#
# Usage:
#   ./setup_and_bundle.sh [--workspace /tmp/remi_deploy] [--zip /tmp/remi-backup.zip]
#
# Example:
#   ./setup_and_bundle.sh --workspace ~/remi_local --zip ~/remi_backup.zip

WORKSPACE="${1:-$PWD/reengage_deploy}"
ZIP_PATH="${2:-$PWD/reengage_backup.zip}"

# simple arg parsing
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="$2"; shift 2;;
    --zip) ZIP_PATH="$2"; shift 2;;
    --help) echo "Usage: $0 [--workspace PATH] [--zip PATH]"; exit 0;;
    *) shift ;;
  esac
done

echo "Workspace: $WORKSPACE"
echo "Output zip: $ZIP_PATH"

mkdir -p "$WORKSPACE"
cd "$WORKSPACE"

REMI_REPO="https://github.com/Lokituxedo/Remi-ai.git"
ELENA_REPO="https://github.com/Lokituxedo/Elena-Remi.git"

# clone repos if missing
if [ ! -d "$WORKSPACE/Remi-ai" ]; then
  echo "Cloning Remi-ai..."
  git clone "$REMI_REPO"
else
  echo "Remi-ai already cloned"
fi

if [ ! -d "$WORKSPACE/Elena-Remi" ]; then
  echo "Cloning Elena-Remi..."
  git clone "$ELENA_REPO"
else
  echo "Elena-Remi already cloned"
fi

# checkout the feature branch in Remi-ai if present
pushd "$WORKSPACE/Remi-ai" >/dev/null
if git show-ref --quiet refs/heads/feature/reengage-proactive; then
  git checkout feature/reengage-proactive || true
else
  # try to fetch
  git fetch origin feature/reengage-proactive:feature/reengage-proactive || true
  git checkout feature/reengage-proactive || git checkout -b feature/reengage-proactive || true
fi
popd >/dev/null

# Prepare python venvs and install deps
# Remi-ai (reengage)
if [ -d "$WORKSPACE/Remi-ai/reengage" ]; then
  echo "Setting up venv for Remi-ai/reengage"
  python3 -m venv "$WORKSPACE/Remi-ai/reengage/.venv"
  source "$WORKSPACE/Remi-ai/reengage/.venv/bin/activate"
  pip install --upgrade pip
  pip install fastapi uvicorn redis requests websocket-client
  deactivate || true
else
  echo "Warning: Remi-ai/reengage directory not found"
fi

# Elena-Remi: create venv and install requirements if requirements.txt exists
pushd "$WORKSPACE/Elena-Remi" >/dev/null || true
if [ -f requirements.txt ]; then
  echo "Setting up venv for Elena-Remi"
  python3 -m venv ".venv"
  source ".venv/bin/activate"
  pip install --upgrade pip
  pip install -r requirements.txt
  deactivate || true
else
  echo "No requirements.txt in Elena-Remi; skipping venv setup"
fi
popd >/dev/null || true

# Ensure Redis is running (best-effort)
if ! command -v redis-cli >/dev/null 2>&1; then
  echo "redis-cli not found. Attempting to install redis-server via apt (requires sudo)."
  if command -v apt-get >/dev/null 2>&1 && [ "$(id -u)" -ne 0 ]; then
    echo "Installing redis-server (sudo apt-get)..."
    sudo apt-get update && sudo apt-get install -y redis-server
  elif [ "$(id -u)" -eq 0 ] && command -v apt-get >/dev/null 2>&1; then
    apt-get update && apt-get install -y redis-server
  else
    echo "Could not install redis automatically. Please install Redis and ensure it's running." >&2
  fi
fi

# Try to start redis if not running
if command -v systemctl >/dev/null 2>&1; then
  if ! systemctl is-active --quiet redis; then
    echo "Starting redis-server via systemctl"
    sudo systemctl enable --now redis || true
  fi
fi

# Wait briefly for redis
sleep 1

# Create a backups folder and copy necessary items
BACKUP_DIR="$WORKSPACE/reengage_bundle"
rm -rf "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/Remi-ai/reengage"
mkdir -p "$BACKUP_DIR/Remi-ai/reengage/agent_skill"
mkdir -p "$BACKUP_DIR/Elena-Remi"

# Copy reengage files (if exist)
cp -r "$WORKSPACE/Remi-ai/reengage" "$BACKUP_DIR/Remi-ai/" 2>/dev/null || true
# Copy agent_skill if it's a sibling
if [ -d "$WORKSPACE/Remi-ai/reengage/agent_skill" ]; then
  cp -r "$WORKSPACE/Remi-ai/reengage/agent_skill" "$BACKUP_DIR/Remi-ai/reengage/" 2>/dev/null || true
fi

# Copy Modelfile from Elena-Remi
if [ -f "$WORKSPACE/Elena-Remi/Modelfile" ]; then
  cp "$WORKSPACE/Elena-Remi/Modelfile" "$BACKUP_DIR/Elena-Remi/Modelfile"
fi

# Add session history JSON that was saved during development in the repo
# If the repo contains a session_history.json at reengage/backups/session_history.json, copy it
if [ -f "$WORKSPACE/Remi-ai/reengage/backups/session_history.json" ]; then
  cp "$WORKSPACE/Remi-ai/reengage/backups/session_history.json" "$BACKUP_DIR/session_history.json"
else
  # fallback: create a placeholder minimal session file
  cat > "$BACKUP_DIR/session_history.json" <<'JSON'
{
  "session_id": "local-backup",
  "created_at": "$(date --iso-8601=seconds)",
  "messages": []
}
JSON
fi

# Make the zip archive
rm -f "$ZIP_PATH"
pushd "$BACKUP_DIR/.." >/dev/null
zip -r "$ZIP_PATH" "$(basename "$BACKUP_DIR")" >/dev/null
popd >/dev/null

echo "Bundle created at: $ZIP_PATH"

echo "Contents:"
unzip -l "$ZIP_PATH" | sed -n '1,120p'

echo "Done."
