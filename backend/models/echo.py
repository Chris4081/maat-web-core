from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any


class EchoAdapter:
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        options: dict[str, Any],
    ) -> AsyncIterator[str]:
        user_text = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                user_text = message.get("content", "")
                break
        response = (
            "Echo-Modus aktiv. Ich habe noch kein Modell erreicht, aber der MAAT Web Core läuft.\n\n"
            f"Deine Eingabe war: {user_text}"
        )
        for word in response.split(" "):
            await asyncio.sleep(0.01)
            yield word + " "

