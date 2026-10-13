"""Application appearance helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication, QToolTip

_NATIVE_STYLE_PROPERTY = "_bettercli_native_style"


def apply_theme(application: QApplication, dark_mode: bool) -> None:
    if getattr(sys, "frozen", False):
        icon_directory = Path(sys._MEIPASS)
    else:
        icon_directory = (
            Path(__file__).resolve().parents[3]
            / "packaging"
            / "app-icons"
        )
    icon_name = "BetterCLI-dark.png" if dark_mode else "BetterCLI-light.png"
    application.setWindowIcon(QIcon(str(icon_directory / icon_name)))

    # Native chrome (title bar, menus, file dialogs) follows this, not the palette.
    style_hints = application.styleHints()
    if hasattr(style_hints, "setColorScheme"):
        style_hints.setColorScheme(
            Qt.ColorScheme.Dark if dark_mode else Qt.ColorScheme.Light
        )

    # The native macOS style ignores most palette roles, so dark mode uses Fusion.
    native_style = application.property(_NATIVE_STYLE_PROPERTY)
    if native_style is None:
        native_style = application.style().name()
        application.setProperty(_NATIVE_STYLE_PROPERTY, native_style)
    wanted_style = "Fusion" if dark_mode else native_style
    if application.style().name().lower() != wanted_style.lower():
        application.setStyle(wanted_style)

    if not dark_mode:
        palette = application.style().standardPalette()
        application.setPalette(palette)
        QToolTip.setPalette(palette)
        _refresh_style_sheets(application)
        return

    palette = QPalette(application.style().standardPalette())
    colors = {
        QPalette.ColorRole.Window: "#171B24",
        QPalette.ColorRole.WindowText: "#E6EAF2",
        QPalette.ColorRole.Base: "#10151D",
        QPalette.ColorRole.AlternateBase: "#1B222E",
        QPalette.ColorRole.ToolTipBase: "#252E3C",
        QPalette.ColorRole.ToolTipText: "#F6F7FB",
        QPalette.ColorRole.Text: "#E6EAF2",
        QPalette.ColorRole.Button: "#252D3A",
        QPalette.ColorRole.ButtonText: "#E6EAF2",
        QPalette.ColorRole.BrightText: "#FF6666",
        QPalette.ColorRole.Link: "#53ACFF",
        QPalette.ColorRole.LinkVisited: "#A98BFF",
        QPalette.ColorRole.Highlight: "#176FE8",
        QPalette.ColorRole.HighlightedText: "#FFFFFF",
        QPalette.ColorRole.PlaceholderText: "#6F7A8A",
        QPalette.ColorRole.Light: "#3A4658",
        QPalette.ColorRole.Midlight: "#303A49",
        QPalette.ColorRole.Mid: "#98A3B3",
        QPalette.ColorRole.Dark: "#11151C",
        QPalette.ColorRole.Shadow: "#090B10",
    }
    if hasattr(QPalette.ColorRole, "Accent"):
        colors[QPalette.ColorRole.Accent] = "#176FE8"
    for role, color in colors.items():
        palette.setColor(role, QColor(color))

    palette.setColor(
        QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, QColor("#2A4A78")
    )

    disabled_colors = {
        QPalette.ColorRole.WindowText: "#7B8594",
        QPalette.ColorRole.Text: "#737D8C",
        QPalette.ColorRole.ButtonText: "#737D8C",
        QPalette.ColorRole.Base: "#141921",
        QPalette.ColorRole.Button: "#1D232D",
        QPalette.ColorRole.PlaceholderText: "#525C6A",
        QPalette.ColorRole.Highlight: "#31435B",
        QPalette.ColorRole.HighlightedText: "#ADB6C3",
    }
    for role, color in disabled_colors.items():
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(color))

    application.setPalette(palette)
    QToolTip.setPalette(palette)
    _refresh_style_sheets(application)


def _refresh_style_sheets(application: QApplication) -> None:
    # Stylesheets resolve palette(...) once, so re-set them to pick up the new colours.
    for widget in application.allWidgets():
        if style_sheet := widget.styleSheet():
            widget.setStyleSheet("")
            widget.setStyleSheet(style_sheet)