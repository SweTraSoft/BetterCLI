from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import subprocess

import pytest

from cligui.cache import SpecCache, make_key
from cligui.discovery import DiscoveryError, split_command
from cligui.discovery.runner import (
    HelpCapture,
    capture_candidates,
    clean_text,
    fingerprint_binary,
    looks_like_help,
    resolve_binary,
)
from cligui.discovery.service import DiscoveryService
from cligui.model.spec import CommandSpec
from cligui.discovery import runner


class TestSplitCommand:
    def test_simple(self):
        assert split_command("rsync") == ["rsync"]

    def test_subcommand(self):
        assert split_command("  git log ") == ["git", "log"]

    def test_quoted_segment(self):
        assert split_command('tool "two words"') == ["tool", "two words"]

    @pytest.mark.parametrize(
        "text",
        [
            "",
            "   ",
            "ls | grep x",
            "ls && rm -rf /",
            "echo $(whoami)",
            "cat f > out",
            "ls; pwd",
            "echo `id`",
        ],
    )
    def test_rejects_shell_syntax_and_blanks(self, text):
        with pytest.raises(DiscoveryError):
            split_command(text)

    def test_rejects_options(self):
        with pytest.raises(DiscoveryError, match="options are configured"):
            split_command("ls -la")

    def test_unbalanced_quotes(self):
        with pytest.raises(DiscoveryError):
            split_command('tool "unclosed')


class TestResolveBinary:
    def test_finds_a_real_binary(self):
        assert resolve_binary("ls").name == "ls"

    def test_missing_binary(self):
        with pytest.raises(DiscoveryError, match="PATH"):
            resolve_binary("definitely-not-a-real-command-xyz")

    @pytest.mark.parametrize("name", ["", "--help", "-x"])
    def test_rejects_non_commands(self, name):
        with pytest.raises(DiscoveryError):
            resolve_binary(name)

    def test_rejects_non_executable_path(self, tmp_path):
        target = tmp_path / "data.txt"
        target.write_text("x", encoding="utf-8")
        with pytest.raises(DiscoveryError, match="executable"):
            resolve_binary(str(target))

    @pytest.mark.parametrize("command", ["git", "make"])
    @pytest.mark.parametrize(
        "developer_directory",
        ["/Applications/Custom Xcode.app/Contents/Developer", "/Library/Developer/CommandLineTools"],
    )
    def test_apple_launchers_use_selected_developer_tools(
        self, monkeypatch, command, developer_directory
    ):
        monkeypatch.setattr(runner.sys, "platform", "darwin")
        monkeypatch.setattr(runner.shutil, "which", lambda _name: f"/usr/bin/{command}")
        selected = Path(developer_directory) / "usr" / "bin" / command
        monkeypatch.setattr(Path, "is_file", lambda path: path == selected)
        monkeypatch.setattr(runner.os, "access", lambda path, _mode: path == selected)
        calls = []

        def select(argv, **kwargs):
            calls.append(argv)
            assert kwargs["stdin"] is subprocess.DEVNULL
            assert kwargs["timeout"] > 0
            return SimpleNamespace(returncode=0, stdout=developer_directory + "\n", stderr="")

        monkeypatch.setattr(runner.subprocess, "run", select)
        assert resolve_binary(command) == selected
        assert calls == [["/usr/bin/xcode-select", "--print-path"]]

    @pytest.mark.parametrize("platform", ["darwin", "linux"])
    def test_custom_git_is_not_replaced(self, monkeypatch, tmp_path, platform):
        binary = tmp_path / "git"
        binary.touch()
        binary.chmod(0o755)
        monkeypatch.setattr(runner.sys, "platform", platform)
        monkeypatch.setattr(runner.shutil, "which", lambda _name: str(binary))
        monkeypatch.setattr(
            runner.subprocess, "run",
            lambda *_args, **_kwargs: pytest.fail("Custom installations must not invoke xcode-select"),
        )
        assert resolve_binary("git") == binary.resolve()
        assert resolve_binary(str(binary)) == binary.resolve()

    def test_explicit_launcher_path_is_preserved(self, monkeypatch):
        monkeypatch.setattr(Path, "is_file", lambda _path: True)
        monkeypatch.setattr(runner.os, "access", lambda *_args: True)
        monkeypatch.setattr(
            runner.subprocess, "run",
            lambda *_args, **_kwargs: pytest.fail("Explicit paths must not invoke xcode-select"),
        )
        assert resolve_binary("/usr/bin/git") == Path("/usr/bin/git").resolve()

    def test_developer_selection_failure_is_explicit(self, monkeypatch):
        monkeypatch.setattr(runner.sys, "platform", "darwin")
        monkeypatch.setattr(runner.shutil, "which", lambda _name: "/usr/bin/git")
        monkeypatch.setattr(
            runner.subprocess, "run",
            lambda *_args, **_kwargs: SimpleNamespace(
                returncode=1, stdout="", stderr="xcode-select: no active developer directory",
            ),
        )
        with pytest.raises(DiscoveryError, match="no active developer directory"):
            resolve_binary("git")

    def test_missing_selected_tool_is_explicit(self, monkeypatch):
        monkeypatch.setattr(runner.sys, "platform", "darwin")
        monkeypatch.setattr(runner.shutil, "which", lambda _name: "/usr/bin/make")
        monkeypatch.setattr(Path, "is_file", lambda _path: False)
        monkeypatch.setattr(
            runner.subprocess, "run",
            lambda *_args, **_kwargs: SimpleNamespace(
                returncode=0, stdout="/missing/developer", stderr="",
            ),
        )
        with pytest.raises(DiscoveryError, match="not an executable"):
            resolve_binary("make")


def test_capture_uses_resolved_binary_for_version_and_help(tmp_path, monkeypatch):
    binary = tmp_path / "git"
    binary.touch()
    calls = []
    monkeypatch.setattr(runner, "resolve_binary", lambda _name: binary)
    monkeypatch.setattr(runner, "capture_man_page", lambda *_args: None)

    def run(argv, *_args):
        calls.append(argv)
        if argv[1] == "--version":
            return 0, "git version 2.50.1"
        return 0, "usage: git [options] <command>\n  --help  Show help information"

    monkeypatch.setattr(runner, "_run", run)
    captures = capture_candidates(["git"])
    assert captures[0].version == "git version 2.50.1"
    assert all(argv[0] == str(binary) for argv in calls)


def test_failed_help_scan_preserves_underlying_errors(tmp_path, monkeypatch):
    binary = tmp_path / "git"
    binary.touch()
    monkeypatch.setattr(runner, "resolve_binary", lambda _name: binary)
    monkeypatch.setattr(runner, "detect_version", lambda *_args: None)
    monkeypatch.setattr(runner, "capture_man_page", lambda *_args: None)

    def run(argv, *_args):
        if argv[1] == "--help":
            raise DiscoveryError("Operation not permitted")
        return 1, "developer tool launcher failed"

    monkeypatch.setattr(runner, "_run", run)
    with pytest.raises(DiscoveryError) as error:
        capture_candidates(["git"])
    assert "Operation not permitted" in str(error.value)
    assert "developer tool launcher failed" in str(error.value)


class TestTextCleanup:
    def test_strips_ansi_colour(self):
        assert clean_text("\x1b[1;31mred\x1b[0m") == "red"

    def test_strips_man_overstrike(self):
        assert clean_text("N\x08NA\x08AM\x08ME\x08E") == "NAME"

    def test_normalises_line_endings(self):
        assert clean_text("a\r\nb") == "a\nb"

    def test_capture_keeps_colored_display_text_and_clean_parser_text(
        self, tmp_path, monkeypatch
    ):
        import cligui.discovery.runner as runner

        binary = tmp_path / "tool"
        binary.write_text("", encoding="utf-8")
        colored = (
            "\x1b[31mUsage: tool --flag\n  --flag  "
            + ("description " * 4)
            + "\x1b[0m"
        )
        monkeypatch.setattr(runner, "resolve_binary", lambda _name: binary)
        monkeypatch.setattr(runner, "detect_version", lambda *_args: None)
        monkeypatch.setattr(runner, "_run", lambda *_args: (0, colored))

        capture = capture_candidates(["tool", "sub"])[0]

        assert capture.display_text == colored
        assert capture.text == clean_text(colored)


class TestDiscoveryCache:
    def test_fast_cache_hit_skips_help_capture(self, tmp_path, monkeypatch):
        binary = tmp_path / "tool"
        binary.write_text("#!/bin/sh\n", encoding="utf-8")
        binary.chmod(0o755)
        argv_prefix = [str(binary)]
        cache = SpecCache(tmp_path / "cache")
        cached_spec = CommandSpec(argv_prefix=argv_prefix)
        fast_key = make_key(argv_prefix, binary, fingerprint_binary(binary, None))
        cache.store(fast_key, cached_spec)
        service = DiscoveryService(cache=cache)

        def fail_if_captured(*args, **kwargs):
            raise AssertionError("help capture should be skipped for a fast cache hit")

        monkeypatch.setattr(
            "cligui.discovery.service.capture_candidates", fail_if_captured
        )

        result = service.discover(argv_prefix)

        assert result.from_cache
        assert result.spec.argv_prefix == argv_prefix

    def test_discovery_populates_fast_cache_key(self, tmp_path, monkeypatch):
        binary = tmp_path / "tool"
        binary.write_text("#!/bin/sh\n", encoding="utf-8")
        binary.chmod(0o755)
        argv_prefix = [str(binary)]
        cache = SpecCache(tmp_path / "cache")
        service = DiscoveryService(cache=cache)
        parsed = SimpleNamespace(spec=CommandSpec(argv_prefix=argv_prefix), stats=object())
        capture = HelpCapture(
            text="Usage: tool",
            origin="--help",
            binary=binary,
            fingerprint="1.0",
            version="1.0",
        )
        monkeypatch.setattr(
            "cligui.discovery.service.capture_candidates",
            lambda *args, **kwargs: [capture],
        )
        monkeypatch.setattr(
            "cligui.discovery.service.heuristic.parse_help",
            lambda *args: parsed,
        )
        monkeypatch.setattr(
            "cligui.discovery.service.confidence.score", lambda stats: 1.0
        )
        monkeypatch.setattr(
            "cligui.discovery.service.confidence.needs_llm",
            lambda stats: False,
        )

        service.discover(argv_prefix)

        fast_key = make_key(argv_prefix, binary, fingerprint_binary(binary, None))
        assert cache.load(fast_key) is not None


class TestLooksLikeHelp:
    def test_accepts_usage_text(self):
        assert looks_like_help("usage: tool [options]\n  --flag   do a thing\n")

    def test_accepts_an_option_list(self):
        assert looks_like_help(
            "  -a   enable the first behaviour\n"
            "  -b   enable the second behaviour\n"
        )

    @pytest.mark.parametrize(
        "text", ["", "error", "command not found", "zsh: no such file or directory"]
    )
    def test_rejects_short_noise(self, text):
        assert not looks_like_help(text)
