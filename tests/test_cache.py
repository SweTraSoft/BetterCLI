from __future__ import annotations

from pathlib import Path

import pytest

from cligui.cache import SpecCache, make_key
from cligui.model.spec import PARSER_VERSION, CommandSpec, OptionSpec


@pytest.fixture
def spec() -> CommandSpec:
    return CommandSpec(argv_prefix=["tool"], options=[OptionSpec(long="--verbose")])


class TestSpecCache:
    def test_round_trip(self, tmp_path: Path, spec):
        cache = SpecCache(tmp_path)
        cache.store("abc", spec)
        loaded = cache.load("abc")
        assert loaded is not None
        assert loaded.options[0].long == "--verbose"

    def test_miss_returns_none(self, tmp_path: Path):
        assert SpecCache(tmp_path).load("nope") is None

    def test_corrupt_entry_is_discarded(self, tmp_path: Path):
        (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
        cache = SpecCache(tmp_path)
        assert cache.load("bad") is None
        assert not (tmp_path / "bad.json").exists()

    def test_stale_parser_version_is_discarded(self, tmp_path: Path, spec):
        spec.parser_version = PARSER_VERSION - 1
        cache = SpecCache(tmp_path)
        cache.store("old", spec)
        assert cache.load("old") is None

    def test_clear_removes_entries(self, tmp_path: Path, spec):
        cache = SpecCache(tmp_path)
        cache.store("a", spec)
        cache.store("b", spec)
        assert cache.clear() == 2
        assert cache.load("a") is None


class TestCacheKey:
    def test_version_change_changes_key(self, tmp_path: Path):
        binary = tmp_path / "tool"
        a = make_key(["tool"], binary, "1.0")
        b = make_key(["tool"], binary, "2.0")
        assert a != b

    def test_subcommand_changes_key(self, tmp_path: Path):
        binary = tmp_path / "git"
        assert make_key(["git"], binary, "1") != make_key(["git", "log"], binary, "1")

    def test_same_inputs_are_stable(self, tmp_path: Path):
        binary = tmp_path / "tool"
        assert make_key(["tool"], binary, "1") == make_key(["tool"], binary, "1")