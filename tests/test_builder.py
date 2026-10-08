from __future__ import annotations

import pytest

from cligui.builder import BuildError, FormValues, build_argv, missing_required, preview
from cligui.model.spec import CommandSpec, Joiner, OptionKind, OptionSpec, PositionalSpec


def spec(**kwargs) -> CommandSpec:
    kwargs.setdefault("argv_prefix", ["tool"])
    return CommandSpec(**kwargs)


class TestFlags:
    def test_true_emits_token(self):
        s = spec(options=[OptionSpec(short="-v", long="--verbose")])
        assert build_argv(s, FormValues(options={"--verbose": True})) == [
            "tool",
            "--verbose",
        ]

    def test_false_is_omitted(self):
        s = spec(options=[OptionSpec(long="--verbose")])
        assert build_argv(s, FormValues(options={"--verbose": False})) == ["tool"]

    def test_negatable_false_emits_no_form(self):
        s = spec(options=[OptionSpec(long="--color", negatable=True)])
        assert build_argv(s, FormValues(options={"--color": False})) == [
            "tool",
            "--no-color",
        ]

    def test_short_only_flag_uses_short(self):
        s = spec(options=[OptionSpec(short="-l")])
        assert build_argv(s, FormValues(options={"-l": True})) == ["tool", "-l"]


class TestValues:
    def test_space_joiner(self):
        s = spec(options=[OptionSpec(long="--out", kind=OptionKind.PATH_FILE)])
        assert build_argv(s, FormValues(options={"--out": "a.txt"})) == [
            "tool",
            "--out",
            "a.txt",
        ]

    def test_equals_joiner(self):
        s = spec(
            options=[
                OptionSpec(long="--out", kind=OptionKind.STRING, joiner=Joiner.EQUALS)
            ]
        )
        assert build_argv(s, FormValues(options={"--out": "a.txt"})) == [
            "tool",
            "--out=a.txt",
        ]

    def test_equals_joiner_falls_back_to_space_for_short_options(self):
        s = spec(
            options=[
                OptionSpec(short="-o", kind=OptionKind.STRING, joiner=Joiner.EQUALS)
            ]
        )
        assert build_argv(s, FormValues(options={"-o": "a"})) == ["tool", "-o", "a"]

    def test_blank_value_is_omitted(self):
        s = spec(options=[OptionSpec(long="--out", kind=OptionKind.STRING)])
        assert build_argv(s, FormValues(options={"--out": "   "})) == ["tool"]

    def test_value_with_spaces_stays_one_token(self):
        s = spec(options=[OptionSpec(long="--msg", kind=OptionKind.STRING)])
        argv = build_argv(s, FormValues(options={"--msg": "hello world; rm -rf /"}))
        assert argv == ["tool", "--msg", "hello world; rm -rf /"]

    def test_count_repeats_short_form(self):
        s = spec(options=[OptionSpec(short="-v", long="--verbose", kind=OptionKind.COUNT)])
        assert build_argv(s, FormValues(options={"--verbose": 3})) == [
            "tool",
            "-v",
            "-v",
            "-v",
        ]

    def test_zero_count_is_omitted(self):
        s = spec(options=[OptionSpec(short="-v", kind=OptionKind.COUNT)])
        assert build_argv(s, FormValues(options={"-v": 0})) == ["tool"]

    def test_multi_repeats_the_option(self):
        s = spec(options=[OptionSpec(long="--tag", kind=OptionKind.MULTI)])
        assert build_argv(s, FormValues(options={"--tag": ["a", "b"]})) == [
            "tool",
            "--tag",
            "a",
            "--tag",
            "b",
        ]

    def test_single_value_option_ignores_extra_entries(self):
        s = spec(options=[OptionSpec(long="--out", kind=OptionKind.STRING)])
        assert build_argv(s, FormValues(options={"--out": ["a", "b"]})) == [
            "tool",
            "--out",
            "a",
        ]


class TestPositionals:
    def test_order_follows_the_spec(self):
        s = spec(
            positionals=[
                PositionalSpec(name="src"),
                PositionalSpec(name="dest", required=False),
            ]
        )
        values = FormValues(positionals={"dest": "b", "src": "a"})
        assert build_argv(s, values) == ["tool", "a", "b"]

    def test_variadic_keeps_every_entry(self):
        s = spec(positionals=[PositionalSpec(name="files", variadic=True)])
        values = FormValues(positionals={"files": ["a", "b", "c"]})
        assert build_argv(s, values) == ["tool", "a", "b", "c"]

    def test_dash_leading_positional_gets_separator(self):
        s = spec(positionals=[PositionalSpec(name="pattern")])
        assert build_argv(s, FormValues(positionals={"pattern": "-x"})) == [
            "tool",
            "--",
            "-x",
        ]

    def test_options_precede_positionals(self):
        s = spec(
            options=[OptionSpec(long="--count", kind=OptionKind.INT)],
            positionals=[PositionalSpec(name="src")],
        )
        values = FormValues(options={"--count": "2"}, positionals={"src": "f"})
        assert build_argv(s, values) == ["tool", "--count", "2", "f"]


class TestRequired:
    def test_missing_required_option_blocks_build(self):
        s = spec(options=[OptionSpec(long="--out", kind=OptionKind.STRING, required=True)])
        with pytest.raises(BuildError, match="--out"):
            build_argv(s, FormValues())

    def test_missing_required_positional_blocks_build(self):
        s = spec(positionals=[PositionalSpec(name="src")])
        with pytest.raises(BuildError, match="src"):
            build_argv(s, FormValues())

    def test_missing_required_reports_every_field(self):
        s = spec(
            options=[OptionSpec(long="--out", kind=OptionKind.STRING, required=True)],
            positionals=[PositionalSpec(name="src")],
        )
        assert missing_required(s, FormValues()) == ["--out", "src"]


class TestExtras:
    def test_extra_arguments_are_appended_verbatim(self):
        s = spec()
        assert build_argv(s, FormValues(extra=["--undocumented", "x"])) == [
            "tool",
            "--undocumented",
            "x",
        ]


class TestPreview:
    def test_quotes_values_that_need_it(self):
        assert preview(["tool", "--msg", "a b"]) == "tool --msg 'a b'"

    def test_round_trips_simple_commands(self):
        assert preview(["ls", "-la"]) == "ls -la"
