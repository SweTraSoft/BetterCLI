"""App Store version enforcement."""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cligui.paths import data_dir

log = logging.getLogger(__name__)

# Set this to the numeric Apple App Store ID after BetterCLI is listed.
APP_STORE_ID: int | None = None
OFFLINE_GRACE_PERIOD = timedelta(days=28)
REQUEST_TIMEOUT_SECONDS = 5
_CACHE_FILENAME = "version-check.json"


@dataclass(frozen=True)
class VersionCheckResult:
    allowed: bool
    message: str = ""
    store_version: str | None = None


def _version_key(version: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+)*", version):
        raise ValueError(f"Unsupported version format: {version!r}")
    parts = [int(part) for part in version.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts + [0] * max(0, 3 - len(parts)))


def _fetch_store_version(app_store_id: int) -> str:
    url = f"https://itunes.apple.com/lookup?id={app_store_id}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "BetterCLI"},
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.load(response)

    results = payload.get("results")
    if payload.get("resultCount") != 1 or not isinstance(results, list):
        raise ValueError("Apple did not return an App Store listing for BetterCLI")
    version = results[0].get("version")
    if not isinstance(version, str):
        raise ValueError("Apple's App Store response did not include a version")
    _version_key(version)
    return version


def _read_cache(cache_path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(cache_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Could not read App Store version cache: %s", exc)
        return {"_invalid": True}
    if not isinstance(value, dict):
        log.warning("Ignoring invalid App Store version cache")
        return {"_invalid": True}
    return value


def _write_cache(cache_path: Path, value: dict[str, Any]) -> bool:
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(value), encoding="utf-8")
    except OSError:
        log.exception("Could not save App Store version cache")
        return False
    return True


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        return None
    return timestamp.astimezone(timezone.utc)


def check_app_store_version(
    current_version: str,
    *,
    app_store_id: int | None = APP_STORE_ID,
    cache_path: Path | None = None,
    now: datetime | None = None,
) -> VersionCheckResult:
    """Allow launch only when the installed app is not known to be outdated."""
    if app_store_id is None:
        log.warning("App Store version enforcement is disabled: no listing ID configured")
        return VersionCheckResult(allowed=True)

    current_key = _version_key(current_version)
    cache_path = cache_path or data_dir() / _CACHE_FILENAME
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cache = _read_cache(cache_path)
    cache_exists = cache is not None
    cache = cache or {}

    try:
        store_version = _fetch_store_version(app_store_id)
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:
        log.warning("Could not verify BetterCLI's App Store version: %s", exc)
        if cache.get("_invalid"):
            return VersionCheckResult(
                allowed=False,
                message=(
                    "BetterCLI's saved version-check data is invalid. Connect to the "
                    "internet to verify the App Store version before continuing."
                ),
            )

        cached_version = cache.get("store_version")
        if isinstance(cached_version, str):
            try:
                if _version_key(cached_version) > current_key:
                    return VersionCheckResult(
                        allowed=False,
                        store_version=cached_version,
                        message=(
                            f"BetterCLI {cached_version} is available in the App Store. "
                            f"This copy is {current_version}; update before continuing."
                        ),
                    )
            except ValueError:
                log.warning("Ignoring invalid cached App Store version %r", cached_version)

        checked_at = _parse_timestamp(cache.get("checked_at"))
        offline_since = _parse_timestamp(cache.get("offline_since"))
        if cache_exists and checked_at is None and offline_since is None:
            return VersionCheckResult(
                allowed=False,
                message=(
                    "BetterCLI's saved version-check data is invalid. Connect to the "
                    "internet to verify the App Store version before continuing."
                ),
            )
        grace_started = checked_at or offline_since
        if grace_started is not None and grace_started > now:
            return VersionCheckResult(
                allowed=False,
                message=(
                    "BetterCLI's saved version-check date is invalid. Connect to the "
                    "internet to verify the App Store version before continuing."
                ),
            )
        if grace_started is None:
            offline_since = now
            if not _write_cache(
                cache_path,
                {"offline_since": offline_since.isoformat()},
            ):
                return VersionCheckResult(
                    allowed=False,
                    message=(
                        "BetterCLI cannot verify its version or save an offline grace period. "
                        "Connect to the internet and try again."
                    ),
                )
            return VersionCheckResult(allowed=True)

        grace_remaining = OFFLINE_GRACE_PERIOD - (now - grace_started)
        if timedelta(0) <= grace_remaining:
            return VersionCheckResult(allowed=True)
        return VersionCheckResult(
            allowed=False,
            message=(
                "BetterCLI could not verify its App Store version within the 28-day "
                "offline grace period. Connect to the internet to continue."
            ),
        )

    cache_value = {
        "checked_at": now.isoformat(),
        "store_version": store_version,
    }
    is_newer = _version_key(store_version) > current_key
    cache_saved = _write_cache(cache_path, cache_value)
    if is_newer:
        return VersionCheckResult(
            allowed=False,
            store_version=store_version,
            message=(
                f"BetterCLI {store_version} is available in the App Store. "
                f"This copy is {current_version}; update before continuing."
            ),
        )
    if not cache_saved:
        return VersionCheckResult(
            allowed=False,
            message=(
                "BetterCLI verified its App Store version but could not save the "
                "verification date. Check the app's data-folder permissions and try again."
            ),
        )
    return VersionCheckResult(allowed=True, store_version=store_version)
