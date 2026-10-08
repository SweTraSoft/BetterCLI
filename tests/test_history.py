from __future__ import annotations

from pathlib import Path

from cligui.history import MAX_ENTRIES, CommandHistory


def store(tmp_path: Path) -> CommandHistory:
    return CommandHistory(tmp_path / "history.json")


class TestCommandHistory:
    def test_starts_empty(self, tmp_path: Path):
        assert store(tmp_path).items() == []

    def test_most_recent_first(self, tmp_path: Path):
        h = store(tmp_path)
        h.add("ls")
        h.add("git log")
        assert h.items() == ["git log", "ls"]

    def test_reuse_moves_to_front_without_duplicating(self, tmp_path: Path):
        h = store(tmp_path)
        for command in ("ls", "tar", "ls"):
            h.add(command)
        assert h.items() == ["ls", "tar"]

    def test_capped_at_twenty(self, tmp_path: Path):
        h = store(tmp_path)
        for i in range(MAX_ENTRIES + 10):
            h.add(f"cmd{i}")
        assert len(h.items()) == MAX_ENTRIES
        assert h.items()[0] == f"cmd{MAX_ENTRIES + 9}"
        assert "cmd0" not in h.items()

    def test_whitespace_is_normalised(self, tmp_path: Path):
        h = store(tmp_path)
        h.add("  git   log  ")
        h.add("git log")
        assert h.items() == ["git log"]

    def test_blank_entries_ignored(self, tmp_path: Path):
        h = store(tmp_path)
        h.add("   ")
        h.add("")
        assert h.items() == []

    def test_persists_across_instances(self, tmp_path: Path):
        store(tmp_path).add("rsync")
        assert store(tmp_path).items() == ["rsync"]

    def test_clear(self, tmp_path: Path):
        h = store(tmp_path)
        h.add("ls")
        h.clear()
        assert h.items() == []
        assert store(tmp_path).items() == []

    def test_corrupt_file_is_ignored(self, tmp_path: Path):
        path = tmp_path / "history.json"
        path.write_text("{not json", encoding="utf-8")
        assert CommandHistory(path).items() == []

    def test_unexpected_shape_is_ignored(self, tmp_path: Path):
        path = tmp_path / "history.json"
        path.write_text('{"a": 1}', encoding="utf-8")
        assert CommandHistory(path).items() == []

    def test_non_string_entries_are_dropped(self, tmp_path: Path):
        path = tmp_path / "history.json"
        path.write_text('["ls", 42, null, "tar"]', encoding="utf-8")
        assert CommandHistory(path).items() == ["ls", "tar"]
