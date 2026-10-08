# cligui

Turn any command-line tool into a graphical form. Type a command, and cligui
reads its `--help` (and man page), works out which options it accepts, and
builds a form for it on the fly. Configure what you want, review the assembled
command, then run it with live output.

## Install

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run cligui
```

## How it works

1. **Capture** — the command's `--help`, `-h`, `help` and `man` page are
   collected. Everything runs argv-based with no shell, no stdin, a timeout,
   and a throwaway working directory.
2. **Parse** — a heuristic parser reads the usage line and option blocks,
   recognising argparse, click, getopt and BSD man-page conventions. It infers
   each option's type from its metavar (`FILE`, `DIR`, `N`, `{a,b,c}`, `X...`).
3. **Fall back** — if the parse looks weak, the help text is sent to DeepSeek,
   which returns a structured spec. This is optional; without an API key the
   parsed result is used and the window says so.
4. **Cache** — the result is stored under `~/Library/Caches/cligui/specs`,
   keyed by the binary, its version and the parser version.
5. **Build and run** — form values become an argv list, never a shell string.
   Risky commands prompt for confirmation first.

## DeepSeek API key (optional)

Either set the environment variable:

```sh
export DEEPSEEK_API_KEY=sk-...
```

or add the key under **Tools › Settings…**, where it is stored in your
Keychain. The base URL and model are configurable in the same dialog.

The LLM is only consulted for commands the built-in parser cannot read; most
common tools never reach it.

## Notes and limits

- Only one command per window. Pipes, redirection and `&&` are rejected by
  design — there is no shell anywhere in the execution path.
- Subcommands work by typing the full path, e.g. `git log` or `docker compose`.
- Interactive and full-screen programs (`vim`, `top`, `ssh` sessions, anything
  needing a password) will not work, because the output pane is not a terminal.
- Safety warnings are advisory and can always be overridden.

## Development

```sh
uv run pytest
```

Parser behaviour is pinned by fixtures in `tests/fixtures/help/`, captured from
real tools plus two synthetic files covering argparse and click conventions.

## Building a macOS app bundle

```sh
uv run pyinstaller packaging/cligui.spec
open dist/cligui.app
```

## Layout

| Path | Purpose |
| --- | --- |
| `src/cligui/model/spec.py` | The command spec schema — the contract everything shares |
| `src/cligui/discovery/` | Help capture, heuristic parser, confidence scoring, LLM fallback |
| `src/cligui/builder.py` | Form values to argv; the only place arguments are produced |
| `src/cligui/safety.py` | Destructive-command heuristics |
| `src/cligui/execution.py` | QProcess wrapper with streaming and cancel |
| `src/cligui/ui/` | Main window, generated form, widgets, dialogs |
