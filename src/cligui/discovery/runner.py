"""Safely capture help text from a command.

Discovery necessarily executes the user's binary, so every invocation is
argv-based (never a shell string), gets no stdin, runs in a throwaway working
directory, and is killed on timeout.
"""

from __future__ import annotations

import os
import logging
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TIMEOUT = 10.0
log = logging.getLogger(__name__)

#: Tried in order; the first response that looks like help text wins.
HELP_ARGS: tuple[tuple[str, ...], ...] = (
    ("--help",),
    ("-h",),
    ("help",),
)

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_OVERSTRIKE = re.compile(r".\x08")


class DiscoveryError(RuntimeError):
    """Raised when help text cannot be obtained for a command."""


class CommandNotFoundError(DiscoveryError):
    """Raised when a command name cannot be resolved on PATH."""


@dataclass(frozen=True)
class HelpCapture:
    text: str
    origin: str
    binary: Path
    fingerprint: str
    version: str | None
    display_text: str = ""


def resolve_binary(name: str) -> Path:
    """Locate ``name`` on PATH, rejecting anything that is not executable."""
    if not name or name.startswith("-"):
        raise DiscoveryError(f"{name!r} is not a valid command name")
    if os.sep in name:
        candidate = Path(name).expanduser()
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate.resolve()
        raise DiscoveryError(f"{name!r} is not an executable file")
    found = shutil.which(name)
    if not found:
        raise CommandNotFoundError(f"{name!r} was not found on your PATH")
    binary = Path(found).resolve()
    if sys.platform == "darwin" and binary in (Path("/usr/bin/git"), Path("/usr/bin/make")):
        try:
            selected = subprocess.run(
                ["/usr/bin/xcode-select", "--print-path"],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                timeout=DEFAULT_TIMEOUT,
                text=True,
                errors="replace",
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise DiscoveryError(
                f"Could not locate the developer-tool executable for {name}: {exc}. "
                "Enter the executable's full path instead."
            ) from exc
        if selected.returncode != 0 or not selected.stdout.strip():
            detail = clean_text(selected.stderr).strip()[:800] or "No developer directory was returned."
            raise DiscoveryError(
                f"Could not locate the developer-tool executable for {name}: {detail} "
                "Install/select Xcode or Command Line Tools, or enter the executable's full path."
            )
        developer_dir = Path(selected.stdout.strip())
        executable = developer_dir / "usr" / "bin" / binary.name
        if not developer_dir.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
            raise DiscoveryError(
                f"The selected developer tool {executable} is not an executable accessible to BetterCLI. "
                "Check your developer-tools installation or enter the executable's full path."
            )
        log.info("Using developer-tool executable %s instead of %s", executable, binary)
        return executable.resolve()
    return binary


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "PAGER": "cat",
            "GIT_PAGER": "cat",
            "MANPAGER": "cat",
            "SYSTEMD_PAGER": "cat",
            "COLUMNS": "120",
        }
    )
    if "NO_COLOR" not in env:
        env["TERM"] = "xterm-256color"
        env["CLICOLOR_FORCE"] = "1"
        env["FORCE_COLOR"] = "1"
    env.pop("LESS", None)
    return env


def clean_text(raw: str) -> str:
    """Strip ANSI colour and man-page overstrike bolding."""
    return _OVERSTRIKE.sub("", _ANSI.sub("", raw)).replace("\r\n", "\n")


def _run(argv: list[str], timeout: float, cwd: str) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603 - argv list, shell is never used
            argv,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            cwd=cwd,
            env=_child_env(),
            text=True,
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise DiscoveryError(f"{argv[0]} did not respond within {timeout:g}s") from None
    except OSError as exc:
        raise DiscoveryError(f"could not run {argv[0]}: {exc}") from exc
    # Many tools print usage to stderr and exit non-zero; keep both streams.
    return proc.returncode, (proc.stdout + proc.stderr).replace("\r\n", "\n")


def looks_like_help(text: str) -> bool:
    if len(text.strip()) < 40:
        return False
    lowered = text.lower()
    if "usage" in lowered or "options" in lowered or "synopsis" in lowered:
        return True
    return bool(re.search(r"^\s+-{1,2}\w", text, re.MULTILINE))


def detect_version(argv_prefix: list[str], timeout: float, cwd: str) -> str | None:
    for flag in ("--version", "-V", "-version"):
        try:
            _, out = _run([argv_prefix[0], flag], timeout, cwd)
        except DiscoveryError:
            continue
        out = clean_text(out)
        first = next((ln.strip() for ln in out.splitlines() if ln.strip()), "")
        if first and re.search(r"\d", first) and len(first) < 200:
            return first
    return None


def fingerprint_binary(binary: Path, version: str | None) -> str:
    if version:
        return version
    try:
        stat = binary.stat()
    except OSError:
        return "unknown"
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def capture_man_page(command: str, timeout: float, cwd: str) -> str | None:
    if not shutil.which("man"):
        return None
    try:
        code, out = _run(["man", command], timeout, cwd)
    except DiscoveryError:
        return None
    return out if code == 0 and looks_like_help(clean_text(out)) else None


def capture_candidates(
    argv_prefix: list[str], timeout: float = DEFAULT_TIMEOUT
) -> list[HelpCapture]:
    """Collect every plausible help text for the command.

    BSD tools on macOS answer `--help` with a bare usage line, so the man page
    is often the only real source of option descriptions. The caller decides
    which candidate parses best.
    """
    binary = resolve_binary(argv_prefix[0])
    invocation = [str(binary), *argv_prefix[1:]]
    candidates: list[HelpCapture] = []
    seen: set[str] = set()
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="cligui-") as cwd:
        version = detect_version(invocation, timeout, cwd)
        fingerprint = fingerprint_binary(binary, version)

        def add(display_text: str, origin: str) -> None:
            text = clean_text(display_text)
            if text in seen:
                return
            seen.add(text)
            candidates.append(
                HelpCapture(
                    text=text,
                    origin=origin,
                    binary=binary,
                    fingerprint=fingerprint,
                    version=version,
                    display_text=display_text,
                )
            )

        for args in HELP_ARGS:
            try:
                code, out = _run([*invocation, *args], timeout, cwd)
            except DiscoveryError as exc:
                failures.append(f"{' '.join(args)}: {exc}")
                continue
            if looks_like_help(clean_text(out)):
                add(out, " ".join(args))
            else:
                detail = clean_text(out).strip()[:800] or "No output."
                failures.append(f"{' '.join(args)} (exit {code}): {detail}")

        if len(argv_prefix) == 1 and (man := capture_man_page(argv_prefix[0], timeout, cwd)):
            add(man, "man")

    if not candidates:
        raise DiscoveryError(
            f"{' '.join(argv_prefix)} produced no recognisable help output "
            f"from {binary}.\n\n" + "\n\n".join(failures)
        )
    return candidates
