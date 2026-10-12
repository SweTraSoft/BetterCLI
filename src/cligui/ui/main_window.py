"""The application window: command entry, generated form, preview and output."""

from __future__ import annotations

import logging
import shlex

from PySide6.QtCore import QObject, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (
    QAction,
    QColor,
    QFontMetrics,
    QKeySequence,
    QPalette,
    QPainter,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from cligui.builder import build_argv, missing_required, preview
from cligui.discovery import (
    CommandNotFoundError,
    DiscoveryError,
    DiscoveryService,
    split_command,
)
from cligui.execution import CommandRunner
from cligui.history import CommandHistory
from cligui.discovery.runner import resolve_binary
from cligui.model.spec import CommandSpec
from cligui.settings import Settings
from cligui.ui.dialogs import HelpTextDialog, SettingsDialog
from cligui.ui.form_view import FormView
from cligui.ui.output_view import OutputView

log = logging.getLogger(__name__)

COMMON_COMMANDS = (
    "git",
    "ls",
    "grep",
    "find",
    "cat",
    "less",
    "pwd",
    "mkdir",
    "cp",
    "mv",
    "curl",
    "ssh",
    "tar",
    "python",
    "pip",
    "npm",
    "docker",
    "make",
    "jq",
    "rsync",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "sed",
    "awk",
    "xargs",
    "touch",
    "rm",
    "chmod",
    "df",
    "du",
    "ps",
    "env",
    "which",
    "whoami",
    "man",
    "zip",
    "unzip",
    "node",
    "npx",
    "uv",
    "go",
    "brew",
)
COMMAND_DESCRIPTIONS = {
    "git": "Track changes and manage version history",
    "ls": "List files and directories",
    "grep": "Search text with patterns",
    "find": "Locate files by name or attributes",
    "cat": "Print or combine file contents",
    "less": "Read text one screen at a time",
    "pwd": "Show the current directory",
    "mkdir": "Create directories",
    "cp": "Copy files and directories",
    "mv": "Move or rename files",
    "curl": "Transfer data using URLs",
    "ssh": "Connect to a remote machine",
    "tar": "Archive or extract files",
    "python": "Run Python programs",
    "pip": "Install and manage Python packages",
    "npm": "Manage Node.js packages and scripts",
    "docker": "Build and run containers",
    "make": "Run tasks defined in a Makefile",
    "jq": "Query and transform JSON",
    "rsync": "Synchronize files efficiently",
    "head": "Show the first lines of a file",
    "tail": "Show the last lines of a file",
    "wc": "Count lines, words, and bytes",
    "sort": "Sort lines of text",
    "uniq": "Find or remove repeated adjacent lines",
    "cut": "Extract columns from text",
    "tr": "Translate or remove characters",
    "sed": "Edit text streams",
    "awk": "Filter and process structured text",
    "xargs": "Build commands from input",
    "touch": "Create files or update timestamps",
    "rm": "Remove files or directories",
    "chmod": "Change file permissions",
    "df": "Show available disk space",
    "du": "Show file and directory sizes",
    "ps": "List running processes",
    "env": "Show or set environment variables",
    "which": "Locate a command on PATH",
    "whoami": "Show the current user",
    "man": "Read command manuals",
    "zip": "Create compressed archives",
    "unzip": "Extract ZIP archives",
    "node": "Run JavaScript with Node.js",
    "npx": "Run Node.js packages",
    "uv": "Manage Python projects and tools",
    "go": "Build and run Go programs",
    "brew": "Install and manage macOS packages",
}
COMMAND_DESCRIPTION_ROLE = Qt.ItemDataRole.UserRole + 1

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

    succeeded = Signal(object, object, object)
    failed = Signal(str)

    def __init__(
        self,
        service: DiscoveryService,
        argv: list[str],
        refresh: bool,
        parent_argv: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._service = service
        self._argv = argv
        self._refresh = refresh
        self._parent_argv = parent_argv

    def run(self) -> None:
        try:
            parent_result = (
                self._service.discover(self._parent_argv, refresh=self._refresh)
                if self._parent_argv is not None
                else None
            )
            result = self._service.discover(self._argv, refresh=self._refresh)
        except DiscoveryError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            log.exception("discovery failed")
            self.failed.emit(f"Unexpected error during discovery: {exc}")
        else:
            self.succeeded.emit(result.spec, result, parent_result)


class _CommandSuggestionDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index) -> None:
        item_option = QStyleOptionViewItem(option)
        self.initStyleOption(item_option, index)
        command = item_option.text
        description = index.data(COMMAND_DESCRIPTION_ROLE) or ""
        item_option.text = ""

        style = item_option.widget.style() if item_option.widget else self.parent().style()
        style.drawControl(
            QStyle.ControlElement.CE_ItemViewItem,
            item_option,
            painter,
            item_option.widget,
        )

        text_rect = item_option.rect.adjusted(10, 0, -10, 0)
        selected = bool(item_option.state & QStyle.StateFlag.State_Selected)
        if selected:
            text_color = item_option.palette.color(QPalette.ColorRole.HighlightedText)
        else:
            text_color = item_option.palette.color(QPalette.ColorRole.Text)

        painter.save()
        painter.setPen(text_color)
        command_font = item_option.font
        command_font.setBold(True)
        painter.setFont(command_font)
        command_width = QFontMetrics(command_font).horizontalAdvance(command)
        command_rect = text_rect.adjusted(
            0, 0, -max(0, text_rect.width() - command_width), 0
        )
        painter.drawText(
            command_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            command,
        )
        if description:
            description_rect = text_rect.adjusted(command_width + 12, 0, 0, 0)
            description_font = item_option.font
            description_font.setBold(False)
            description_font.setPointSizeF(max(8.0, description_font.pointSizeF() - 1))
            painter.setFont(description_font)
            description_color = (
                text_color
                if selected
                else item_option.palette.color(QPalette.ColorRole.Mid)
            )
            painter.setPen(description_color)
            visible_description = QFontMetrics(description_font).elidedText(
                description,
                Qt.TextElideMode.ElideRight,
                description_rect.width(),
            )
            painter.drawText(
                description_rect,
                Qt.AlignmentFlag.AlignVCenter,
                visible_description,
            )
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        hint = super().sizeHint(option, index)
        return QSize(max(hint.width(), 440), max(hint.height(), 30))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BetterCLI")
        self.resize(QSize(1220, 760))

        self.settings = Settings.load()
        self.service = DiscoveryService(self.settings)
        self.history = CommandHistory()
        self.runner = CommandRunner(self)
        self._spec: CommandSpec | None = None
        self._subcommand_owner: list[str] | None = None
        self._subcommand_descriptions: dict[str, str] = {}
        self._thread: QThread | None = None
        self._worker: _DiscoveryWorker | None = None
        self._updating_preview = False
        self._editor_typed = False
        self._keep_typed_command = False
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(500)
        self._search_timer.timeout.connect(self.discover)

        self._build_ui()
        self._connect()
        self._update_preview()

    # ----- construction -------------------------------------------------

    def _build_ui(self) -> None:
        self.history_list = QListWidget()
        self.history_list.setAccessibleName("Recent commands")
        self.history_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.history_list.setSpacing(2)
        self.history_list.setStyleSheet(
            "QListWidget { border: none; background: palette(window); }"
            "QListWidget::item { padding: 9px 10px; border-radius: 4px; }"
            "QListWidget::item:hover { background: palette(midlight); }"
            "QListWidget::item:selected {"
            " background: palette(highlight); color: palette(highlighted-text); }"
        )
        self.history_empty = QLabel("No recent commands")
        self.history_empty.setWordWrap(True)
        self.history_empty.setContentsMargins(10, 8, 10, 8)

        sidebar = QWidget()
        sidebar.setMinimumWidth(160)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 8, 12)
        history_heading = QLabel("Recent commands")
        heading_font = history_heading.font()
        heading_font.setBold(True)
        history_heading.setFont(heading_font)
        sidebar_layout.addWidget(history_heading)
        sidebar_layout.addWidget(self.history_empty)
        sidebar_layout.addWidget(self.history_list, 1)

        self.command_input = QComboBox()
        self.command_input.setEditable(True)
        # History is managed explicitly, so Qt must not insert entries itself.
        self.command_input.setInsertPolicy(QComboBox.NoInsert)
        self.command_input.setMaxVisibleItems(20)
        self.command_input.lineEdit().setPlaceholderText(
            "Command to configure, e.g. rsync, git log, ffmpeg"
        )
        self.command_input.lineEdit().setClearButtonEnabled(True)
        # Qt's inline completion rewrites the typed text and moves the caret back
        # into it; suggestions stay available through the dropdown instead.
        self.command_input.setCompleter(None)
        self.command_input.setToolTip("Common CLI commands are listed here")
        self.command_input.setItemDelegate(
            _CommandSuggestionDelegate(self.command_input)
        )
        self.command_input.view().setMinimumWidth(460)
        self._command_input_palette = QPalette(self.command_input.lineEdit().palette())
        self._populate_command_suggestions()
        self._refresh_history()

        self.command_description = QLabel()
        self.command_description.setMaximumWidth(260)
        self.command_description.setWordWrap(True)
        self.command_description.setStyleSheet("color: palette(mid);")
        self.command_description.hide()

        self.discover_button = QPushButton("Discover")
        self.discover_button.setDefault(True)
        self.help_text_button = QPushButton("Show help text")
        self.help_text_button.setToolTip(
            "Show the original --help output these options were read from"
        )
        self.help_text_button.setEnabled(False)
        self.clear_inputs_button = QPushButton("Clear inputs")
        self.clear_inputs_button.setToolTip("Clear the command and command line")

        self.subcommand_combo = QComboBox()
        self.subcommand_combo.setMinimumWidth(240)
        self.subcommand_combo.setMaxVisibleItems(25)
        self.subcommand_combo.setToolTip("Open a subcommand of the current command")
        self.subcommand_combo.hide()

        command_row = QHBoxLayout()
        command_row.addWidget(self.command_input, 1)
        command_row.addWidget(self.command_description)
        command_row.addWidget(self.subcommand_combo)
        command_row.addWidget(self.discover_button)
        command_row.addWidget(self.help_text_button)
        command_row.addWidget(self.clear_inputs_button)

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
        upper_layout.addWidget(self.form, 1)

        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.addWidget(QLabel("Command Line Interface"))
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

        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(command_row)
        layout.addWidget(splitter, 1)

        central = QSplitter(Qt.Horizontal)
        central.addWidget(sidebar)
        central.addWidget(workspace)
        central.setChildrenCollapsible(False)
        central.setStretchFactor(0, 0)
        central.setStretchFactor(1, 1)
        central.setSizes([220, 1000])
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

        menu = self.menuBar().addMenu("Tools")
        menu.addAction(settings_action)
        menu.addAction(clear_history_action)
        menu.addAction(clear_cache_action)

    def _connect(self) -> None:
        self.history_list.itemDoubleClicked.connect(self._open_history_command)
        self.history_list.itemActivated.connect(self._open_history_command)
        open_history_action = QAction(self.history_list)
        open_history_action.setShortcuts(
            [QKeySequence(Qt.Key_Return), QKeySequence(Qt.Key_Enter)]
        )
        open_history_action.setShortcutContext(Qt.WidgetShortcut)
        open_history_action.triggered.connect(
            lambda: self._open_history_command(self.history_list.currentItem())
        )
        self.history_list.addAction(open_history_action)
        self.command_input.lineEdit().textEdited.connect(
            self._on_command_text_edited
        )
        self.command_input.currentTextChanged.connect(
            lambda _: self._update_command_description()
        )
        self.command_input.currentTextChanged.connect(self._update_command_input_width)
        self._update_command_input_width(self.command_input.currentText())
        self.command_input.lineEdit().returnPressed.connect(self.discover)
        self.command_input.activated.connect(lambda _: self.discover())
        self.discover_button.clicked.connect(self.discover)
        self.clear_inputs_button.clicked.connect(self._clear_inputs)
        self.subcommand_combo.activated.connect(self._open_subcommand)
        self.form.changed.connect(self._update_preview)
        self.command_editor.textChanged.connect(self._on_command_editor_changed)
        self.help_text_button.clicked.connect(self._show_help_text)
        self.cwd_button.clicked.connect(self._choose_cwd)
        self.copy_button.clicked.connect(self._copy_command)
        self.run_button.clicked.connect(self.run)
        self.cancel_button.clicked.connect(self.runner.cancel)
        self.clear_output_button.clicked.connect(self.output.clear)

        self.runner.output.connect(self.output.append_text)
        self.runner.failed.connect(self._on_run_failed)
        self.runner.finished.connect(self._on_run_finished)

    def _update_command_input_width(self, command: str) -> None:
        text_width = self.command_input.lineEdit().fontMetrics().horizontalAdvance(command)
        self.command_input.setMinimumWidth(max(160, text_width + 64))

    # ----- discovery ----------------------------------------------------

    def discover(
        self, refresh: bool = False, argv: list[str] | None = None
    ) -> None:
        self._search_timer.stop()
        if self._thread is not None:
            return
        try:
            argv = argv or split_command(self.command_input.currentText())
            self.service.preflight(argv)
        except CommandNotFoundError as exc:
            self._set_command_input_invalid(True)
            self.statusBar().showMessage(str(exc))
            return
        except DiscoveryError as exc:
            self._set_command_input_invalid(False)
            self._warn("Cannot read that command", str(exc))
            return

        self._set_command_input_invalid(False)
        self._set_discovering(True)
        parent_argv = None
        if len(argv) > 1 and (
            self._subcommand_owner is None
            or argv[: len(self._subcommand_owner)] != self._subcommand_owner
        ):
            parent_argv = argv[:1]

        thread = QThread(self)
        worker = _DiscoveryWorker(self.service, argv, refresh, parent_argv)
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

    def _on_command_text_edited(self, _text: str) -> None:
        self._set_command_input_invalid(False)
        self._search_timer.start()

    def _set_command_input_invalid(self, invalid: bool) -> None:
        line_edit = self.command_input.lineEdit()
        if not invalid:
            line_edit.setPalette(self._command_input_palette)
            return

        palette = QPalette(self._command_input_palette)
        base = palette.color(QPalette.ColorRole.Base)
        tint = QColor(220, 70, 70)
        strength = 0.16
        palette.setColor(
            QPalette.ColorRole.Base,
            QColor(
                round(base.red() * (1 - strength) + tint.red() * strength),
                round(base.green() * (1 - strength) + tint.green() * strength),
                round(base.blue() * (1 - strength) + tint.blue() * strength),
            ),
        )
        line_edit.setPalette(palette)

    def _set_discovering(self, busy: bool) -> None:
        self.discover_button.setEnabled(not busy)
        self.history_list.setEnabled(not busy)
        if busy:
            self.statusBar().showMessage("Reading --help…")

    def _on_thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
        self._worker = None
        self._set_discovering(False)

    def _on_discovered(self, spec: CommandSpec, result, parent_result=None) -> None:
        self._spec = spec
        self._keep_typed_command = self._editor_typed
        try:
            self.form.load(spec)
        finally:
            self._keep_typed_command = False
        self.help_text_button.setEnabled(bool(spec.raw_help))
        self.history.add(spec.display_name)
        self._refresh_history()
        if parent_result is not None:
            self._refresh_subcommands(parent_result.spec)
        self._refresh_subcommands(spec)
        self._update_command_description()
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
        if not spec.subcommands:
            try:
                current_argv = split_command(self.command_input.currentText())
            except DiscoveryError:
                current_argv = []
            if (
                self._subcommand_owner is not None
                and (
                    (
                        len(current_argv) > len(self._subcommand_owner)
                        and current_argv[: len(self._subcommand_owner)]
                        == self._subcommand_owner
                    )
                    or (
                        len(spec.argv_prefix) > len(self._subcommand_owner)
                        and spec.argv_prefix[: len(self._subcommand_owner)]
                        == self._subcommand_owner
                    )
                )
            ):
                child_argv = (
                    spec.argv_prefix
                    if spec.argv_prefix[: len(self._subcommand_owner)]
                    == self._subcommand_owner
                    else current_argv
                )
                child = child_argv[len(self._subcommand_owner)]
                child_index = self.subcommand_combo.findData(child)
                if child_index >= 0:
                    self.subcommand_combo.setCurrentIndex(child_index)
                self.subcommand_combo.setVisible(True)
                self._update_command_description()
                return

        self.subcommand_combo.blockSignals(True)
        self.subcommand_combo.clear()
        if spec.subcommands:
            self._subcommand_owner = list(spec.argv_prefix)
            self._subcommand_descriptions = {
                subcommand.name: subcommand.help for subcommand in spec.subcommands
            }
            self.subcommand_combo.addItem(
                f"Subcommands ({len(spec.subcommands)})…", userData=None
            )
            for sub in spec.subcommands:
                self.subcommand_combo.addItem(sub.display, userData=sub.name)
        else:
            self._subcommand_owner = None
            self._subcommand_descriptions = {}
        self.subcommand_combo.blockSignals(False)
        self.subcommand_combo.setVisible(bool(spec.subcommands))

    def _update_command_description(self) -> None:
        try:
            argv = split_command(self.command_input.currentText())
        except DiscoveryError:
            argv = []

        description = COMMAND_DESCRIPTIONS.get(argv[0], "") if argv else ""
        selected_subcommand = self.subcommand_combo.currentData()
        owner = self._subcommand_owner
        if selected_subcommand and owner and argv[: len(owner)] == owner:
            if len(argv) == len(owner) or argv[len(owner)] == selected_subcommand:
                description = (
                    self._subcommand_descriptions.get(selected_subcommand)
                    or description
                )

        self.command_description.setText(description)
        self.command_description.setToolTip(description)
        self.command_description.setVisible(bool(description))

    def _open_subcommand(self, index: int) -> None:
        name = self.subcommand_combo.itemData(index)
        if not name or self._spec is None:
            return
        parent_argv = self._subcommand_owner or self._spec.argv_prefix
        argv = [*parent_argv, name]
        self._set_command_text(argv[0])
        self.subcommand_combo.setCurrentIndex(index)
        self.discover(argv=argv)

    def _on_discovery_failed(self, message: str) -> None:
        self.statusBar().showMessage("Discovery failed")
        self._warn("Could not discover options", message)

    def _populate_command_suggestions(self) -> None:
        """Fill the suggestion list once; later model edits rewrite the typed text."""
        self.command_input.addItems(COMMON_COMMANDS)
        # A selected row makes Qt replace whatever the user typed.
        self.command_input.setCurrentIndex(-1)
        model = self.command_input.model()
        if not isinstance(model, QStandardItemModel):
            return
        for index, command in enumerate(COMMON_COMMANDS):
            item = model.item(index)
            if item is None:
                continue
            description = COMMAND_DESCRIPTIONS.get(command, "")
            item.setData(description, COMMAND_DESCRIPTION_ROLE)
            item.setToolTip(description)
            try:
                resolve_binary(command)
            except CommandNotFoundError:
                item.setEnabled(False)

    def _set_command_text(self, text: str) -> None:
        """Leave the field alone while the user is typing in it."""
        if self.command_input.lineEdit().hasFocus():
            return
        self.command_input.setCurrentText(text)

    def _refresh_history(self) -> None:
        """Refresh the recent commands sidebar without touching the command field."""
        recent_commands = self.history.items()
        self.history_list.clear()
        active = self._spec.display_name if self._spec is not None else None
        for command in recent_commands:
            item = QListWidgetItem(command, self.history_list)
            item.setToolTip(command)
            item.setSizeHint(QSize(0, 40))
            if command == active:
                self.history_list.setCurrentItem(item)
        self.history_empty.setVisible(not recent_commands)

    def _open_history_command(self, item: QListWidgetItem | None) -> None:
        if item is None or self._thread is not None:
            return
        self._set_command_text(item.text())
        self.discover()

    def _clear_history(self) -> None:
        self.history.clear()
        self._refresh_history()
        self.statusBar().showMessage("Command history cleared")

    def _clear_inputs(self) -> None:
        self._search_timer.stop()
        self.command_input.setCurrentIndex(-1)
        self.command_input.clearEditText()
        self._set_command_input_invalid(False)
        self.command_editor.clear()
        self.subcommand_combo.hide()
        self._subcommand_owner = None
        self._subcommand_descriptions = {}

    # ----- command assembly and execution --------------------------------

    def _current_argv(self) -> list[str] | None:
        try:
            return shlex.split(self.command_editor.toPlainText()) or None
        except ValueError:
            return None

    def _update_preview(self) -> None:
        if self._keep_typed_command:
            self._on_command_edited()
            return
        self._updating_preview = True
        try:
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
                    self.command_editor.setPlainText(
                        preview(build_argv(self._spec, values))
                    )
        finally:
            self._updating_preview = False
        self._editor_typed = False
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

    def _on_command_editor_changed(self) -> None:
        self._on_command_edited()
        if self._updating_preview:
            return
        self._editor_typed = True

        try:
            argv = shlex.split(self.command_editor.toPlainText())
        except ValueError:
            self._search_timer.stop()
            return
        if not argv:
            self._search_timer.stop()
            return

        target = argv[:1]
        if self._spec is not None:
            current_prefix = self._spec.argv_prefix
            if argv[: len(current_prefix)] == current_prefix:
                remaining = argv[len(current_prefix) :]
                if not remaining:
                    return
                subcommands = {
                    subcommand.name for subcommand in self._spec.subcommands
                }
                if remaining[0] not in subcommands:
                    return
                target = [*current_prefix, remaining[0]]

        self._set_command_text(shlex.join(target))
        self._search_timer.start()

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
