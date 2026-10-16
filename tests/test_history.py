from __future__ import annotations

import json
from pathlib import Path

import pytest

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

    def test_session_persists_with_command(self, tmp_path: Path):
        history = store(tmp_path)
        history.add("git log")
        history.update_session(
            "git log", command_line="git log --oneline", cwd="/tmp", output="commit\n"
        )
        history.add("git log")

        assert store(tmp_path).session("git log") == {
            "command": "git log",
            "command_line": "git log --oneline",
            "cwd": "/tmp",
            "output": "commit\n",
        }

    def test_sessions_keep_separate_output(self, tmp_path: Path):
        history = store(tmp_path)
        history.add("ls")
        history.add("pwd")
        history.update_session("ls", output="file.txt\n")
        history.update_session("pwd", output="/tmp\n")

        assert store(tmp_path).session("ls")["output"] == "file.txt\n"
        assert store(tmp_path).session("pwd")["output"] == "/tmp\n"

    def test_old_history_loads_with_empty_output(self, tmp_path: Path):
        path = tmp_path / "history.json"
        path.write_text('["ls", "git log"]', encoding="utf-8")

        history = CommandHistory(path)

        assert history.items() == ["ls", "git log"]
        assert history.session("git log")["output"] == ""

    def test_clear(self, tmp_path: Path):
        h = store(tmp_path)
        h.add("ls")
        h.record_usage("ls")
        h.clear()
        assert h.items() == []
        assert store(tmp_path).items() == []
        assert h.usage_count("ls") == 0
        assert store(tmp_path).usage_count("ls") == 0

    def test_usage_counts_runs_not_history_visits(self, tmp_path: Path):
        h = store(tmp_path)
        h.add("git log")
        h.add("git log")
        assert h.usage_count("git") == 0

        h.record_usage("git")
        h.record_usage("/usr/bin/git")
        h.record_usage("curl")

        reopened = store(tmp_path)
        assert reopened.usage_count("git") == 2
        assert reopened.usage_count("/opt/homebrew/bin/git") == 2
        assert reopened.usage_count("curl") == 1
        assert reopened.usage_count("ls") == 0

    def test_usage_survives_history_eviction(self, tmp_path: Path):
        h = store(tmp_path)
        h.add("git")
        h.record_usage("git")
        for i in range(MAX_ENTRIES):
            h.add(f"cmd{i}")

        reopened = store(tmp_path)
        assert "git" not in reopened.items()
        assert reopened.usage_count("git") == 1

    def test_legacy_history_has_no_invented_usage(self, tmp_path: Path):
        path = tmp_path / "history.json"
        path.write_text('["git log", "curl"]', encoding="utf-8")

        h = CommandHistory(path)

        assert h.items() == ["git log", "curl"]
        assert h.usage_count("git") == 0

    @pytest.mark.parametrize("invalid", [-1, 1.5, True, "5", None])
    def test_invalid_usage_counts_are_logged(self, tmp_path: Path, caplog, invalid):
        h = store(tmp_path)
        h.usage_path.write_text(
            json.dumps({"git": invalid, "curl": 3}), encoding="utf-8"
        )

        reopened = store(tmp_path)

        assert reopened.usage_count("git") == 0
        assert reopened.usage_count("curl") == 3
        assert "invalid command usage entry" in caplog.text

    @pytest.mark.parametrize("raw", ["{broken", "[]"])
    def test_invalid_usage_file_is_logged(self, tmp_path: Path, caplog, raw):
        h = store(tmp_path)
        h.usage_path.write_text(raw, encoding="utf-8")

        assert store(tmp_path).usage_count("git") == 0
        assert "command usage" in caplog.text

    def test_usage_write_failure_is_logged(self, tmp_path: Path, caplog):
        h = store(tmp_path)
        h.usage_path.mkdir()

        h.record_usage("git")

        assert h.usage_count("git") == 1
        assert "could not write command usage" in caplog.text

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
