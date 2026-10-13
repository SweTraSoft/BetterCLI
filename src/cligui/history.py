"""Recent commands and their saved execution sessions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cligui.paths import data_dir

log = logging.getLogger(__name__)

MAX_ENTRIES = 50


class CommandHistory:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "history.json"
        self._items = self._load()

    def _load(self) -> list[dict[str, str]]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(raw, list):
            return []
        items = []
        for item in raw:
            if isinstance(item, str):
                item = {"command": item}
            if not isinstance(item, dict):
                continue
            command = item.get("command")
            if not isinstance(command, str) or not command.strip():
                continue
            entry = {"command": command.strip()}
            for field in ("command_line", "cwd", "output"):
                value = item.get(field, "")
                entry[field] = value if isinstance(value, str) else ""
            if not any(saved["command"] == entry["command"] for saved in items):
                items.append(entry)
        return items[:MAX_ENTRIES]

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._items, indent=2), encoding="utf-8")
        except OSError as exc:
            log.warning("could not write command history: %s", exc)

    def items(self) -> list[str]:
        """Most recent first."""
        return [item["command"] for item in self._items]

    def session(self, command: str) -> dict[str, str]:
        text = " ".join(command.split())
        for item in self._items:
            if item["command"] == text:
                return dict(item)
        return {"command": text, "command_line": "", "cwd": "", "output": ""}

    def update_session(self, command: str, **values: str) -> None:
        text = " ".join(command.split())
        for item in self._items:
            if item["command"] == text:
                for field in ("command_line", "cwd", "output"):
                    if field in values:
                        item[field] = values[field]
                self._save()
                return

    def add(self, command: str) -> None:
        text = " ".join(command.split())
        if not text:
            return
        entry = self.session(text)
        self._items = [
            entry, *(item for item in self._items if item["command"] != text)
        ][:MAX_ENTRIES]
        self._save()

    def clear(self) -> None:
        self._items = []
        self._save()
