from __future__ import annotations

from collections.abc import Callable
from typing import Any


CommandHandler = Callable[[list[str], dict[str, Any]], str]


class CommandRouter:
    def __init__(self):
        self.commands: dict[str, tuple[CommandHandler, str]] = {}
        self.aliases: dict[str, str] = {}

    def register(
        self,
        name: str,
        handler: CommandHandler,
        description: str = "",
        aliases: list[str] | None = None,
    ) -> None:
        self.commands[name] = (handler, description)
        for alias in aliases or []:
            self.aliases[alias] = name

    def match(self, text: str) -> bool:
        return text.strip().startswith("/")

    def execute(self, text: str, context: dict[str, Any]) -> str:
        parts = text.strip().split()
        if not parts:
            return ""
        base = self.aliases.get(parts[0], parts[0])
        args = parts[1:]
        entry = self.commands.get(base)
        if not entry:
            return f"Unbekannter Befehl `{base}`. Nutze `/help`."
        handler, _ = entry
        return handler(args, context)

    def help_text(self) -> str:
        lines = ["**MAAT Web Core Befehle**"]
        for name, (_, desc) in sorted(self.commands.items()):
            lines.append(f"- `{name}` - {desc}")
        return "\n".join(lines)

