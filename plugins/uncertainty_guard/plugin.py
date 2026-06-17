from __future__ import annotations

import re


class Plugin:
    type = "chat"
    commands = {
        "/guard": "Zeigt den Status des Unsicherheitswächters.",
    }

    def __init__(self):
        self.enabled = True

    def command(self, cmd, context=None):
        cmd = cmd.strip().lower()
        if cmd == "/guard off":
            self.enabled = False
            return "Uncertainty Guard deaktiviert."
        if cmd == "/guard on":
            self.enabled = True
            return "Uncertainty Guard aktiviert."
        return f"Uncertainty Guard: {'an' if self.enabled else 'aus'}"

    def before_chat(self, user_input: str, context=None):
        if not self.enabled:
            return False, user_input
        lowered = user_input.lower()
        strong_claim = re.search(r"\b(perfekt|bewiesen|garantiert|immer|niemals|beste|100%)\b", lowered)
        maat_claim = any(token in lowered for token in ("maat", "theorie", "ki", "system"))
        if strong_claim and maat_claim:
            context = context or {}
            context.setdefault("events", []).append(
                {
                    "plugin": "uncertainty_guard",
                    "hint": "Starke Behauptung erkannt: kritisch prüfen und Evidenz koppeln.",
                }
            )
        return False, user_input

    def after_response(self, reply: str, context=None):
        if not self.enabled:
            return reply
        context = context or {}
        events = context.get("events") or []
        if not any(event.get("plugin") == "uncertainty_guard" for event in events):
            return reply
        if "bewiesen" in reply.lower() and not re.search(r"\b(evidenz|quelle|unsicher|vorsichtig|symbolisch)\b", reply.lower()):
            return reply + "\n\nHinweis: Diese Aussage sollte an konkrete Evidenz oder Quellen gekoppelt werden."
        return reply

