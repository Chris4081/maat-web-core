from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any


class PluginManager:
    def __init__(self, plugin_roots: list[Path]):
        self.plugin_roots = [Path(root) for root in plugin_roots]
        self.plugins: list[Any] = []
        self.loaded_ids: set[str] = set()
        self.errors: list[str] = []

    def load_all(self) -> None:
        self.plugins.clear()
        self.loaded_ids.clear()
        self.errors.clear()
        for root in self.plugin_roots:
            if not root.exists():
                continue
            for entry in sorted(root.iterdir()):
                if entry.name.startswith("_"):
                    continue
                candidate = entry / "plugin.py" if entry.is_dir() else entry
                if not candidate.exists() and entry.is_dir():
                    candidate = entry / "plugin_main.py"
                if candidate.is_file() and candidate.suffix == ".py":
                    self._load_one(candidate)

    def _load_one(self, path: Path) -> None:
        plugin_id = path.parent.name if path.name in {"plugin.py", "plugin_main.py"} else path.stem
        if plugin_id in self.loaded_ids:
            return
        try:
            spec = importlib.util.spec_from_file_location(f"maat_web_plugin_{plugin_id}", path)
            if spec is None or spec.loader is None:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin_class = getattr(module, "Plugin", None)
            if plugin_class is None or not inspect.isclass(plugin_class):
                return
            plugin = plugin_class()
            setattr(plugin, "plugin_id", plugin_id)
            self.plugins.append(plugin)
            self.loaded_ids.add(plugin_id)
        except Exception as exc:
            self.errors.append(f"{plugin_id}: {exc}")

    def register_commands(self, router) -> None:
        for plugin in self.plugins:
            commands = getattr(plugin, "commands", {})
            if not isinstance(commands, dict):
                continue
            for command, description in commands.items():
                if command in getattr(router, "commands", {}):
                    continue
                router.register(
                    command,
                    self._make_command_handler(plugin, command),
                    description=str(description),
                )

    def _make_command_handler(self, plugin, command: str):
        def handler(args: list[str], context: dict[str, Any]) -> str:
            full = " ".join([command, *args]).strip()
            result = plugin.command(full, context)
            if isinstance(result, tuple):
                return str(result[-1] or "")
            return str(result or "")

        return handler

    def call_startup(self, context: dict[str, Any]) -> None:
        for plugin in self.plugins:
            fn = getattr(plugin, "on_startup", None)
            if callable(fn):
                fn(context)

    def before_chat(self, text: str, context: dict[str, Any]) -> tuple[bool, str]:
        current = text
        for plugin in self.plugins:
            fn = getattr(plugin, "before_chat", None)
            if not callable(fn):
                continue
            result = fn(current, context)
            if isinstance(result, tuple) and len(result) == 2:
                handled, output = result
                if handled:
                    return True, output or current
                if output is not None:
                    current = output
            elif isinstance(result, str):
                current = result
        return False, current

    def after_response(self, text: str, context: dict[str, Any]) -> str:
        current = text
        for plugin in self.plugins:
            fn = getattr(plugin, "after_response", None)
            if callable(fn):
                result = fn(current, context)
                if result is not None:
                    current = str(result)
        return current

    def before_final_response(self, text: str, context: dict[str, Any]) -> str:
        current = text
        for plugin in self.plugins:
            fn = getattr(plugin, "before_final_response", None)
            if callable(fn):
                result = fn(current, context)
                if result is not None:
                    current = str(result)
        return current

    def after_final_response(self, text: str, context: dict[str, Any]) -> None:
        for plugin in self.plugins:
            fn = getattr(plugin, "after_final_response", None)
            if callable(fn):
                fn(text, context)

    def info(self) -> list[dict[str, Any]]:
        result = []
        for plugin in self.plugins:
            result.append(
                {
                    "id": getattr(plugin, "plugin_id", plugin.__class__.__name__),
                    "type": getattr(plugin, "type", "chat"),
                    "commands": sorted(getattr(plugin, "commands", {}).keys())
                    if isinstance(getattr(plugin, "commands", {}), dict)
                    else [],
                }
            )
        return result

    def info_json(self) -> str:
        return json.dumps(self.info(), indent=2, ensure_ascii=False)
