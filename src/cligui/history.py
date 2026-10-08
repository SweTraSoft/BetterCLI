"""The most recently discovered commands, persisted across sessions."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cligui.paths import data_dir

log = logging.getLogger(__name__)

MAX_ENTRIES = 20


class CommandHistory:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "history.json"
        self._items = self._load()

    def _load(self) -> list[str]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        if not isinstance(raw, list):
            return []
        items = [item.strip() for item in raw if isinstance(item, str) and item.strip()]
        return items[:MAX_ENTRIES]

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._items, indent=2), encoding="utf-8")
        except OSError as exc:
            log.warning("could not write command history: %s", exc)

    def items(self) -> list[str]:
        """Most recent first."""
        return list(self._items)

    def add(self, command: str) -> None:
        text = " ".join(command.split())
        if not text:
            return
        self._items = [text, *(item for item in self._items if item != text)][:MAX_ENTRIES]
        self._save()

    def clear(self) -> None:
        self._items = []
        self._save()
