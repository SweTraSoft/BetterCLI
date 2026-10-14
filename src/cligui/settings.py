"""User settings: a small JSON file plus the OS keychain for the API key."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass

from cligui.paths import data_dir

log = logging.getLogger(__name__)

KEYRING_SERVICE = "cligui"
KEYRING_USERNAME = "deepseek-api-key"
ENV_API_KEY = "DEEPSEEK_API_KEY"

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

APPEARANCE_LIGHT = "light"
APPEARANCE_DARK = "dark"
APPEARANCE_SYSTEM = "system"
APPEARANCES = (APPEARANCE_LIGHT, APPEARANCE_DARK, APPEARANCE_SYSTEM)


@dataclass
class Settings:
    appearance: str = APPEARANCE_SYSTEM
    llm_enabled: bool = True
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    discovery_timeout: float = 10.0
    confirm_unknown_binaries: bool = True

    @classmethod
    def load(cls) -> Settings:
        path = data_dir() / "settings.json"
        if not path.is_file():
            return cls()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.warning("ignoring unreadable settings file %s: %s", path, exc)
            return cls()
        if not isinstance(raw, dict):
            return cls()
        # Older versions stored a boolean "dark_mode" instead of "appearance".
        if "appearance" not in raw and raw.get("dark_mode") is True:
            raw["appearance"] = APPEARANCE_DARK
        known = {f for f in cls().__dataclass_fields__}
        settings = cls(**{k: v for k, v in raw.items() if k in known})
        if settings.appearance not in APPEARANCES:
            settings.appearance = APPEARANCE_SYSTEM
        return settings

    def save(self) -> None:
        path = data_dir() / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


def get_api_key() -> str | None:
    """Env var wins so CI and one-off runs do not touch the keychain."""
    if env := os.environ.get(ENV_API_KEY):
        return env.strip() or None
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except Exception as exc:  # keyring backends fail in many creative ways
        log.debug("keyring lookup failed: %s", exc)
        return None


def set_api_key(value: str | None) -> bool:
    try:
        import keyring

        if value:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, value)
        else:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except Exception as exc:
        log.warning("could not store API key: %s", exc)
        return False
    return True
