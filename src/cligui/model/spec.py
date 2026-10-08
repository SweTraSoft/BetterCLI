"""Schema describing a discovered CLI command.

This module is the single source of truth for the shape of a command spec: the
heuristic parser, the LLM fallback, the on-disk cache and the GUI all speak it.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

#: Bump whenever parsing or the schema changes so stale cache entries are dropped.
PARSER_VERSION = 2


class OptionKind(StrEnum):
    FLAG = "flag"
    COUNT = "count"
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    CHOICE = "choice"
    PATH_FILE = "path_file"
    PATH_DIR = "path_dir"
    MULTI = "multi"


class Joiner(StrEnum):
    SPACE = "space"
    EQUALS = "equals"


class SpecSource(StrEnum):
    HEURISTIC = "heuristic"
    LLM = "llm"
    MANUAL = "manual"


VALUE_KINDS = frozenset(
    {
        OptionKind.STRING,
        OptionKind.INT,
        OptionKind.FLOAT,
        OptionKind.CHOICE,
        OptionKind.PATH_FILE,
        OptionKind.PATH_DIR,
        OptionKind.MULTI,
    }
)


class OptionSpec(BaseModel):
    """A single switch accepted by the command."""

    short: str | None = None
    long: str | None = None
    kind: OptionKind = OptionKind.FLAG
    metavar: str | None = None
    choices: list[str] = Field(default_factory=list)
    help: str = ""
    required: bool = False
    repeatable: bool = False
    joiner: Joiner = Joiner.SPACE
    default: str | None = None
    negatable: bool = False

    @field_validator("short", "long")
    @classmethod
    def _strip_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    def model_post_init(self, _context: object) -> None:
        if not self.short and not self.long:
            raise ValueError("option must define a short or long form")

    @property
    def name(self) -> str:
        """Stable identifier used as the key in a values dict."""
        return self.long or self.short or ""

    @property
    def display(self) -> str:
        return ", ".join(part for part in (self.short, self.long) if part)

    @property
    def takes_value(self) -> bool:
        return self.kind in VALUE_KINDS

    @property
    def preferred_token(self) -> str:
        """The form emitted on the command line; long is less ambiguous."""
        return self.long or self.short or ""


class PositionalSpec(BaseModel):
    """A positional argument, ordered by its index in ``CommandSpec.positionals``."""

    name: str
    kind: OptionKind = OptionKind.STRING
    help: str = ""
    required: bool = True
    variadic: bool = False

    @property
    def takes_value(self) -> bool:
        return True


class SubcommandSpec(BaseModel):
    """A nested command, e.g. the `doctor` in `openclaw doctor`."""

    name: str
    help: str = ""
    #: True when the help text marks it as having subcommands of its own.
    has_children: bool = False

    @property
    def display(self) -> str:
        label = f"{self.name} ›" if self.has_children else self.name
        return f"{label}  —  {self.help}" if self.help else label


class CommandSpec(BaseModel):
    """Everything the GUI needs to render a form for one command."""

    argv_prefix: list[str] = Field(min_length=1)
    version: str | None = None
    usage_line: str | None = None
    options: list[OptionSpec] = Field(default_factory=list)
    positionals: list[PositionalSpec] = Field(default_factory=list)
    subcommands: list[SubcommandSpec] = Field(default_factory=list)
    source: SpecSource = SpecSource.HEURISTIC
    confidence: float = 0.0
    raw_help: str = ""
    parser_version: int = PARSER_VERSION

    @property
    def display_name(self) -> str:
        return " ".join(self.argv_prefix)

    def option_by_name(self, name: str) -> OptionSpec | None:
        return next((opt for opt in self.options if opt.name == name), None)
