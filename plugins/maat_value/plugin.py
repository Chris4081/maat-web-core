from __future__ import annotations

import re


class Plugin:
    type = "chat"
    commands = {
        "/maat": "Zeigt den letzten MAAT-Score.",
    }

    def __init__(self):
        self.last_report = "Noch keine Antwort analysiert."
        self.last_score = None

    def command(self, cmd, context=None):
        return self.last_report

    def after_response(self, reply: str, context=None):
        context = context or {}
        score = self._score(reply)
        context.setdefault("maat", {}).update(score)
        self.last_score = score
        self.last_report = (
            f"H={score['H']:.2f} | B={score['B']:.2f} | S={score['S']:.2f} | "
            f"V={score['V']:.2f} | R={score['R']:.2f} → Stability≈{score['stability']:.2f}"
        )
        return reply

    def _score(self, text: str) -> dict[str, float]:
        words = re.findall(r"\w+", text.lower())
        count = max(1, len(words))
        sentences = max(1, len(re.findall(r"[.!?]", text)) or 1)
        unique_ratio = len(set(words)) / count
        avg_sentence = count / sentences

        contrast = bool(re.search(r"\b(aber|jedoch|gleichzeitig|andererseits|trotzdem)\b", text.lower()))
        uncertainty = bool(re.search(r"\b(könnte|vielleicht|unsicher|wahrscheinlich|möglich)\b", text.lower()))
        absolute = bool(re.search(r"\b(immer|niemals|garantiert|bewiesen|perfekt|100%)\b", text.lower()))
        connection = len(re.findall(r"\b(du|dir|dich|dein|wir|uns|user|nutzer|maat)\b", text.lower()))
        structure = min(1.0, text.count("\n") / 4 + 0.45)

        h = max(0.0, min(1.0, structure + (0.25 if 8 <= avg_sentence <= 28 else 0.0)))
        b = 0.62 + (0.18 if contrast else 0.0) + (0.10 if uncertainty else 0.0) - (0.18 if absolute and not uncertainty else 0.0)
        s = min(1.0, 0.45 + unique_ratio * 0.75)
        v = min(1.0, 0.45 + connection / max(4, count / 18))
        r = 0.9 - (0.22 if absolute and not uncertainty else 0.0) + (0.08 if uncertainty else 0.0)

        h = max(0.0, min(1.0, h))
        b = max(0.0, min(1.0, b))
        s = max(0.0, min(1.0, s))
        v = max(0.0, min(1.0, v))
        r = max(0.0, min(1.0, r))
        stability = min(r, (h * b * s * v) ** 0.25)
        return {"H": h, "B": b, "S": s, "V": v, "R": r, "stability": stability}
