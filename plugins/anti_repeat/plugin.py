from __future__ import annotations


class Plugin:
    type = "chat"
    commands = {
        "/repeat": "Zeigt den Status des Wiederholungsfilters.",
    }

    def command(self, cmd, context=None):
        return "Anti-Repeat ist aktiv."

    def before_final_response(self, reply: str, context=None):
        lines = reply.splitlines()
        cleaned = []
        previous = None
        for line in lines:
            normalized = line.strip()
            if normalized and normalized == previous:
                continue
            cleaned.append(line)
            previous = normalized
        return "\n".join(cleaned)

