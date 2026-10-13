"""Application entry point."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from cligui import __version__
from cligui.settings import Settings
from cligui.ui.theme import apply_theme


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    app = QApplication(sys.argv)
    settings = Settings.load()
    apply_theme(app, settings.dark_mode)
    app.setApplicationName("BetterCLI")
    app.setApplicationDisplayName("BetterCLI")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("BetterCLI")

    from cligui.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
