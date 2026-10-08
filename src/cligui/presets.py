"""Named, reusable sets of form values for a command."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from cligui.builder import FormValues
from cligui.paths import presets_dir

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug(text: str) -> str:
    cleaned = _UNSAFE.sub("_", text).strip("_")
    return cleaned[:80] or "unnamed"


class PresetStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or presets_dir()

    def _dir_for(self, argv_prefix: list[str]) -> Path:
        return self.directory / _slug(" ".join(argv_prefix))

    def names(self, argv_prefix: list[str]) -> list[str]:
        folder = self._dir_for(argv_prefix)
        if not folder.is_dir():
            return []
        names = []
        for path in folder.glob("*.json"):
            try:
                names.append(json.loads(path.read_text(encoding="utf-8"))["name"])
            except (OSError, ValueError, KeyError):
                continue
        return sorted(names)

    def save(self, argv_prefix: list[str], name: str, values: FormValues) -> None:
        folder = self._dir_for(argv_prefix)
        folder.mkdir(parents=True, exist_ok=True)
        payload = {"name": name, "command": argv_prefix, "values": asdict(values)}
        path = folder / f"{_slug(name)}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, argv_prefix: list[str], name: str) -> FormValues | None:
        path = self._dir_for(argv_prefix) / f"{_slug(name)}.json"
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return FormValues(**payload["values"])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def delete(self, argv_prefix: list[str], name: str) -> bool:
        path = self._dir_for(argv_prefix) / f"{_slug(name)}.json"
        if not path.is_file():
            return False
        path.unlink()
        return True
