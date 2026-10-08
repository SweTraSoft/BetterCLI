"""Score how well the heuristic parser understood a help text."""

from __future__ import annotations

from cligui.discovery.heuristic import ParseStats

#: Below this score the LLM fallback is worth the round trip.
LLM_THRESHOLD = 0.55


def score(stats: ParseStats) -> float:
    """Return a 0..1 estimate of parse quality."""
    if stats.options == 0:
        return 0.0

    # How many of the lines that looked like options did we actually understand?
    coverage = (
        stats.consumed_lines / stats.option_like_lines if stats.option_like_lines else 0.0
    )
    # Descriptions are what make the generated form usable.
    described = stats.with_help / stats.options
    # A handful of options is normal; more is strong evidence of a clean parse.
    volume = min(stats.options, 8) / 8

    value = 0.45 * coverage + 0.30 * described + 0.15 * volume
    if stats.usage_found:
        value += 0.10
    return round(min(value, 1.0), 3)


def needs_llm(stats: ParseStats, threshold: float = LLM_THRESHOLD) -> bool:
    return score(stats) < threshold
