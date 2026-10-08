"""The application window: command entry, generated form, preview and output."""

from __future__ import annotations

import logging
import shlex

from PySide6.QtCore import QObject, QSize, Qt, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from cligui.builder import build_argv, missing_required, preview
from cligui.discovery import DiscoveryError, DiscoveryService, split_command
from cligui.execution import CommandRunner
from cligui.history import CommandHistory
from cligui.model.spec import CommandSpec
from cligui.presets import PresetStore
from cligui.settings import Settings
from cligui.ui.dialogs import HelpTextDialog, PresetDialog, SettingsDialog
from cligui.ui.form_view import FormView
from cligui.ui.output_view import OutputView

log = logging.getLogger(__name__)

#: Applied to Run when a command is ready; `palette(highlight)` follows the OS accent.
RUN_READY_STYLE = (
    "QPushButton {"
    " background-color: palette(highlight);"
    " color: palette(highlighted-text);"
    " border: 1px solid palette(highlight);"
    " border-radius: 5px; padding: 4px 16px; font-weight: 600;"
    "}"
    "QPushButton:pressed { background-color: palette(dark); border-color: palette(dark); }"
)


class _DiscoveryWorker(QObject):
    """Runs discovery off the GUI thread; the child process may block for seconds."""

    succeeded = Signal(object, object)
    failed = Signal(str)

    def __init__(self, service: DiscoveryService, argv: list[str], refresh: bool) -> None:
        super().__init__()
        self._service = service
        self._argv = argv
        self._refresh = refresh

    def run(self) -> None:
        try:
            result = self._service.discover(self._argv, refresh=self._refresh)
        except DiscoveryError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            log.exception("discovery failed")
            self.failed.emit(f"Unexpected error during discovery: {exc}")
        else:
            self.succeeded.emit(result.spec, result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("cligui")
        self.resize(QSize(1000, 760))

        self.settings = Settings.load()
        self.service = DiscoveryService(self.settings)
        self.presets = PresetStore()
        self.history = CommandHistory()
        self.runner = CommandRunner(self)
        self._spec: CommandSpec | None = None
        self._thread: QThread | None = None
        self._worker: _DiscoveryWorker | None = None
        self._approved_binaries: set[str] = set()

        self._build_ui()
        self._connect()
        self._update_preview()

    # ----- construction -------------------------------------------------

    def _build_ui(self) -> None:
        self.command_input = QComboBox()
        self.command_input.setEditable(True)
        # History is managed explicitly, so Qt must not insert entries itself.
        self.command_input.setInsertPolicy(QComboBox.NoInsert)
        self.command_input.setMaxVisibleItems(20)
        self.command_input.lineEdit().setPlaceholderText(
            "Command to configure, e.g. rsync, git log, ffmpeg"
        )
        self.command_input.lineEdit().setClearButtonEnabled(True)
        self.command_input.setToolTip("Recently used commands are listed here")
        self._refresh_history()

        self.discover_button = QPushButton("Discover")
        self.discover_button.setDefault(True)
        self.refresh_button = QPushButton("Re-scan")
        self.refresh_button.setToolTip("Ignore the cached options and read --help again")

        self.subcommand_combo = QComboBox()
        self.subcommand_combo.setMinimumWidth(240)
        self.subcommand_combo.setMaxVisibleItems(25)
        self.subcommand_combo.setToolTip("Open a subcommand of the current command")
        self.subcommand_combo.hide()

        command_row = QHBoxLayout()
        command_row.addWidget(self.command_input, 1)
        command_row.addWidget(self.subcommand_combo)
        command_row.addWidget(self.discover_button)
        command_row.addWidget(self.refresh_button)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter options…")
        self.filter_input.setClearButtonEnabled(True)

        self.help_text_button = QPushButton("Help text")
        self.help_text_button.setToolTip(
            "Show the original --help output these options were read from"
        )
        self.help_text_button.setEnabled(False)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(160)
        self.preset_combo.setToolTip("Load a saved configuration")
        self.save_preset_button = QPushButton("Save preset")
        self.reset_button = QPushButton("Reset")

        tools_row = QHBoxLayout()
        tools_row.addWidget(self.filter_input, 1)
        tools_row.addWidget(self.help_text_button)
        tools_row.addWidget(self.preset_combo)
        tools_row.addWidget(self.save_preset_button)
        tools_row.addWidget(self.reset_button)

        self.form = FormView()

        self.command_editor = QPlainTextEdit()
        self.command_editor.setTabChangesFocus(True)
        self.command_editor.setFixedHeight(84)
        self.command_editor.setStyleSheet(
            "font-family: Menlo, monospace;"
            "background: palette(base); padding: 8px; border-radius: 4px;"
        )

        self.cwd_input = QLineEdit()
        self.cwd_input.setPlaceholderText("Working directory (defaults to your home)")
        self.cwd_button = QPushButton("Choose…")
        self.copy_button = QPushButton("Copy")
        self.run_button = QPushButton("Run")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)

        run_row = QHBoxLayout()
        run_row.addWidget(self.cwd_input, 1)
        run_row.addWidget(self.cwd_button)
        run_row.addWidget(self.copy_button)
        run_row.addWidget(self.run_button)
        run_row.addWidget(self.cancel_button)

        upper = QWidget()
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addLayout(tools_row)
        upper_layout.addWidget(self.form, 1)

        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.addWidget(QLabel("Command"))
        lower_layout.addWidget(self.command_editor)
        lower_layout.addLayout(run_row)

        self.clear_output_button = QPushButton("Clear")
        self.clear_output_button.setToolTip("Clear the output below")
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output"))
        output_row.addStretch(1)
        output_row.addWidget(self.clear_output_button)
        lower_layout.addLayout(output_row)

        self.output = OutputView()
        lower_layout.addWidget(self.output, 1)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(upper)
        splitter.addWidget(lower)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(command_row)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.statusBar().showMessage("Ready")
        self._build_menu()

    def _build_menu(self) -> None:
        settings_action = QAction("Settings…", self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.triggered.connect(self._open_settings)

        clear_cache_action = QAction("Clear discovery cache", self)
        clear_cache_action.triggered.connect(self._clear_cache)

        clear_history_action = QAction("Clear command history", self)
        clear_history_action.triggered.connect(self._clear_history)

        delete_preset_action = QAction("Delete selected preset", self)
        delete_preset_action.triggered.connect(self._delete_preset)

        menu = self.menuBar().addMenu("Tools")
        menu.addAction(settings_action)
        menu.addAction(delete_preset_action)
        menu.addSeparator()
        menu.addAction(clear_history_action)
        menu.addAction(clear_cache_action)

    def _connect(self) -> None:
        self.command_input.lineEdit().returnPressed.connect(self.discover)
        self.command_input.activated.connect(lambda _: self.discover())
        self.discover_button.clicked.connect(self.discover)
        self.refresh_button.clicked.connect(lambda: self.discover(refresh=True))
        self.subcommand_combo.activated.connect(self._open_subcommand)
        self.filter_input.textChanged.connect(self.form.apply_filter)
        self.form.changed.connect(self._update_preview)
        self.command_editor.textChanged.connect(self._on_command_edited)
        self.help_text_button.clicked.connect(self._show_help_text)
        self.reset_button.clicked.connect(self.form.reset_values)
        self.save_preset_button.clicked.connect(self._save_preset)
        self.preset_combo.activated.connect(self._load_preset)
        self.cwd_button.clicked.connect(self._choose_cwd)
        self.copy_button.clicked.connect(self._copy_command)
        self.run_button.clicked.connect(self.run)
        self.cancel_button.clicked.connect(self.runner.cancel)
        self.clear_output_button.clicked.connect(self.output.clear)

        self.runner.output.connect(self.output.append_text)
        self.runner.failed.connect(self._on_run_failed)
        self.runner.finished.connect(self._on_run_finished)

    # ----- discovery ----------------------------------------------------

    def discover(self, refresh: bool = False) -> None:
        if self._thread is not None:
            return
        try:
            argv = split_command(self.command_input.currentText())
            binary = self.service.preflight(argv)
        except DiscoveryError as exc:
            self._warn("Cannot read that command", str(exc))
            return

        if self.settings.confirm_unknown_binaries and str(binary) not in self._approved_binaries:
            answer = QMessageBox.question(
                self,
                "Run --help?",
                f"cligui will run:\n\n{binary} --help\n\n"
                "to discover the available options. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return
            self._approved_binaries.add(str(binary))

        self._set_discovering(True)
        thread = QThread(self)
        worker = _DiscoveryWorker(self.service, argv, refresh)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.succeeded.connect(self._on_discovered)
        worker.failed.connect(self._on_discovery_failed)
        for signal in (worker.succeeded, worker.failed):
            signal.connect(thread.quit)
        thread.finished.connect(self._on_thread_finished)
        # Qt holds no Python reference to the worker, so without this it would be
        # garbage collected mid-run and take the thread down with it.
        self._thread = thread
        self._worker = worker
        thread.start()

    def _set_discovering(self, busy: bool) -> None:
        self.discover_button.setEnabled(not busy)
        self.refresh_button.setEnabled(not busy)
        if busy:
            self.statusBar().showMessage("Reading --help…")

    def _on_thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
        self._worker = None
        self._set_discovering(False)

    def _on_discovered(self, spec: CommandSpec, result) -> None:
        self._spec = spec
        self.form.load(spec)
        self.filter_input.clear()
        self.help_text_button.setEnabled(bool(spec.raw_help))
        self.history.add(spec.display_name)
        self._refresh_history()
        self._refresh_subcommands(spec)
        self._refresh_presets()

        origin = "cache" if result.from_cache else spec.source.value
        parts = [f"{len(spec.options)} options", f"{len(spec.positionals)} arguments"]
        if spec.subcommands:
            parts.append(f"{len(spec.subcommands)} subcommands")
        self.statusBar().showMessage(
            f"{spec.display_name}: {', '.join(parts)} (via {origin})"
        )
        if result.note:
            self.output.append_notice(result.note)

    def _refresh_subcommands(self, spec: CommandSpec) -> None:
        self.subcommand_combo.blockSignals(True)
        self.subcommand_combo.clear()
        if spec.subcommands:
            self.subcommand_combo.addItem(
                f"Subcommands ({len(spec.subcommands)})…", userData=None
            )
            for sub in spec.subcommands:
                self.subcommand_combo.addItem(sub.display, userData=sub.name)
        self.subcommand_combo.blockSignals(False)
        self.subcommand_combo.setVisible(bool(spec.subcommands))

    def _open_subcommand(self, index: int) -> None:
        name = self.subcommand_combo.itemData(index)
        if not name or self._spec is None:
            return
        self.command_input.setCurrentText(f"{self._spec.display_name} {name}")
        self.discover()

    def _on_discovery_failed(self, message: str) -> None:
        self.statusBar().showMessage("Discovery failed")
        self._warn("Could not discover options", message)

    # ----- presets ------------------------------------------------------

    def _refresh_history(self) -> None:
        """Repopulate the dropdown without disturbing what the user has typed."""
        typed = self.command_input.currentText()
        self.command_input.blockSignals(True)
        self.command_input.clear()
        self.command_input.addItems(self.history.items())
        self.command_input.setCurrentText(typed)
        self.command_input.blockSignals(False)

    def _clear_history(self) -> None:
        self.history.clear()
        self._refresh_history()
        self.statusBar().showMessage("Command history cleared")

    def _refresh_presets(self) -> None:
        self.preset_combo.clear()
        if self._spec is None:
            return
        names = self.presets.names(self._spec.argv_prefix)
        self.preset_combo.addItem("Presets…")
        self.preset_combo.addItems(names)
        self.preset_combo.setEnabled(bool(names))

    def _save_preset(self) -> None:
        if self._spec is None:
            return
        dialog = PresetDialog(self.presets.names(self._spec.argv_prefix), self)
        if dialog.exec() != PresetDialog.Accepted or not dialog.name():
            return
        self.presets.save(self._spec.argv_prefix, dialog.name(), self.form.values())
        self._refresh_presets()
        self.statusBar().showMessage(f"Saved preset “{dialog.name()}”")

    def _load_preset(self, index: int) -> None:
        if self._spec is None or index <= 0:
            return
        name = self.preset_combo.itemText(index)
        values = self.presets.load(self._spec.argv_prefix, name)
        if values is None:
            self._warn("Preset unavailable", f"“{name}” could not be read.")
            return
        self.form.set_values(values)
        self.statusBar().showMessage(f"Loaded preset “{name}”")

    def _delete_preset(self) -> None:
        index = self.preset_combo.currentIndex()
        if self._spec is None or index <= 0:
            return
        name = self.preset_combo.currentText()
        if self.presets.delete(self._spec.argv_prefix, name):
            self._refresh_presets()
            self.statusBar().showMessage(f"Deleted preset “{name}”")

    # ----- command assembly and execution --------------------------------

    def _current_argv(self) -> list[str] | None:
        try:
            return shlex.split(self.command_editor.toPlainText()) or None
        except ValueError:
            return None

    def _update_preview(self) -> None:
        if self._spec is None:
            self.command_editor.setPlaceholderText("No command configured yet.")
            self.command_editor.clear()
        else:
            values = self.form.values()
            outstanding = missing_required(self._spec, values)
            if outstanding:
                self.command_editor.setPlaceholderText(
                    f"{self._spec.display_name}  …  still required: "
                    f"{', '.join(outstanding)}"
                )
                self.command_editor.clear()
            else:
                self.command_editor.setPlainText(preview(build_argv(self._spec, values)))
        self._on_command_edited()

    def _on_command_edited(self) -> None:
        argv = self._current_argv()
        self.command_editor.setToolTip(
            "Invalid command: check for unmatched quotes"
            if argv is None and self.command_editor.toPlainText().strip()
            else ""
        )
        self.copy_button.setEnabled(argv is not None)
        self._set_run_ready(argv is not None and not self.runner.running)

    def _set_run_ready(self, ready: bool) -> None:
        """Highlight Run once there is a runnable command, and only one at a time."""
        self.run_button.setEnabled(ready)
        self.run_button.setStyleSheet(RUN_READY_STYLE if ready else "")
        self.run_button.setDefault(ready)
        self.discover_button.setDefault(not ready)

    def _copy_command(self) -> None:
        if (argv := self._current_argv()) is None:
            return
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(preview(argv))
        self.statusBar().showMessage("Command copied to the clipboard")

    def _choose_cwd(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Working directory")
        if chosen:
            self.cwd_input.setText(chosen)

    def run(self) -> None:
        argv = self._current_argv()
        if argv is None or self.runner.running:
            return

        self.output.append_notice(f"$ {preview(argv)}")
        try:
            self.runner.start(argv, self.cwd_input.text().strip() or None)
        except (RuntimeError, ValueError) as exc:
            self._warn("Could not start", str(exc))
            return

        self._set_run_ready(False)
        self.cancel_button.setEnabled(True)
        self.statusBar().showMessage("Running…")

    def _on_run_failed(self, message: str) -> None:
        self.output.append_notice(message)

    def _on_run_finished(self, code: int) -> None:
        self.cancel_button.setEnabled(False)
        if code == -1:
            summary = "Cancelled"
        elif code == 0:
            summary = "Finished successfully"
        else:
            summary = f"Exited with code {code}"
        self.output.append_notice(summary)
        self.statusBar().showMessage(summary)
        self._on_command_edited()

    # ----- misc ---------------------------------------------------------

    def _open_settings(self) -> None:
        if SettingsDialog(self.settings, self).exec() == SettingsDialog.Accepted:
            self.service.settings = self.settings
            self.statusBar().showMessage("Settings saved")

    def _show_help_text(self) -> None:
        if self._spec is not None:
            HelpTextDialog(self._spec, self).exec()

    def _clear_cache(self) -> None:
        removed = self.service.cache.clear()
        self.statusBar().showMessage(f"Cleared {removed} cached command(s)")

    def _warn(self, title: str, message: str) -> None:
        QMessageBox.warning(self, title, message)

    def closeEvent(self, event) -> None:
        if self.runner.running:
            self.runner.cancel()
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
        super().closeEvent(event)
