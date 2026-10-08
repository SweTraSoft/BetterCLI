"""Heuristic parser that turns `--help` output into a :class:`CommandSpec`.

It targets the conventions shared by argparse, click, getopt, docopt and
hand-rolled help text rather than any single framework, and reports statistics
so :mod:`cligui.discovery.confidence` can decide whether the LLM fallback is
needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from cligui.model.spec import (
    CommandSpec,
    Joiner,
    OptionKind,
    OptionSpec,
    PositionalSpec,
    SpecSource,
    SubcommandSpec,
)

_OPEN = "[({<"
_CLOSE = "])}>"

_USAGE_HEADER = re.compile(r"^\s*(usage|synopsis)\s*:?\s*", re.IGNORECASE)
_OPTION_LINE = re.compile(r"^\s*-{1,2}[A-Za-z0-9\[]")
_ALTERNATIVE = re.compile(
    r"^(?P<name>--?(?:\[no-\])?[A-Za-z0-9][A-Za-z0-9._+-]*)(?P<rest>.*)$"
)
_DEFAULT = re.compile(r"[\[(]default:?\s*(?P<value>[^\])]*)[\])]", re.IGNORECASE)
_REPEAT_HINT = re.compile(
    r"(repeat|multiple times|more than once|may be (given|used|specified)|"
    r"can be (given|used|specified) (multiple|more))",
    re.IGNORECASE,
)
_COUNT_HINT = re.compile(r"(increase|increment|more verbose|verbosity)", re.IGNORECASE)

_DIR_WORDS = {"DIR", "DIRECTORY", "FOLDER", "DIRNAME", "PREFIX", "WORKDIR", "CWD"}
_FILE_WORDS = {
    "FILE",
    "FILENAME",
    "PATH",
    "INFILE",
    "OUTFILE",
    "INPUT",
    "OUTPUT",
    "SRC",
    "SOURCE",
    "DEST",
    "DESTINATION",
    "TARGET",
    "CONFIG",
    "LOGFILE",
}
_INT_WORDS = {
    "N",
    "NUM",
    "NUMBER",
    "COUNT",
    "INT",
    "INTEGER",
    "SIZE",
    "PORT",
    "SECONDS",
    "SECS",
    "MS",
    "LEVEL",
    "DEPTH",
    "WIDTH",
    "HEIGHT",
    "BYTES",
    "LIMIT",
    "JOBS",
    "LINES",
    "RETRIES",
    "TIMEOUT",
}
_FLOAT_WORDS = {"FLOAT", "RATE", "RATIO", "SCALE", "FACTOR", "SPEED", "THRESHOLD"}

#: Usage-line tokens that stand in for other arguments rather than naming one.
_USAGE_PLACEHOLDERS = {
    "option",
    "options",
    "arg",
    "args",
    "argument",
    "arguments",
    "flag",
    "flags",
    "command",
    "commands",
    "subcommand",
    "params",
    "parameters",
}

#: argparse renders repeatable options as `--opt X [X ...]`.
_ARGPARSE_VARIADIC = re.compile(r"\s*\[\s*\S+\s*\.\.\.\s*\]$")

#: Section headers introducing a command list: "Commands:", "Available Commands:",
#: and git's "These are common Git commands used in various situations:".
_COMMAND_SECTION = re.compile(r"^\s*[^:]*\bcommands?\b[^:]*:\s*$", re.IGNORECASE)

#: A short "Label:" line, which ends a command section (git groups do not match).
_SECTION_END = re.compile(r"^\s*\S[\w \-/]{0,40}:\s*$")

#: Give up on a section after this many consecutive lines yield no command.
_SECTION_PATIENCE = 10

#: `doctor   Health checks`, optionally flagged with `*` for having nested commands.
#: The name must end alphanumerically so prose like "mirrors." is not mistaken for one.
_COMMAND_ENTRY = re.compile(
    r"^(?P<name>[A-Za-z][A-Za-z0-9._-]*[A-Za-z0-9]|[A-Za-z])"
    r"(?P<children>\s*\*)?"
    r"(?:\s{2,}(?P<help>\S.*))?$"
)

#: Words that appear in command sections but are not themselves commands.
_NOT_COMMANDS = {"hint", "note", "help", "usage", "see", "run"}


@dataclass
class ParseStats:
    """Signals about how well the text was understood."""

    usage_found: bool = False
    option_like_lines: int = 0
    consumed_lines: int = 0
    options: int = 0
    with_help: int = 0
    unparsed_samples: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    spec: CommandSpec
    stats: ParseStats


def _split_top_level(text: str, separators: str = ",|") -> list[str]:
    """Split on separators that are not nested inside brackets."""
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for char in text:
        if char in _OPEN:
            depth += 1
        elif char in _CLOSE:
            depth = max(0, depth - 1)
        if depth == 0 and char in separators:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(char)
    parts.append("".join(buf))

    out: list[str] = []
    for part in parts:
        piece = part.strip()
        if not piece:
            continue
        # `-h/--help` is a common shorthand for `-h, --help`.
        if re.match(r"^-\S+/--\S+$", piece):
            out.extend(piece.split("/"))
        else:
            out.append(piece)
    return out


def _tokenize_usage(text: str) -> list[str]:
    tokens: list[str] = []
    buf: list[str] = []
    depth = 0
    for char in text:
        if char in _OPEN:
            depth += 1
        elif char in _CLOSE:
            depth = max(0, depth - 1)
        if char.isspace() and depth == 0:
            if buf:
                tokens.append("".join(buf))
                buf = []
        else:
            buf.append(char)
    if buf:
        tokens.append("".join(buf))
    return tokens


def _clean_metavar(raw: str) -> tuple[str | None, list[str], bool]:
    """Return ``(metavar, choices, variadic)`` from a raw usage fragment."""
    text = raw.strip()
    variadic = False
    collapsed = _ARGPARSE_VARIADIC.sub("", text)
    if collapsed != text:
        text = collapsed.strip()
        variadic = True
    while text.endswith("..."):
        text = text[:-3].strip()
        variadic = True
    while text and text[0] in _OPEN and text[-1] in _CLOSE:
        text = text[1:-1].strip()
        while text.endswith("..."):
            text = text[:-3].strip()
            variadic = True
    if not text:
        return None, [], variadic
    choices = [c for c in _split_top_level(text, ",|") if c] if "," in text or "|" in text else []
    if len(choices) > 1:
        return text, choices, variadic
    return text, [], variadic


def _infer_kind(metavar: str | None, choices: list[str], variadic: bool) -> OptionKind:
    if choices:
        return OptionKind.CHOICE
    if metavar is None:
        return OptionKind.FLAG
    if variadic:
        return OptionKind.MULTI
    word = re.sub(r"[^A-Za-z]", "", metavar).upper()
    if word in _DIR_WORDS:
        return OptionKind.PATH_DIR
    if word in _FILE_WORDS:
        return OptionKind.PATH_FILE
    if word in _INT_WORDS:
        return OptionKind.INT
    if word in _FLOAT_WORDS:
        return OptionKind.FLOAT
    return OptionKind.STRING


def _parse_head(head: str) -> OptionSpec | None:
    short: str | None = None
    long: str | None = None
    metavar: str | None = None
    choices: list[str] = []
    joiner = Joiner.SPACE
    negatable = False
    variadic = False

    for alt in _split_top_level(head, ","):
        match = _ALTERNATIVE.match(alt)
        if not match:
            continue
        name = match.group("name")
        rest = match.group("rest")
        if "[no-]" in name:
            negatable = True
            name = name.replace("[no-]", "")
        if rest.lstrip().startswith("="):
            joiner = Joiner.EQUALS
        if rest.strip():
            candidate, alt_choices, alt_variadic = _clean_metavar(rest.lstrip("= "))
            if candidate and (metavar is None or len(candidate) > len(metavar)):
                metavar = candidate
            choices = choices or alt_choices
            variadic = variadic or alt_variadic
        if name.startswith("--"):
            long = long or name
        elif len(name) <= 2:
            short = short or name
        else:
            # Single-dash long options (`-version`, `find -name`).
            long = long or name

    if not short and not long:
        return None

    kind = _infer_kind(metavar, choices, variadic)
    return OptionSpec(
        short=short,
        long=long,
        kind=kind,
        metavar=metavar,
        choices=choices,
        joiner=joiner,
        negatable=negatable,
        repeatable=variadic,
    )


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def _extract_usage(
    lines: list[str], argv_prefix: list[str]
) -> tuple[str | None, list[str], set[int]]:
    """Find the usage block and split it into alternative invocations.

    Man pages list several independent synopses (`tar -c ...`, `tar -x ...`);
    joining them would invent positionals that belong to different forms.
    """
    program = argv_prefix[0].rsplit("/", 1)[-1]
    for index, line in enumerate(lines):
        if not _USAGE_HEADER.match(line) or not line.strip():
            continue
        body = _USAGE_HEADER.sub("", line).strip()
        used = {index}
        base_indent = _indent_of(line)
        collected = [body] if body else []
        for offset in range(index + 1, len(lines)):
            nxt = lines[offset]
            if not nxt.strip():
                break
            # Tools like curl start listing options immediately after the usage
            # line with no blank separator; never swallow those.
            if _OPTION_LINE.match(nxt):
                break
            if _indent_of(nxt) <= base_indent and collected:
                break
            collected.append(nxt.strip())
            used.add(offset)
        if not collected:
            continue

        alternatives: list[str] = []
        for piece in collected:
            head = piece.split(maxsplit=1)[0] if piece.split() else ""
            if alternatives and head.rsplit("/", 1)[-1] != program:
                alternatives[-1] = f"{alternatives[-1]} {piece}"
            else:
                alternatives.append(piece)
        return " ".join(collected), alternatives, used
    return None, [], set()


def _parse_positionals(usage: str, argv_prefix: list[str]) -> list[PositionalSpec]:
    tokens = _tokenize_usage(usage)
    program = argv_prefix[0].rsplit("/", 1)[-1]
    # Drop the program name and any subcommand words the user already typed.
    skip = 0
    for token in tokens:
        if skip >= len(argv_prefix) or token.startswith("-"):
            break
        skip += 1
    positionals: list[PositionalSpec] = []
    seen: set[str] = set()
    for token in tokens[skip:]:
        stripped = token.strip()
        if not stripped or stripped in {"--", "..."}:
            continue
        optional = stripped.startswith("[")
        name, choices, variadic = _clean_metavar(stripped)
        if not name or name.startswith("-"):
            continue
        if choices:
            # `{add,remove}` in a usage line is a subcommand selector, not an arg.
            continue
        # A multi-word fragment is a bracketing artefact, not an argument name.
        if any(ch.isspace() for ch in name):
            continue
        key = name.lower()
        if key in seen or key in _USAGE_PLACEHOLDERS or key == program.lower():
            continue
        seen.add(key)
        positionals.append(
            PositionalSpec(
                name=name,
                kind=_infer_kind(name, [], False),
                required=not optional,
                variadic=variadic,
            )
        )
    return positionals


def _subcommands_from_usage(usage: str) -> list[SubcommandSpec]:
    """argparse advertises its subparsers as `{add,remove,list}` in the usage line."""
    for token in _tokenize_usage(usage):
        stripped = token.strip().strip("[]")
        if not (stripped.startswith("{") and stripped.endswith("}")):
            continue
        names = [n for n in _split_top_level(stripped[1:-1], ",|") if n]
        if len(names) > 1 and all(re.fullmatch(r"[A-Za-z][\w.-]*", n) for n in names):
            return [SubcommandSpec(name=name) for name in names]
    return []


def _extract_subcommands(
    lines: list[str], skip: set[int], program: str
) -> list[SubcommandSpec]:
    """Collect entries from every `Commands:`-style section in the help text."""
    found: dict[str, SubcommandSpec] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if (index - 1) in skip or not _COMMAND_SECTION.match(line):
            continue

        header_indent = _indent_of(line)
        entry_indent: int | None = None
        barren = 0
        while index < len(lines) and barren < _SECTION_PATIENCE:
            nxt = lines[index]
            if not nxt.strip():
                index += 1
                continue
            if _SECTION_END.match(nxt) and _indent_of(nxt) <= header_indent:
                break

            indent = _indent_of(nxt)
            # git groups its commands under unindented category headings; skip
            # those rather than treating them as the end of the section.
            if indent <= header_indent:
                index += 1
                barren += 1
                continue
            if entry_indent is None:
                entry_indent = indent
            # Deeper lines are wrapped descriptions belonging to the previous entry.
            if indent > entry_indent:
                index += 1
                continue

            index += 1
            match = _COMMAND_ENTRY.match(nxt.strip())
            if match is None:
                barren += 1
                continue
            name = match.group("name")
            if name.lower() in _NOT_COMMANDS or name == program:
                barren += 1
                continue

            barren = 0
            help_text = (match.group("help") or "").strip()
            while index < len(lines):
                follow = lines[index]
                if not follow.strip() or _indent_of(follow) <= entry_indent:
                    break
                help_text = f"{help_text} {follow.strip()}".strip()
                index += 1

            if name not in found:
                found[name] = SubcommandSpec(
                    name=name,
                    help=re.sub(r"\s+", " ", help_text),
                    has_children=bool(match.group("children")),
                )
    return list(found.values())


def _finalize(option: OptionSpec, description: str) -> OptionSpec:
    option.help = re.sub(r"\s+", " ", description).strip()
    if default := _DEFAULT.search(option.help):
        value = default.group("value").strip().strip("\"'")
        if value and value.lower() not in {"none", "null"}:
            option.default = value
    if _REPEAT_HINT.search(option.help):
        option.repeatable = True
    if option.kind is OptionKind.FLAG and option.repeatable:
        option.kind = OptionKind.COUNT
    elif (
        option.kind is OptionKind.FLAG
        and option.short
        and _COUNT_HINT.search(option.help)
    ):
        option.kind = OptionKind.COUNT
        option.repeatable = True
    return option


def parse_help(text: str, argv_prefix: list[str]) -> ParseResult:
    lines = text.replace("\t", "    ").splitlines()
    stats = ParseStats()
    usage, alternatives, usage_lines = _extract_usage(lines, argv_prefix)
    stats.usage_found = usage is not None

    options: list[OptionSpec] = []
    by_name: dict[str, OptionSpec] = {}
    index = 0

    while index < len(lines):
        line = lines[index]
        if index in usage_lines or not _OPTION_LINE.match(line):
            index += 1
            continue

        stats.option_like_lines += 1
        indent = _indent_of(line)
        body = line.strip()

        split = re.search(r"\s{2,}", body)
        if split:
            head, description = body[: split.start()], body[split.end() :].strip()
        else:
            head, description = body, ""

        option = _parse_head(head)
        index += 1
        if option is None:
            if len(stats.unparsed_samples) < 5:
                stats.unparsed_samples.append(body)
            continue

        # Absorb wrapped description lines indented past the option itself.
        extra: list[str] = []
        while index < len(lines):
            nxt = lines[index]
            if not nxt.strip():
                break
            if _indent_of(nxt) <= indent or _OPTION_LINE.match(nxt):
                break
            extra.append(nxt.strip())
            index += 1
        if extra:
            description = " ".join([description, *extra]).strip()

        stats.consumed_lines += 1
        option = _finalize(option, description)
        existing = by_name.get(option.name)
        if existing is None:
            by_name[option.name] = option
            options.append(option)
        elif not existing.help and option.help:
            existing.help = option.help

    stats.options = len(options)
    stats.with_help = sum(1 for opt in options if opt.help)

    program = argv_prefix[-1].rsplit("/", 1)[-1]
    subcommands = _extract_subcommands(lines, usage_lines, program)
    if not subcommands and alternatives:
        subcommands = _subcommands_from_usage(alternatives[0])

    spec = CommandSpec(
        argv_prefix=argv_prefix,
        usage_line=usage,
        options=options,
        positionals=_parse_positionals(alternatives[0], argv_prefix)
        if alternatives
        else [],
        subcommands=subcommands,
        source=SpecSource.HEURISTIC,
        raw_help=text,
    )
    return ParseResult(spec=spec, stats=stats)
