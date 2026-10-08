"""Orchestrates discovery: cache -> help capture -> heuristic -> LLM -> cache."""

from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass

from cligui.cache import SpecCache, make_key
from cligui.discovery import confidence, heuristic, llm
from cligui.discovery.runner import (
    DiscoveryError,
    capture_candidates,
    resolve_binary,
)
from cligui.model.spec import CommandSpec, SpecSource
from cligui.settings import Settings

log = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    spec: CommandSpec
    from_cache: bool = False
    #: Human-readable note shown in the UI, e.g. why the LLM was skipped.
    note: str | None = None


def split_command(text: str) -> list[str]:
    """Split user input into an argv prefix, rejecting shell metacharacters."""
    try:
        parts = shlex.split(text.strip())
    except ValueError as exc:
        raise DiscoveryError(f"could not parse command: {exc}") from exc
    if not parts:
        raise DiscoveryError("enter a command first")
    for part in parts:
        if any(ch in part for ch in "|&;<>$`\n"):
            raise DiscoveryError(
                "shell operators are not supported; enter a single command"
            )
    if any(part.startswith("-") for part in parts):
        raise DiscoveryError(
            "enter only the command and any subcommands; options are configured in the form"
        )
    return parts


class DiscoveryService:
    def __init__(
        self, settings: Settings | None = None, cache: SpecCache | None = None
    ) -> None:
        self.settings = settings or Settings.load()
        self.cache = cache or SpecCache()

    def preflight(self, argv_prefix: list[str]):
        """Resolve the binary before anything is executed, so the UI can confirm."""
        return resolve_binary(argv_prefix[0])

    def discover(self, argv_prefix: list[str], refresh: bool = False) -> DiscoveryResult:
        binary = resolve_binary(argv_prefix[0])
        candidates = capture_candidates(
            argv_prefix, timeout=self.settings.discovery_timeout
        )
        key = make_key(argv_prefix, binary, candidates[0].fingerprint)

        if not refresh and (cached := self.cache.load(key)) is not None:
            return DiscoveryResult(spec=cached, from_cache=True)

        # Several help sources may be available; keep whichever parses richest.
        parsed_candidates = [
            (heuristic.parse_help(candidate.text, argv_prefix), candidate)
            for candidate in candidates
        ]
        parsed, capture = max(
            parsed_candidates,
            key=lambda pair: (len(pair[0].spec.options), confidence.score(pair[0].stats)),
        )

        spec = parsed.spec
        spec.version = capture.version
        spec.confidence = confidence.score(parsed.stats)

        # A man page may list the most options while only `--help` lists the
        # subcommands, so take the best of each rather than one whole candidate.
        if not spec.subcommands:
            richest = max(
                (p.spec.subcommands for p, _ in parsed_candidates), key=len, default=[]
            )
            spec.subcommands = richest

        note: str | None = None

        if confidence.needs_llm(parsed.stats):
            if llm.is_available(self.settings):
                try:
                    improved = llm.extract_spec(
                        argv_prefix, capture.text, self.settings
                    )
                    improved.version = capture.version
                    improved.usage_line = spec.usage_line
                    improved.subcommands = improved.subcommands or spec.subcommands
                    if len(improved.options) >= len(spec.options):
                        spec = improved
                        note = "Options were reconstructed by DeepSeek."
                    else:
                        note = "DeepSeek found fewer options than the parser; kept the parsed result."
                except llm.LLMUnavailable as exc:
                    log.info("LLM fallback unavailable: %s", exc)
                    note = f"Low-confidence parse; DeepSeek fallback unavailable ({exc})."
            else:
                note = (
                    "Low-confidence parse. Add a DeepSeek API key in Settings to "
                    "improve results for commands like this one."
                )

        if not spec.options and not spec.positionals and not spec.subcommands:
            note = note or (
                f"No options were found in the help output of {' '.join(argv_prefix)}."
            )

        if spec.source is not SpecSource.MANUAL:
            self.cache.store(key, spec)
        return DiscoveryResult(spec=spec, note=note)
