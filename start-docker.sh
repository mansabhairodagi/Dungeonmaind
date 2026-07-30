#!/usr/bin/env bash
# One-command Docker startup for Dungeon M-AI-nd (frontend + backend + Ollama).
# Usage: ./start-docker.sh [--detach] [--no-build] ...

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Install Docker Desktop: https://www.docker.com/products/docker-desktop/" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker Desktop and try again." >&2
  exit 1
fi

if [[ ! -f backend/.env ]]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from .env.example — edit HF_TOKEN or OLLAMA_API_KEY if needed."
fi

echo "Starting Dungeon M-AI-nd with Docker Compose..."
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000"
echo "  Ollama:   http://localhost:11434"
echo

exec docker compose up --build "$@"
