"""LLM fallback that extracts a command spec from help text.

Used only when the heuristic parser reports low confidence. The model's output
is treated as untrusted data: it is validated against a narrow schema and can
never influence which executable is run, only how the form is rendered.
"""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field, ValidationError

from cligui.model.spec import (
    CommandSpec,
    OptionSpec,
    PositionalSpec,
    SpecSource,
    SubcommandSpec,
)
from cligui.settings import Settings, get_api_key

log = logging.getLogger(__name__)

MAX_HELP_CHARS = 12_000
REQUEST_TIMEOUT = 60.0

SYSTEM_PROMPT = """\
You extract machine-readable command-line interface specifications from help text.
Reply with a single JSON object and nothing else. Use this exact shape:

{
  "options": [
    {
      "short": "-o" or null,
      "long": "--output" or null,
      "kind": one of "flag","count","string","int","float","choice","path_file","path_dir","multi",
      "metavar": "FILE" or null,
      "choices": ["a","b"],
      "help": "one-line description",
      "required": false,
      "repeatable": false,
      "joiner": "space" or "equals",
      "default": "value" or null,
      "negatable": false
    }
  ],
  "positionals": [
    {"name": "SOURCE", "kind": "path_file", "help": "...", "required": true, "variadic": false}
  ],
  "subcommands": [
    {"name": "doctor", "help": "one-line description", "has_children": false}
  ]
}

Rules:
- Every option MUST have a non-null "short" or "long", written with its leading dashes.
- "flag" means the option takes no value. "count" means a valueless option that may be
  repeated to increase an amount (e.g. -v). "multi" means it accepts several values.
- Use "path_file" / "path_dir" when the value names a file or directory.
- Use "equals" for joiner only when the help text shows `--opt=VALUE`.
- Only describe options that actually appear in the help text. Never invent any.
- List nested commands under "subcommands" (bare names, no dashes), not as positionals.
  Set "has_children" when the help text marks that subcommand as having its own.
"""


class _LLMPayload(BaseModel):
    options: list[OptionSpec] = Field(default_factory=list)
    positionals: list[PositionalSpec] = Field(default_factory=list)
    subcommands: list[SubcommandSpec] = Field(default_factory=list)


class LLMUnavailable(RuntimeError):
    """Raised when the LLM fallback cannot be used (no key, no network, ...)."""


def is_available(settings: Settings | None = None) -> bool:
    settings = settings or Settings.load()
    return settings.llm_enabled and bool(get_api_key())


def _client(settings: Settings):
    key = get_api_key()
    if not key:
        raise LLMUnavailable(
            "No LLM API key configured."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise LLMUnavailable("the openai package is not installed") from exc
    return OpenAI(api_key=key, base_url=settings.base_url, timeout=REQUEST_TIMEOUT)


def _user_prompt(argv_prefix: list[str], help_text: str) -> str:
    body = help_text[:MAX_HELP_CHARS]
    truncated = "\n\n[help text truncated]" if len(help_text) > MAX_HELP_CHARS else ""
    return (
        f"Command: {' '.join(argv_prefix)}\n\n"
        f"Help text:\n```\n{body}\n```{truncated}"
    )


def _parse_payload(content: str) -> _LLMPayload:
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return _LLMPayload.model_validate_json(text)


def extract_spec(
    argv_prefix: list[str],
    help_text: str,
    settings: Settings | None = None,
    client=None,
) -> CommandSpec:
    """Ask the model to describe ``help_text``; raises :class:`LLMUnavailable`."""
    settings = settings or Settings.load()
    if not settings.llm_enabled:
        raise LLMUnavailable("the LLM fallback is disabled")
    client = client or _client(settings)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _user_prompt(argv_prefix, help_text)},
    ]

    payload: _LLMPayload | None = None
    last_error: Exception | None = None
    content = ""
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=settings.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
            content = response.choices[0].message.content or ""
            payload = _parse_payload(content)
            break
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == 0:
                messages.extend(
                    [
                        {"role": "assistant", "content": content},
                        {
                            "role": "user",
                            "content": (
                                "That response did not match the required schema:\n"
                                f"{exc}\nReply again with only the corrected JSON object."
                            ),
                        },
                    ]
                )
        except Exception as exc:
            raise LLMUnavailable(f"LLM request failed: {exc}") from exc

    if payload is None:
        raise LLMUnavailable(f"the model returned unusable JSON: {last_error}")

    return CommandSpec(
        argv_prefix=argv_prefix,
        options=payload.options,
        positionals=payload.positionals,
        subcommands=payload.subcommands,
        source=SpecSource.LLM,
        confidence=0.8 if payload.options else 0.2,
        raw_help=help_text,
    )
