"""Turn configured form values into an argv list.

This is the only module that produces executable arguments. It always emits a
list of discrete tokens - never a shell string - so values containing spaces,
quotes or metacharacters cannot change the structure of the command.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Any

from cligui.model.spec import CommandSpec, Joiner, OptionKind, OptionSpec


class BuildError(ValueError):
    """Raised when the configured values cannot produce a runnable command."""


@dataclass
class FormValues:
    options: dict[str, Any] = field(default_factory=dict)
    positionals: dict[str, Any] = field(default_factory=dict)
    #: Verbatim extra arguments for anything discovery missed.
    extra: list[str] = field(default_factory=list)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if str(v).strip()]
    text = str(value).strip()
    return [text] if text else []


def _negated(option: OptionSpec) -> str | None:
    if not option.negatable or not option.long:
        return None
    return f"--no-{option.long.lstrip('-')}"


def _emit_option(option: OptionSpec, value: Any) -> list[str]:
    token = option.preferred_token

    if option.kind is OptionKind.FLAG:
        if value is True:
            return [token]
        if value is False and (negated := _negated(option)):
            return [negated]
        return []

    if option.kind is OptionKind.COUNT:
        times = int(value or 0)
        if times <= 0:
            return []
        repeat = option.short or token
        return [repeat] * times

    values = _as_list(value)
    if not values:
        return []
    if option.kind is not OptionKind.MULTI and not option.repeatable:
        values = values[:1]

    argv: list[str] = []
    for item in values:
        if option.joiner is Joiner.EQUALS and token.startswith("--"):
            argv.append(f"{token}={item}")
        else:
            argv.extend([token, item])
    return argv


def missing_required(spec: CommandSpec, values: FormValues) -> list[str]:
    missing: list[str] = []
    for option in spec.options:
        if not option.required:
            continue
        raw = values.options.get(option.name)
        if option.kind is OptionKind.FLAG:
            if raw is not True:
                missing.append(option.display)
        elif not _as_list(raw):
            missing.append(option.display)
    for positional in spec.positionals:
        if positional.required and not _as_list(values.positionals.get(positional.name)):
            missing.append(positional.name)
    return missing


def build_argv(spec: CommandSpec, values: FormValues) -> list[str]:
    outstanding = missing_required(spec, values)
    if outstanding:
        raise BuildError("Required and still empty: " + ", ".join(outstanding))

    argv = list(spec.argv_prefix)
    for option in spec.options:
        if option.name in values.options:
            argv.extend(_emit_option(option, values.options[option.name]))

    argv.extend(str(item) for item in values.extra if str(item).strip())

    positionals: list[str] = []
    for positional in spec.positionals:
        items = _as_list(values.positionals.get(positional.name))
        if not positional.variadic:
            items = items[:1]
        positionals.extend(items)

    # `--` keeps positionals that start with a dash from being read as options.
    if positionals and any(item.startswith("-") for item in positionals):
        argv.append("--")
    argv.extend(positionals)
    return argv


def preview(argv: list[str]) -> str:
    """A copy-pasteable rendering of ``argv``; for display only, never executed."""
    return shlex.join(argv)
