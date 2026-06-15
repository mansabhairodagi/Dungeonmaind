import json
from typing import AsyncGenerator

import httpx

from app.core.config import settings


async def run_custom_model(chat_history: list[dict]) -> AsyncGenerator[str, None]:
    """
    Sends a chat history to the Ollama model and streams the assistant reply.
    """
    print("MODEL BEING USED:", settings.llm_model)
    payload = {
        "model": settings.llm_model,
        "messages": chat_history,
        "stream": True,
    }
    
    print("========== OLLAMA PAYLOAD ==========")
    print(payload)
    print("====================================")

    timeout = httpx.Timeout(connect=10.0, read=None, write=10.0, pool=None)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{settings.ollama_url}/api/chat",
                json=payload,
            ) as resp:
                resp.raise_for_status()

                async for line in resp.aiter_lines():
                    if not line:
                        continue

                    line = line.strip()
                    if line.startswith("data:"):
                        line = line[len("data:"):].strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    content = data.get("message", {}).get("content")
                    if content:
                        yield content
    except httpx.ReadTimeout:
        yield "[Error: Backend request timed out]"
    except httpx.HTTPStatusError as e:
        yield f"[Error: Server returned {e.response.status_code}]"
    except httpx.RequestError as e:
        yield f"[Network error: {e}]"
    except Exception as e:
        yield f"[Unexpected error: {e}]"
