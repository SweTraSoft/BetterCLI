"""Application entry point."""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox

from cligui import __version__
from cligui.settings import Settings
from cligui.updates import APP_STORE_ID, check_app_store_version
from cligui.ui.theme import apply_theme


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    app = QApplication(sys.argv)
    settings = Settings.load()
    apply_theme(app, settings.appearance)
    app.setApplicationName("BetterCLI")
    app.setApplicationDisplayName("BetterCLI")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("BetterCLI")

    version_check = check_app_store_version(__version__)
    if not version_check.allowed:
        dialog = QMessageBox(
            QMessageBox.Icon.Warning,
            "Update required" if version_check.store_version else "Version check required",
            version_check.message,
            QMessageBox.StandardButton.NoButton,
        )
        if version_check.store_version and APP_STORE_ID is not None:
            open_store = dialog.addButton(
                "Open App Store", QMessageBox.ButtonRole.AcceptRole
            )
            dialog.addButton("Quit", QMessageBox.ButtonRole.RejectRole)
            dialog.exec()
            if dialog.clickedButton() is open_store:
                QDesktopServices.openUrl(
                    QUrl(f"https://apps.apple.com/app/id{APP_STORE_ID}")
                )
        else:
            dialog.exec()
        return 1

    from cligui.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
