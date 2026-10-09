"""Modal dialogs: settings, safety confirmation and preset naming."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cligui.safety import Finding, Severity
from cligui.settings import ENV_API_KEY, Settings, get_api_key, set_api_key


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(460)
        self._settings = settings

        form = QFormLayout()
        self._llm_enabled = QCheckBox("Use DeepSeek when --help cannot be parsed")
        self._llm_enabled.setChecked(settings.llm_enabled)

        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.Password)
        self._api_key.setPlaceholderText(
            "stored in your Keychain" if get_api_key() is None else "unchanged"
        )

        self._base_url = QLineEdit(settings.base_url)
        self._model = QLineEdit(settings.model)

        self._timeout = QDoubleSpinBox()
        self._timeout.setRange(1.0, 120.0)
        self._timeout.setSuffix(" s")
        self._timeout.setValue(settings.discovery_timeout)

        form.addRow("LLM fallback", self._llm_enabled)
        form.addRow("API key", self._api_key)
        form.addRow("Base URL", self._base_url)
        form.addRow("Model", self._model)
        form.addRow("Discovery timeout", self._timeout)

        note = QLabel(
            f"The {ENV_API_KEY} environment variable overrides the stored key. "
            "Help text is sent to DeepSeek only when the built-in parser is unsure."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: palette(mid);")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self._settings.llm_enabled = self._llm_enabled.isChecked()
        self._settings.base_url = self._base_url.text().strip() or self._settings.base_url
        self._settings.model = self._model.text().strip() or self._settings.model
        self._settings.discovery_timeout = self._timeout.value()
        self._settings.save()
        if key := self._api_key.text().strip():
            if not set_api_key(key):
                QMessageBox.warning(
                    self,
                    "Could not save the key",
                    f"Your keychain refused the write. Set {ENV_API_KEY} instead.",
                )
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

        viewer = QPlainTextEdit()
        viewer.setReadOnly(True)
        viewer.setPlainText(spec.raw_help or "No help text was captured.")
        viewer.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = QFont("Menlo")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(12)
        viewer.setFont(font)

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


class PresetDialog(QDialog):
    """Pick an existing preset name or type a new one."""

    def __init__(self, names: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Save preset")
        self._combo = QComboBox()
        self._combo.setEditable(True)
        self._combo.addItems(names)
        self._combo.setCurrentText("")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Preset name"))
        layout.addWidget(self._combo)
        layout.addWidget(buttons)

    def name(self) -> str:
        return self._combo.currentText().strip()
