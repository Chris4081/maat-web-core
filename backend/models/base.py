from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol


class ModelAdapter(Protocol):
    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        options: dict[str, Any],
    ) -> AsyncIterator[str | dict[str, Any]]:
        ...
