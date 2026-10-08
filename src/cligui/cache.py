"""On-disk cache of parsed command specs.

Entries are keyed by the resolved binary, its reported version (or inode
fingerprint when it has none), the argv prefix, and ``PARSER_VERSION`` so that
upgrading the parser or the tool itself invalidates stale results.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from cligui.model.spec import PARSER_VERSION, CommandSpec
from cligui.paths import spec_cache_dir

log = logging.getLogger(__name__)


def make_key(argv_prefix: list[str], binary: Path, fingerprint: str) -> str:
    raw = "\x00".join([*argv_prefix, str(binary), fingerprint, str(PARSER_VERSION)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


class SpecCache:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or spec_cache_dir()

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def load(self, key: str) -> CommandSpec | None:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            spec = CommandSpec.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.debug("discarding unreadable cache entry %s: %s", path, exc)
            path.unlink(missing_ok=True)
            return None
        if spec.parser_version != PARSER_VERSION:
            path.unlink(missing_ok=True)
            return None
        return spec

    def store(self, key: str, spec: CommandSpec) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(key)
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            log.warning("could not write cache entry %s: %s", path, exc)
            tmp.unlink(missing_ok=True)

    def clear(self) -> int:
        if not self.directory.is_dir():
            return 0
        removed = 0
        for path in self.directory.glob("*.json"):
            path.unlink(missing_ok=True)
            removed += 1
        return removed
