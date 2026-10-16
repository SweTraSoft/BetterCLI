"""Append-only pane that shows streamed command output."""

from __future__ import annotations

from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from cligui.ui.i18n import tr

#: Keeps a long-running command from growing the document without bound.
MAX_BLOCKS = 5000
ROUNDED_FIELD_STYLE = (
    "QPlainTextEdit, QLineEdit {"
    " background: palette(base);"
    " border: 1px solid palette(midlight);"
    " border-radius: 6px;"
    " padding: 8px;"
    "}"
    "QPlainTextEdit { font-family: Menlo, monospace; }"
)


class OutputView(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(MAX_BLOCKS)
        self.setPlaceholderText(tr("Command output appears here."))
        font = QFont("Menlo")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(12)
        self.setFont(font)
        self.setStyleSheet(ROUNDED_FIELD_STYLE)

    def append_text(self, text: str) -> None:
        at_bottom = (
            self.verticalScrollBar().value() >= self.verticalScrollBar().maximum() - 4
        )
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        if at_bottom:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def append_notice(self, text: str) -> None:
        prefix = "" if self.toPlainText().endswith("\n") or not self.toPlainText() else "\n"
        self.append_text(f"{prefix}── {text} ──\n")
