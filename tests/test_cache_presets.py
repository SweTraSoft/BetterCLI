from __future__ import annotations

from pathlib import Path

import pytest

from cligui.builder import FormValues
from cligui.cache import SpecCache, make_key
from cligui.model.spec import PARSER_VERSION, CommandSpec, OptionSpec
from cligui.presets import PresetStore


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


class TestPresetStore:
    def test_save_and_load(self, tmp_path: Path):
        store = PresetStore(tmp_path)
        values = FormValues(options={"--verbose": True}, positionals={"src": "a.txt"})
        store.save(["tool"], "My Preset", values)
        loaded = store.load(["tool"], "My Preset")
        assert loaded is not None
        assert loaded.options == {"--verbose": True}
        assert loaded.positionals == {"src": "a.txt"}

    def test_names_are_listed(self, tmp_path: Path):
        store = PresetStore(tmp_path)
        store.save(["tool"], "beta", FormValues())
        store.save(["tool"], "alpha", FormValues())
        assert store.names(["tool"]) == ["alpha", "beta"]

    def test_presets_are_scoped_per_command(self, tmp_path: Path):
        store = PresetStore(tmp_path)
        store.save(["git", "log"], "mine", FormValues())
        assert store.names(["git", "log"]) == ["mine"]
        assert store.names(["git", "diff"]) == []

    def test_delete(self, tmp_path: Path):
        store = PresetStore(tmp_path)
        store.save(["tool"], "x", FormValues())
        assert store.delete(["tool"], "x")
        assert not store.delete(["tool"], "x")

    def test_path_traversal_in_name_is_neutralised(self, tmp_path: Path):
        store = PresetStore(tmp_path)
        store.save(["tool"], "../../escape", FormValues())
        written = list(tmp_path.rglob("*.json"))
        assert len(written) == 1
        assert tmp_path in written[0].parents

    def test_missing_preset_returns_none(self, tmp_path: Path):
        assert PresetStore(tmp_path).load(["tool"], "absent") is None
