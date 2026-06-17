from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx


class OpenAICompatAdapter:
    """Streams from local OpenAI-compatible APIs, including llama.cpp server or text-generation-webui."""

    def __init__(self, api_base: str, model_name: str):
        self.api_base = api_base.rstrip("/")
        self.model_name = model_name

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        options: dict[str, Any],
    ) -> AsyncIterator[str | dict[str, Any]]:
        payload = {
            "model": options.get("model_name") or self.model_name,
            "messages": messages,
            "temperature": float(options.get("temperature", 0.7)),
            "top_p": float(options.get("top_p", 0.9)),
            "max_tokens": int(options.get("max_tokens", 512)),
            "stream": True,
        }
        url = f"{self.api_base}/chat/completions"
        started = time.perf_counter()
        yield {
            "event": "log",
            "data": {
                "source": "model",
                "title": "OpenAI-kompatibler Adapter",
                "lines": [
                    f"url={url}",
                    f"model={payload['model']}",
                    f"messages={len(messages)} max_tokens={payload['max_tokens']}",
                    f"temperature={payload['temperature']:.2f} top_p={payload['top_p']:.2f}",
                ],
            },
        }
        timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                yield {
                    "event": "log",
                    "data": {
                        "source": "model",
                        "title": "API verbunden",
                        "lines": [
                            f"status={response.status_code}",
                            "warte auf Prompt-Eval / erstes Token vom Backend",
                        ],
                    },
                }
                chunks = 0
                chars = 0
                first_token_elapsed = 0.0
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line == "[DONE]":
                        break
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    delta = choices[0].get("delta") or {}
                    chunk = delta.get("content")
                    if chunk:
                        if chunks == 0:
                            first_token_elapsed = time.perf_counter() - started
                            yield {
                                "event": "log",
                                "data": {
                                    "source": "progress",
                                    "title": "Erstes Token empfangen",
                                    "lines": [
                                        f"erstes_token_nach={first_token_elapsed:.2f}s",
                                        f"model={payload['model']}",
                                    ],
                                },
                            }
                        chunks += 1
                        chars += len(str(chunk))
                        yield str(chunk)
                elapsed = time.perf_counter() - started
                yield {
                    "event": "log",
                    "data": {
                        "source": "generation",
                        "title": "Generation fertig",
                        "lines": [
                            f"model={payload['model']}",
                            f"chunks={chunks} chars={chars}",
                            f"erstes_token={first_token_elapsed:.2f}s gesamtzeit={elapsed:.2f}s",
                        ],
                    },
                }
