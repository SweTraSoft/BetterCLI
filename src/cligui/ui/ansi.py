"""Render ANSI-styled text as safe HTML for Qt's rich-text widgets."""

from __future__ import annotations

import html
import re

_SEQUENCE = re.compile(
    r"\x1b\[([0-9;]*)m|\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)"
)
_OVERSTRIKE = re.compile(r".\x08")
_BASIC_COLORS = (
    "#000000",
    "#cd0000",
    "#00cd00",
    "#cdcd00",
    "#0000ee",
    "#cd00cd",
    "#00cdcd",
    "#e5e5e5",
)
_BRIGHT_COLORS = (
    "#7f7f7f",
    "#ff0000",
    "#00ff00",
    "#ffff00",
    "#5c5cff",
    "#ff00ff",
    "#00ffff",
    "#ffffff",
)


def _indexed_color(index: int) -> str:
    if index < 16:
        return (_BASIC_COLORS + _BRIGHT_COLORS)[index]
    if index < 232:
        value = index - 16
        levels = (0, 95, 135, 175, 215, 255)
        red, value = divmod(value, 36)
        green, blue = divmod(value, 6)
        return f"#{levels[red]:02x}{levels[green]:02x}{levels[blue]:02x}"
    gray = 8 + (index - 232) * 10
    return f"#{gray:02x}{gray:02x}{gray:02x}"


def ansi_to_html(text: str) -> str:
    """Convert ANSI SGR formatting to escaped HTML while dropping other controls."""
    text = _OVERSTRIKE.sub("", text)
    foreground: str | None = None
    background: str | None = None
    bold = italic = underline = False
    output: list[str] = ["<pre>"]
    position = 0

    def append_segment(segment: str) -> None:
        if not segment:
            return
        styles = []
        if foreground:
            styles.append(f"color:{foreground}")
        if background:
            styles.append(f"background-color:{background}")
        if bold:
            styles.append("font-weight:bold")
        if italic:
            styles.append("font-style:italic")
        if underline:
            styles.append("text-decoration:underline")
        escaped = html.escape(segment)
        output.append(
            f'<span style="{";".join(styles)}">{escaped}</span>'
            if styles
            else escaped
        )

    for match in _SEQUENCE.finditer(text):
        append_segment(text[position : match.start()])
        position = match.end()
        if match.group(1) is None:
            continue

        codes = [int(code or "0") for code in match.group(1).split(";")]
        index = 0
        while index < len(codes):
            code = codes[index]
            if code == 0:
                foreground = background = None
                bold = italic = underline = False
            elif code == 1:
                bold = True
            elif code == 3:
                italic = True
            elif code == 4:
                underline = True
            elif code == 22:
                bold = False
            elif code == 23:
                italic = False
            elif code == 24:
                underline = False
            elif code == 39:
                foreground = None
            elif code == 49:
                background = None
            elif 30 <= code <= 37:
                foreground = _BASIC_COLORS[code - 30]
            elif 40 <= code <= 47:
                background = _BASIC_COLORS[code - 40]
            elif 90 <= code <= 97:
                foreground = _BRIGHT_COLORS[code - 90]
            elif 100 <= code <= 107:
                background = _BRIGHT_COLORS[code - 100]
            elif code in (38, 48) and index + 1 < len(codes):
                is_foreground = code == 38
                mode = codes[index + 1]
                color: str | None = None
                if mode == 5 and index + 2 < len(codes):
                    color = _indexed_color(max(0, min(255, codes[index + 2])))
                    index += 2
                elif mode == 2 and index + 4 < len(codes):
                    red, green, blue = (
                        max(0, min(255, channel))
                        for channel in codes[index + 2 : index + 5]
                    )
                    color = f"#{red:02x}{green:02x}{blue:02x}"
                    index += 4
                if color:
                    if is_foreground:
                        foreground = color
                    else:
                        background = color
            index += 1

    append_segment(text[position:])
    output.append("</pre>")
    return "".join(output)
