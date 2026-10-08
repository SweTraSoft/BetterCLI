"""Warn before running commands that are destructive or hard to undo.

These are advisory heuristics over the assembled argv, not a security boundary:
the user can always proceed. They exist to catch the kind of mistake that a
point-and-click form makes easy, such as leaving `--force` ticked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path


class Severity(IntEnum):
    NONE = 0
    CAUTION = 1
    HIGH = 2


@dataclass(frozen=True)
class Finding:
    severity: Severity
    title: str
    detail: str


#: Paths whose recursive deletion would be catastrophic.
_CRITICAL_ROOTS = {"/", "/*", "~", "~/", "/Users", "/home", "/System", "/etc", "/var"}

_DESTRUCTIVE_BINARIES = {
    "dd": (Severity.HIGH, "dd writes raw blocks and can destroy a disk."),
    "mkfs": (Severity.HIGH, "mkfs formats a filesystem, erasing its contents."),
    "fdisk": (Severity.HIGH, "fdisk edits the partition table."),
    "diskutil": (Severity.HIGH, "diskutil can erase or repartition volumes."),
    "shutdown": (Severity.HIGH, "This will shut down or reboot the machine."),
    "reboot": (Severity.HIGH, "This will reboot the machine."),
    "halt": (Severity.HIGH, "This will halt the machine."),
    "shred": (Severity.HIGH, "shred irreversibly overwrites file contents."),
    "killall": (Severity.CAUTION, "killall terminates every matching process."),
    "chown": (Severity.CAUTION, "Changing ownership can lock you out of files."),
}

_CAUTION_FLAGS = {
    "--force": "Forced operations skip the usual safety checks.",
    "-f": "The -f flag usually means 'force'.",
    "--hard": "A hard reset discards uncommitted work.",
    "--purge": "Purging removes configuration as well as data.",
    "--prune": "Pruning permanently removes unreferenced data.",
    "--overwrite": "Existing files will be overwritten.",
    "--delete": "Files will be deleted.",
    "--no-preserve-root": "This disables the guard against deleting /.",
}

_FORK_BOMB = re.compile(r":\(\)\s*\{.*\|.*&.*\}")


def _basename(token: str) -> str:
    return Path(token).name


def _is_recursive_delete(argv: list[str]) -> bool:
    if _basename(argv[0]) != "rm":
        return False
    for token in argv[1:]:
        if token.startswith("--"):
            if token in {"--recursive", "--force"}:
                return True
        elif token.startswith("-") and any(ch in token for ch in "rR"):
            return True
    return False


def _dangerous_targets(argv: list[str]) -> list[str]:
    hits = []
    for token in argv[1:]:
        if token.startswith("-"):
            continue
        normalized = token.rstrip("/") or "/"
        if token in _CRITICAL_ROOTS or normalized in _CRITICAL_ROOTS:
            hits.append(token)
        elif Path(token).expanduser() == Path.home():
            hits.append(token)
    return hits


def inspect(argv: list[str]) -> list[Finding]:
    """Return every concern raised by ``argv``, worst first."""
    if not argv:
        return []

    findings: list[Finding] = []
    name = _basename(argv[0])

    if name in {"sudo", "doas"}:
        findings.append(
            Finding(
                Severity.HIGH,
                "Runs with administrator privileges",
                "sudo will prompt for a password on a terminal that this window does "
                "not provide, so the command is likely to hang or fail.",
            )
        )

    for binary, (severity, detail) in _DESTRUCTIVE_BINARIES.items():
        if name == binary or name.startswith(f"{binary}."):
            findings.append(Finding(severity, f"{name} is a destructive tool", detail))
            break

    if _is_recursive_delete(argv):
        targets = _dangerous_targets(argv)
        if targets:
            findings.append(
                Finding(
                    Severity.HIGH,
                    "Recursive delete of a critical location",
                    f"This would recursively delete: {', '.join(targets)}.",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.CAUTION,
                    "Recursive delete",
                    "Files will be removed recursively and will not go to the Trash.",
                )
            )

    if name == "chmod" and any(arg in {"777", "-R", "--recursive"} for arg in argv[1:]):
        findings.append(
            Finding(
                Severity.CAUTION,
                "Broad permission change",
                "Recursive or world-writable permission changes are rarely intended.",
            )
        )

    seen_flags: set[str] = set()
    for token in argv[1:]:
        flag = token.split("=", 1)[0]
        if flag in _CAUTION_FLAGS and flag not in seen_flags:
            seen_flags.add(flag)
            findings.append(
                Finding(Severity.CAUTION, f"{flag} is set", _CAUTION_FLAGS[flag])
            )

    if any(_FORK_BOMB.search(token) for token in argv):
        findings.append(
            Finding(Severity.HIGH, "Fork bomb pattern", "This would exhaust system resources.")
        )

    return sorted(findings, key=lambda f: f.severity, reverse=True)


def worst(findings: list[Finding]) -> Severity:
    return max((f.severity for f in findings), default=Severity.NONE)
