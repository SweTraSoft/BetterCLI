from datetime import datetime, timedelta, timezone

import pytest

from cligui import updates


NOW = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)


def test_no_app_store_id_disables_check():
    result = updates.check_app_store_version("1.00", app_store_id=None)

    assert result.allowed
    assert result.store_version is None


def test_newer_store_version_blocks_and_is_cached(monkeypatch, tmp_path):
    cache_path = tmp_path / "version-check.json"
    monkeypatch.setattr(updates, "_fetch_store_version", lambda _store_id: "1.1")

    result = updates.check_app_store_version(
        "1.00", app_store_id=123, cache_path=cache_path, now=NOW
    )

    assert not result.allowed
    assert result.store_version == "1.1"
    assert "update before continuing" in result.message
    assert '"store_version": "1.1"' in cache_path.read_text(encoding="utf-8")


def test_current_version_blocks_if_successful_check_cannot_be_cached(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(updates, "_fetch_store_version", lambda _store_id: "1.00")
    monkeypatch.setattr(updates, "_write_cache", lambda *_args: False)

    result = updates.check_app_store_version(
        "1.00", app_store_id=123, cache_path=tmp_path / "cache.json", now=NOW
    )

    assert not result.allowed
    assert "could not save the verification date" in result.message


def test_equal_versions_ignore_trailing_zeroes(monkeypatch, tmp_path):
    monkeypatch.setattr(updates, "_fetch_store_version", lambda _store_id: "1.0.0")

    result = updates.check_app_store_version(
        "1.00", app_store_id=123, cache_path=tmp_path / "cache.json", now=NOW
    )

    assert result.allowed


def test_versions_ignore_any_number_of_trailing_zeroes():
    assert updates._version_key("1.0.0.0") == updates._version_key("1")


def test_offline_grace_starts_on_first_offline_launch(monkeypatch, tmp_path):
    monkeypatch.setattr(
        updates,
        "_fetch_store_version",
        lambda _store_id: (_ for _ in ()).throw(TimeoutError("offline")),
    )
    cache_path = tmp_path / "cache.json"

    result = updates.check_app_store_version(
        "1.00", app_store_id=123, cache_path=cache_path, now=NOW
    )

    assert result.allowed
    assert "offline_since" in cache_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("days_offline", [27, 28])
def test_offline_grace_allows_use_for_28_days(
    monkeypatch, tmp_path, days_offline
):
    monkeypatch.setattr(
        updates,
        "_fetch_store_version",
        lambda _store_id: (_ for _ in ()).throw(TimeoutError("offline")),
    )
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        f'{{"checked_at": "{(NOW - timedelta(days=days_offline)).isoformat()}", '
        '"store_version": "1.00"}',
        encoding="utf-8",
    )

    result = updates.check_app_store_version(
        "1.00", app_store_id=123, cache_path=cache_path, now=NOW
    )

    assert result.allowed


def test_offline_grace_blocks_after_28_days(monkeypatch, tmp_path):
    monkeypatch.setattr(
        updates,
        "_fetch_store_version",
        lambda _store_id: (_ for _ in ()).throw(TimeoutError("offline")),
    )
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        f'{{"checked_at": "{(NOW - timedelta(days=29)).isoformat()}", '
        '"store_version": "1.00"}',
        encoding="utf-8",
    )

    result = updates.check_app_store_version(
        "1.00", app_store_id=123, cache_path=cache_path, now=NOW
    )

    assert not result.allowed
    assert "28-day offline grace period" in result.message


def test_offline_cache_of_newer_version_still_blocks(monkeypatch, tmp_path):
    monkeypatch.setattr(
        updates,
        "_fetch_store_version",
        lambda _store_id: (_ for _ in ()).throw(TimeoutError("offline")),
    )
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(
        f'{{"checked_at": "{NOW.isoformat()}", "store_version": "1.1"}}',
        encoding="utf-8",
    )

    result = updates.check_app_store_version(
        "1.00", app_store_id=123, cache_path=cache_path, now=NOW
    )

    assert not result.allowed
    assert result.store_version == "1.1"


def test_invalid_cache_does_not_restart_offline_grace(monkeypatch, tmp_path):
    monkeypatch.setattr(
        updates,
        "_fetch_store_version",
        lambda _store_id: (_ for _ in ()).throw(TimeoutError("offline")),
    )
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}", encoding="utf-8")

    result = updates.check_app_store_version(
        "1.00", app_store_id=123, cache_path=cache_path, now=NOW
    )

    assert not result.allowed
    assert "saved version-check data is invalid" in result.message
