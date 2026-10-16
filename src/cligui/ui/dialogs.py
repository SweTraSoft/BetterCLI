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
from cligui.ui.i18n import LANGUAGE_SYSTEM, LANGUAGES, tr


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Settings"))
        self.setMinimumWidth(360)
        self._settings = settings

        form = QFormLayout()
        self._appearance = QComboBox()
        for label, value in (
            (tr("Light"), APPEARANCE_LIGHT),
            (tr("Dark"), APPEARANCE_DARK),
            (tr("Follow system"), APPEARANCE_SYSTEM),
        ):
            self._appearance.addItem(label, value)
        index = self._appearance.findData(settings.appearance)
        self._appearance.setCurrentIndex(
            index if index >= 0 else self._appearance.findData(APPEARANCE_SYSTEM)
        )

        form.addRow(tr("Appearance"), self._appearance)

        self._language = QComboBox()
        self._language.addItem(tr("System language"), LANGUAGE_SYSTEM)
        for code, name in LANGUAGES:
            self._language.addItem(name, code)
        index = self._language.findData(settings.language)
        self._language.setCurrentIndex(
            index if index >= 0 else self._language.findData(LANGUAGE_SYSTEM)
        )
        form.addRow(tr("Language"), self._language)

        self._version = QLabel(__version__)
        self._version.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow(tr("Version"), self._version)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(tr("Save"))
        buttons.button(QDialogButtonBox.Cancel).setText(tr("Cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self._settings.appearance = self._appearance.currentData()
        self._settings.language = self._language.currentData()
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
        self.setWindowTitle(tr("Review before running"))
        self.setMinimumWidth(520)
        severity = max(f.severity for f in findings)

        heading = QLabel(
            tr("This command looks dangerous.")
            if severity is Severity.HIGH
            else tr("This command needs a second look.")
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
        buttons.button(QDialogButtonBox.Cancel).setText(tr("Cancel"))
        self._run = QPushButton(tr("Run anyway"))
        buttons.addButton(self._run, QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        if severity is Severity.HIGH:
            self._confirm = QLineEdit()
            self._confirm.setPlaceholderText(tr("Type RUN to enable the button"))
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
        self.setWindowTitle(tr("Help text — {name}", name=spec.display_name))
        self.resize(900, 640)

        summary = QLabel(
            tr("{options} options and {arguments} arguments were read from this text "
               "(source: {source}, confidence {confidence}).",
               options=len(spec.options),
               arguments=len(spec.positionals),
               source=spec.source.value,
               confidence=f"{spec.confidence:.0%}")
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("color: palette(mid);")

        viewer = QTextEdit()
        viewer.setReadOnly(True)
        viewer.setHtml(ansi_to_html(spec.raw_help or tr("No help text was captured.")))
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
        buttons.button(QDialogButtonBox.Close).setText(tr("Close"))
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
