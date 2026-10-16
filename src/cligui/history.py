"""Recent commands, saved execution sessions, and command usage counts."""

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
        self.usage_path = self.path.with_name(f"{self.path.stem}-usage.json")
        self._items = self._load()
        self._usage = self._load_usage()

    def _load_usage(self) -> dict[str, int]:
        try:
            raw = json.loads(self.usage_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, ValueError) as exc:
            log.warning("could not read command usage: %s", exc)
            return {}
        if not isinstance(raw, dict):
            log.warning("invalid command usage: expected a command-to-count mapping")
            return {}
        counts = {}
        for command, count in raw.items():
            if (
                isinstance(command, str)
                and command
                and Path(command).name == command
                and type(count) is int
                and count >= 0
            ):
                counts[command] = count
            else:
                log.warning("invalid command usage entry for %r", command)
        return counts

    def _save_usage(self) -> None:
        try:
            self.usage_path.parent.mkdir(parents=True, exist_ok=True)
            self.usage_path.write_text(
                json.dumps(self._usage, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            log.warning("could not write command usage: %s", exc)

    def usage_count(self, executable: str) -> int:
        return self._usage.get(Path(executable).name, 0)

    def record_usage(self, executable: str) -> None:
        """Count a run by executable, combining subcommands and absolute paths."""
        command = Path(executable).name
        if not command:
            raise ValueError("cannot record usage for an empty executable")
        self._usage[command] = self.usage_count(command) + 1
        self._save_usage()

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
        self._usage = {}
        self._save()
        self._save_usage()
