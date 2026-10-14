"""Modal dialogs for settings, safety confirmation, and help text."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cligui import __version__
from cligui.safety import Finding, Severity
from cligui.settings import (
    APPEARANCE_DARK,
    APPEARANCE_LIGHT,
    APPEARANCE_SYSTEM,
    Settings,
)
from cligui.ui.ansi import ansi_to_html


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(360)
        self._settings = settings

        form = QFormLayout()
        self._appearance = QComboBox()
        for label, value in (
            ("Light", APPEARANCE_LIGHT),
            ("Dark", APPEARANCE_DARK),
            ("Follow system", APPEARANCE_SYSTEM),
        ):
            self._appearance.addItem(label, value)
        index = self._appearance.findData(settings.appearance)
        self._appearance.setCurrentIndex(
            index if index >= 0 else self._appearance.findData(APPEARANCE_SYSTEM)
        )

        form.addRow("Appearance", self._appearance)

        self._version = QLabel(__version__)
        self._version.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Version", self._version)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self._settings.appearance = self._appearance.currentData()
        self._settings.save()
        super().accept()


class SafetyDialog(QDialog):
    """Confirmation shown before a risky command runs.

    HIGH severity requires typing RUN so a stray Return cannot approve it.
    """

    def __init__(
        self, command: str, findings: list[Finding], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review before running")
        self.setMinimumWidth(520)
        severity = max(f.severity for f in findings)

        heading = QLabel(
            "This command looks dangerous."
            if severity is Severity.HIGH
            else "This command needs a second look."
        )
        heading.setStyleSheet("font-weight: 600; font-size: 15px;")

        preview = QLabel(command)
        preview.setWordWrap(True)
        preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        preview.setStyleSheet(
            "font-family: Menlo, monospace;"
            "background: palette(base); padding: 8px; border-radius: 4px;"
        )

        layout = QVBoxLayout(self)
        layout.addWidget(heading)
        layout.addWidget(preview)
        for finding in findings:
            item = QLabel(f"• <b>{finding.title}</b><br>{finding.detail}")
            item.setWordWrap(True)
            item.setTextFormat(Qt.RichText)
            layout.addWidget(item)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self._run = QPushButton("Run anyway")
        buttons.addButton(self._run, QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        if severity is Severity.HIGH:
            self._confirm = QLineEdit()
            self._confirm.setPlaceholderText("Type RUN to enable the button")
            self._run.setEnabled(False)
            self._confirm.textChanged.connect(
                lambda text: self._run.setEnabled(text.strip() == "RUN")
            )
            layout.addWidget(self._confirm)

        buttons.button(QDialogButtonBox.Cancel).setDefault(True)
        layout.addWidget(buttons)


class HelpTextDialog(QDialog):
    """Shows the raw help text that the options were derived from."""

    def __init__(self, spec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Help text — {spec.display_name}")
        self.resize(900, 640)

        summary = QLabel(
            f"{len(spec.options)} options and {len(spec.positionals)} arguments were "
            f"read from this text (source: {spec.source.value}, "
            f"confidence {spec.confidence:.0%})."
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("color: palette(mid);")

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setHtml(ansi_to_html(spec.raw_help or "No help text was captured."))
        viewer.setLineWrapMode(QTextEdit.NoWrap)
        font = QFont("Menlo")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(12)
        viewer.setFont(font)
        text_color = viewer.palette().text().color().name()
        viewer.document().setDefaultStyleSheet(
            f"pre {{ color: {text_color}; font-family: Menlo, monospace; "
            "font-size: 12pt; }"
        )

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        if spec.usage_line:
            usage = QLabel(spec.usage_line)
            usage.setWordWrap(True)
            usage.setTextInteractionFlags(Qt.TextSelectableByMouse)
            usage.setStyleSheet(
                "font-family: Menlo, monospace;"
                "background: palette(base); padding: 8px; border-radius: 4px;"
            )
            layout.addWidget(usage)
        layout.addWidget(summary)
        layout.addWidget(viewer, 1)
        layout.addWidget(buttons)

