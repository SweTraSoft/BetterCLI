"""Platform-appropriate locations for cache, history, and settings."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "cligui"


def _base(macos: str, xdg_env: str, xdg_default: str) -> Path:
    if sys.platform == "darwin":
        return Path.home() / macos / APP_NAME
    root = os.environ.get(xdg_env)
    return (Path(root) if root else Path.home() / xdg_default) / APP_NAME


def cache_dir() -> Path:
    override = os.environ.get("CLIGUI_CACHE_DIR")
    if override:
        return Path(override)
    return _base("Library/Caches", "XDG_CACHE_HOME", ".cache")


def data_dir() -> Path:
    override = os.environ.get("CLIGUI_DATA_DIR")
    if override:
        return Path(override)
    return _base("Library/Application Support", "XDG_DATA_HOME", ".local/share")


def spec_cache_dir() -> Path:
    return cache_dir() / "specs"


