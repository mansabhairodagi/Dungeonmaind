# Docker Deployment

Recommended way to run Dungeon M-AI-nd for demos and releases.

## One-command start

```bash
./start-docker.sh
```

Windows:

```powershell
.\start-docker.ps1
```

The script checks that Docker is running, creates `backend/.env` from `.env.example` when missing, then runs `docker compose up --build`.

Pass through Compose flags as needed, for example:

```bash
./start-docker.sh --detach
```

## Services

The `docker-compose.yml` defines three services:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `frontend` | Nginx (production build) | `5173` | Vue 3 web UI |
| `backend` | Python 3.12 | `8000` | FastAPI + Uvicorn |
| `ollama` | Ollama | `11434` | Local LLM server |

The backend waits for Ollama to become healthy before starting.

## Manual Compose commands

```bash
cp backend/.env.example backend/.env   # only if you skip start-docker.sh
docker compose up --build
docker compose up --build -d
docker compose build --no-cache
docker compose logs -f
docker compose down
```

Open **http://localhost:5173** after startup.

## Volumes

- `chroma_volume` → `/app/data/chroma_db` (vector store persistence)
- `ollama_volume` → `/root/.ollama` (pulled LLM models)
- Session exports still live under `backend/data/SavedSessions/` via the backend bind mount

## Ollama models

The Ollama image pulls the default Ministral / Phi models during build (see `LLM/run-ollama.sh`). To pull more:

```bash
docker compose exec ollama ollama pull <model-name>
```

Then select the model in the web UI under Configuration → LLM Settings.

## Notes

- Browser clients must use `http://localhost:8000` (published host port), not the Docker service hostname `backend`.
- First backend image build downloads WhisperX and embedding models; later rebuilds are faster with cache.
