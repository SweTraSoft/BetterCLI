from __future__ import annotations

import pytest

from cligui.discovery.confidence import needs_llm, score
from cligui.discovery.heuristic import parse_help
from cligui.model.spec import Joiner, OptionKind


def parse(help_text, name, argv_prefix):
    return parse_help(help_text(name), argv_prefix)


class TestSyntheticArgparse:
    @pytest.fixture
    def result(self, help_text):
        return parse(help_text, "synthetic_argparse", ["demo"])

    def test_usage_line_captured(self, result):
        assert result.spec.usage_line.startswith("demo [-h]")

    def test_pairs_short_and_long_forms(self, result):
        opt = result.spec.option_by_name("--output")
        assert opt.short == "-o"
        assert opt.metavar == "FILE"
        assert opt.kind is OptionKind.PATH_FILE

    def test_plain_flag(self, result):
        opt = result.spec.option_by_name("--help")
        assert opt.kind is OptionKind.FLAG
        assert opt.help == "show this help message and exit"

    def test_repeated_flag_becomes_count(self, result):
        opt = result.spec.option_by_name("--verbose")
        assert opt.kind is OptionKind.COUNT
        assert opt.repeatable

    def test_choices(self, result):
        opt = result.spec.option_by_name("--format")
        assert opt.kind is OptionKind.CHOICE
        assert opt.choices == ["json", "yaml", "toml"]
        assert opt.default == "json"

    def test_numeric_metavars(self, result):
        assert result.spec.option_by_name("--retries").kind is OptionKind.INT
        assert result.spec.option_by_name("--threshold").kind is OptionKind.FLOAT

    def test_directory_metavar(self, result):
        assert result.spec.option_by_name("--workdir").kind is OptionKind.PATH_DIR

    def test_variadic_option_is_multi(self, result):
        opt = result.spec.option_by_name("--include")
        assert opt.kind is OptionKind.MULTI
        assert opt.repeatable

    def test_negatable_flag(self, result):
        assert result.spec.option_by_name("--color").negatable

    def test_positionals_from_usage(self, result):
        names = [(p.name, p.required) for p in result.spec.positionals]
        assert names == [("source", True), ("dest", False)]

    def test_confidence_is_high(self, result):
        assert score(result.stats) > 0.8
        assert not needs_llm(result.stats)


class TestSyntheticClick:
    @pytest.fixture
    def result(self, help_text):
        return parse(help_text, "synthetic_click", ["tool"])

    def test_option_count(self, result):
        assert len(result.spec.options) == 8

    def test_path_option(self, result):
        opt = result.spec.option_by_name("--config")
        assert opt.kind is OptionKind.PATH_FILE
        assert opt.short == "-c"
        assert opt.default == "tool.toml"

    def test_integer_option(self, result):
        assert result.spec.option_by_name("--port").kind is OptionKind.INT
        assert result.spec.option_by_name("--port").default == "8080"

    def test_bracketed_choices(self, result):
        opt = result.spec.option_by_name("--mode")
        assert opt.kind is OptionKind.CHOICE
        assert opt.choices == ["fast", "safe"]

    def test_repeatable_from_description(self, result):
        assert result.spec.option_by_name("--tag").repeatable

    def test_uppercase_positionals(self, result):
        names = [p.name for p in result.spec.positionals]
        assert names == ["SRC", "DEST"]

    def test_confident(self, result):
        assert not needs_llm(result.stats)


class TestRealWorldHelp:
    @pytest.mark.parametrize(
        ("fixture", "argv", "minimum"),
        [
            ("curl", ["curl"], 10),
            ("curl_all", ["curl"], 150),
            ("tar", ["tar"], 5),
            ("rsync", ["rsync"], 0),
        ],
    )
    def test_finds_options(self, help_text, fixture, argv, minimum):
        result = parse(help_text, fixture, argv)
        assert len(result.spec.options) >= minimum

    @pytest.mark.parametrize("fixture", ["grep", "ssh", "rsync"])
    def test_usage_only_help_is_low_confidence(self, help_text, fixture):
        result = parse(help_text, fixture, [fixture])
        assert result.spec.usage_line is not None
        assert needs_llm(result.stats)

    def test_equals_joiner_is_preserved(self, help_text):
        result = parse(help_text, "curl_all", ["curl"])
        opt = result.spec.option_by_name("--data")
        assert opt is not None
        assert opt.kind is OptionKind.STRING

    def test_man_page_style_is_parsed(self, help_text):
        result = parse(help_text, "git_log", ["git", "log"])
        assert result.spec.option_by_name("--oneline") is not None
        assert len(result.spec.options) > 50

    def test_never_emits_option_without_a_name(self, help_text):
        for fixture, argv in [
            ("curl_all", ["curl"]),
            ("rsync", ["rsync"]),
            ("git_log", ["git", "log"]),
            ("tar", ["tar"]),
        ]:
            result = parse(help_text, fixture, argv)
            for opt in result.spec.options:
                assert opt.short or opt.long
                assert opt.name.startswith("-")


class TestSubcommands:
    @pytest.fixture
    def openclaw(self, help_text):
        return parse(help_text, "openclaw", ["openclaw"])

    def test_finds_every_listed_command(self, openclaw):
        names = [s.name for s in openclaw.spec.subcommands]
        assert "doctor" in names
        assert "gateway" in names
        assert len(names) > 50

    def test_captures_descriptions(self, openclaw):
        doctor = next(s for s in openclaw.spec.subcommands if s.name == "doctor")
        assert "Health checks" in doctor.help

    def test_marks_nested_commands(self, openclaw):
        by_name = {s.name: s for s in openclaw.spec.subcommands}
        assert by_name["channels"].has_children
        assert not by_name["doctor"].has_children

    def test_does_not_leak_other_sections(self, openclaw):
        names = [s.name for s in openclaw.spec.subcommands]
        assert not any(n.startswith("openclaw") for n in names)
        assert "Hint" not in names
        assert not any(n.startswith("-") for n in names)

    def test_options_still_parsed_alongside(self, openclaw):
        assert openclaw.spec.option_by_name("--profile") is not None

    def test_wrapped_descriptions_are_joined(self, openclaw):
        agent = next(s for s in openclaw.spec.subcommands if s.name == "agent")
        assert "embedded" in agent.help

    def test_generic_commands_section(self):
        text = (
            "Usage: tool <command>\n"
            "\n"
            "Available Commands:\n"
            "  build       Build the project\n"
            "  test        Run the tests\n"
            "\n"
            "Flags:\n"
            "  -v, --verbose   be loud\n"
        )
        spec = parse_help(text, ["tool"]).spec
        assert [s.name for s in spec.subcommands] == ["build", "test"]
        assert spec.option_by_name("--verbose") is not None

    def test_argparse_choice_group_becomes_subcommands(self):
        text = "usage: tool [-h] {add,remove,list} ...\n\noptions:\n  -h, --help  show help\n"
        spec = parse_help(text, ["tool"]).spec
        assert [s.name for s in spec.subcommands] == ["add", "remove", "list"]

    def test_commands_are_not_turned_into_positionals(self):
        text = "usage: tool [-h] {add,remove} ...\n"
        spec = parse_help(text, ["tool"]).spec
        assert [p.name for p in spec.positionals] == []

    def test_no_subcommands_for_flat_tools(self, help_text):
        assert parse(help_text, "curl_all", ["curl"]).spec.subcommands == []


class TestEdgeCases:
    def test_empty_text(self):
        result = parse_help("", ["x"])
        assert result.spec.options == []
        assert score(result.stats) == 0.0

    def test_equals_metavar(self):
        result = parse_help("Options:\n  --out=FILE   write here\n", ["x"])
        opt = result.spec.option_by_name("--out")
        assert opt.joiner is Joiner.EQUALS
        assert opt.metavar == "FILE"

    def test_slash_separated_forms(self):
        result = parse_help("Options:\n  -h/--help   show help\n", ["x"])
        opt = result.spec.option_by_name("--help")
        assert opt.short == "-h"

    def test_end_of_options_marker_ignored(self):
        result = parse_help("Options:\n  --   end of options\n", ["x"])
        assert result.spec.options == []

    def test_usage_block_is_not_mined_for_options(self):
        text = "usage: x [--alpha] [--beta]\n\nOptions:\n  --alpha   only this one\n"
        result = parse_help(text, ["x"])
        assert [o.name for o in result.spec.options] == ["--alpha"]


def test_every_usage_form_contributes_positionals():
    text = (
        "usage: cp [-R [-H | -L | -P]] [-fi | -n] [-aclpSsvXx] source_file target_file\n"
        "       cp [-R [-H | -L | -P]] [-fi | -n] [-aclpSsvXx] source_file ... target_directory\n"
    )
    spec = parse_help(text, ["cp"]).spec
    assert [(p.name, p.kind, p.required, p.variadic) for p in spec.positionals] == [
        ("source_file", OptionKind.PATH_FILE, True, True),
        ("target_file", OptionKind.PATH_FILE, False, False),
        ("target_directory", OptionKind.PATH_DIR, False, False),
    ]
