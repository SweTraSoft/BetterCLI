from __future__ import annotations

import pytest

from cligui.discovery import DiscoveryError, split_command
from cligui.discovery.runner import clean_text, looks_like_help, resolve_binary


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
