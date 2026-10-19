# BetterCLI

Turn any command-line tool into a graphical form. Type a command, and BetterCLI
reads its `--help` (and man page), works out which options it accepts, and
builds a form for it on the fly. Configure what you want, review the assembled
command, then run it with live output.

## Install

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run bettercli
```

## How it works

1. **Capture** — the command's `--help`, `-h`, `help` and `man` page are
   collected. Everything runs argv-based with no shell, no stdin, a timeout,
   and a throwaway working directory.
2. **Parse** — a heuristic parser reads the usage line and option blocks,
   recognising argparse, click, getopt and BSD man-page conventions. It infers
   each option's type from its metavar (`FILE`, `DIR`, `N`, `{a,b,c}`, `X...`).
3. **Fall back** — if the parse looks weak, the help text is sent to an LLM,
   which returns a structured spec. This is optional; without an API key the
   parsed result is used and the window says so.
4. **Cache** — the result is stored under `~/Library/Caches/cligui/specs`,
   keyed by the binary, its version and the parser version.
5. **Build and run** — form values become an argv list, never a shell string.
   Risky commands prompt for confirmation first.

The help-text viewer preserves ANSI colors and styles when a command provides them.

The top command dropdown lists 100 common CLI commands. Initially ordered by
estimated general usage frequency, it promotes commands as you run them in
BetterCLI. Usage counts persist across restarts; subcommands and absolute
executable paths count toward the same command. Ties keep the initial order.
Each entry includes a description; commands not found on your PATH are disabled.
The list scrolls when it cannot fit on screen.

## Appearance

Under **Tools › Settings…**, choose **Light**, **Dark**, or **Follow system**
(the default), which tracks the macOS appearance while the app is running.
## Language

Under **Tools › Settings…**, choose **System language** to follow the operating
system language (English is used when it is not available), or select one of
the 16 included UI languages. Language changes take effect as soon as they are
saved.

## Notes and limits

- Only one command per window. Pipes, redirection and `&&` are rejected by
  design — there is no shell anywhere in the execution path.
- Subcommands work by typing the full path, e.g. `git log` or `docker compose`.
- Absolute executable paths are supported. The editable command and preview retain
  the full path, while subcommand headings use the executable's filename. Hover over
  the command field to see a long path in full.
- On macOS, when a command name resolves to `/usr/bin/git` or `/usr/bin/make`,
  discovery and execution use the actual executable in the developer directory
  reported by `xcode-select --print-path`, avoiding the system developer-tool
  launcher. This supports Xcode (including renamed installations) and Command Line
  Tools. Custom installations found first on PATH and explicitly entered paths
  are preserved. If developer-tool resolution fails, BetterCLI reports the error;
  you can enter the actual executable's full path instead. This does not grant
  additional sandbox permissions. Failed help scans include the underlying errors.
- Recent commands in the left sidebar retain their output, last executed command,
  and working directory across app restarts. Double-click an entry or press Enter
  to reopen it without running it. Repeated runs append to that command's output;
  Clear removes the active command's saved output. These transcripts are stored
  locally and may contain sensitive command output. Clear command history in the
  Tools menu to remove all saved sessions and reset the dropdown's usage ranking.
- Interactive and full-screen programs (`vim`, `top`, `ssh` sessions, anything
  needing a password) will not work, because the output pane is not a terminal.
- Safety warnings are advisory and can always be overridden.

## Development

### Run in VS Code

Install the Microsoft **Python** and **Python Debugger** extensions. Open
**Run and Debug** in the left sidebar, select **Run BetterCLI**, and click the
green play button (or press **F5**). VS Code runs `uv sync` before launching
the GUI with the project's virtual environment. Python does not need a
separate compilation step to run the app.

### Tests

```sh
uv run pytest
```

Parser behaviour is pinned by fixtures in `tests/fixtures/help/`, captured from
real tools plus two synthetic files covering argparse and click conventions.

## Building a macOS app bundle

```sh
uv run pyinstaller packaging/cligui.spec
open dist/BetterCLI.app
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
