from __future__ import annotations

from types import SimpleNamespace

import pytest

from cligui.cache import SpecCache, make_key
from cligui.discovery import DiscoveryError, split_command
from cligui.discovery.runner import (
    HelpCapture,
    clean_text,
    fingerprint_binary,
    looks_like_help,
    resolve_binary,
)
from cligui.discovery.service import DiscoveryService
from cligui.model.spec import CommandSpec


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


class TestTextCleanup:
    def test_strips_ansi_colour(self):
        assert clean_text("\x1b[1;31mred\x1b[0m") == "red"

    def test_strips_man_overstrike(self):
        assert clean_text("N\x08NA\x08AM\x08ME\x08E") == "NAME"

    def test_normalises_line_endings(self):
        assert clean_text("a\r\nb") == "a\nb"


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
