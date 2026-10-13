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


@dataclass
class Settings:
    dark_mode: bool = False
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
        known = {f for f in cls().__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in known})

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
