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

## Appearance

Under **Tools › Settings…**, choose **Light**, **Dark**, or **Follow system**
(the default), which tracks the macOS appearance while the app is running.

## App Store version enforcement

When BetterCLI is listed on the Apple App Store, set `APP_STORE_ID` in
`src/cligui/updates.py` to its numeric listing ID. At startup, the app checks
Apple's lookup service and blocks outdated versions. If the service is
unavailable, BetterCLI permits offline use for up to 28 days after its last
successful check (or first offline launch); after that, it requires a
successful check before opening.

## Notes and limits

- Only one command per window. Pipes, redirection and `&&` are rejected by
  design — there is no shell anywhere in the execution path.
- Subcommands work by typing the full path, e.g. `git log` or `docker compose`.
- Recent commands in the left sidebar retain their output, last executed command,
  and working directory across app restarts. Double-click an entry or press Enter
  to reopen it without running it. Repeated runs append to that command's output;
  Clear removes the active command's saved output. These transcripts are stored
  locally and may contain sensitive command output. Clear command history in the
  Tools menu to remove all saved sessions.
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

### Preparing a Mac App Store package

The regular build above is not an App Store submission. Use the separate
distribution workflow after installing these items:

1. In your [Apple Developer account](https://developer.apple.com/account/),
   use the registered explicit macOS App ID `com.swetrasoft.BetterCLI` (or your own bundle
   ID). Use the same ID for the app record in App Store Connect.
2. Create an **Apple Distribution** or **Mac App Distribution** certificate
   for app signing, and a **Mac Installer Distribution** certificate for
   package signing. Import them into Keychain Access on the Mac that holds
   their private keys. Apple Development and Developer ID certificates are
   not substitutes. `security find-identity -v` must list both identities.
3. Create a **Mac App Store distribution provisioning profile** for that
   explicit App ID and app signing certificate. Download the
   `.provisionprofile` outside this repository.

Use the full identity names from Keychain Access:

```sh
uv sync
uv run python packaging/build_app_store.py \
  --app-identity "Apple Distribution: YOUR NAME (TEAMID)" \
  --installer-identity "3rd Party Mac Developer Installer: YOUR NAME (TEAMID)" \
  --profile "$HOME/Downloads/BetterCLI.provisionprofile" \
  --build-number 1
```

For a different registered App ID, also supply `--bundle-id YOUR.BUNDLE.ID`.
Increment the build number for each new upload. Output is isolated under
`dist/app-store/BUILD_NUMBER/`; an existing output directory is never overwritten.
The workflow checks the profile's platform, expiration, App ID, team and signing
certificate, builds from current source, embeds the profile, signs the app and
installer, and verifies their local signatures. Do not commit profiles,
certificates, private keys or signed distribution artifacts.

**Sandbox compatibility remains a release gate.** The distribution build enables
App Sandbox, outgoing network access and access to user-selected files. Nested
executables inherit the sandbox. These entitlements do not grant arbitrary access
to the filesystem or make every external CLI compatible. Test command discovery,
execution, working-directory selection, settings, history, Keychain access and
network requests in a sandboxed development-signed build. Reopening file access
across launches may require security-scoped bookmarks, which BetterCLI does not
currently implement. Do not advertise unrestricted CLI compatibility for the
sandboxed version.

After compatibility testing, use Apple's
[Transporter](https://apps.apple.com/app/transporter/id1450874784) to validate and
upload the `.pkg` to App Store Connect. Local signature verification is not Apple
validation or approval. An App Store distribution-signed app is not a substitute
for a development-signed build for local testing.

## Layout

| Path | Purpose |
| --- | --- |
| `src/cligui/model/spec.py` | The command spec schema — the contract everything shares |
| `src/cligui/discovery/` | Help capture, heuristic parser, confidence scoring, LLM fallback |
| `src/cligui/builder.py` | Form values to argv; the only place arguments are produced |
| `src/cligui/safety.py` | Destructive-command heuristics |
| `src/cligui/execution.py` | QProcess wrapper with streaming and cancel |
| `src/cligui/ui/` | Main window, generated form, widgets, dialogs |
