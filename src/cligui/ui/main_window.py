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
    QApplication,
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
from cligui.ui.output_view import MAX_BLOCKS, ROUNDED_FIELD_STYLE, OutputView
from cligui.ui.theme import apply_theme

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
        parent_argvs: list[list[str]] | None = None,
    ) -> None:
        super().__init__()
        self._service = service
        self._argv = argv
        self._refresh = refresh
        self._parent_argv = parent_argv
        self._parent_argvs = parent_argvs or ([parent_argv] if parent_argv else [])

    def run(self) -> None:
        try:
            parent_results = []
            for parent_argv in self._parent_argvs:
                if parent_results:
                    known_subcommands = {
                        subcommand.name
                        for subcommand in parent_results[-1].spec.subcommands
                    }
                    if parent_argv[-1] not in known_subcommands:
                        break
                parent_results.append(
                    self._service.discover(parent_argv, refresh=self._refresh)
                )
            result = self._service.discover(self._argv, refresh=self._refresh)
        except DiscoveryError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            log.exception("discovery failed")
            self.failed.emit(f"Unexpected error during discovery: {exc}")
        else:
            self.succeeded.emit(result.spec, result, parent_results)


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
        self._active_session: str | None = None
        self._running_session: str | None = None
        self._spec: CommandSpec | None = None
        self._subcommand_owner: list[str] | None = None
        self._subcommand_specs: dict[tuple[str, ...], CommandSpec] = {}
        self._subcommand_combos: list[QComboBox] = []
        self._subcommand_combo_owners: list[list[str] | None] = []
        self._selected_command_path: list[str] = []
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
        self.history_list.setSpacing(1)
        self.history_list.setStyleSheet(
            "QListWidget { border: none; background: palette(window); }"
            "QListWidget::item { padding: 5px 10px; border-radius: 4px; }"
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
        self.settings_button = QPushButton("Settings…")
        sidebar_layout.addWidget(self.settings_button)

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
        self.clear_inputs_button = QPushButton("New")
        self.clear_inputs_button.setToolTip("Start a new command")

        self.subcommand_combo = QComboBox()
        self.subcommand_combo.setMinimumWidth(240)
        self.subcommand_combo.setMaxVisibleItems(25)
        self.subcommand_combo.setToolTip("Open a subcommand of the current command")
        self.subcommand_combo.hide()
        self._subcommand_combos = [self.subcommand_combo]
        self._subcommand_combo_owners = [None]
        command_field_height = max(
            self.command_input.sizeHint().height(),
            self.subcommand_combo.sizeHint().height(),
        )
        self.command_input.setFixedHeight(command_field_height)
        self.subcommand_combo.setFixedHeight(command_field_height)
        self._command_field_text_inset = self.command_input.lineEdit().geometry().left()
        self.command_description.setIndent(self._command_field_text_inset)

        self._command_fields_row = QHBoxLayout()
        self._command_fields_row.setContentsMargins(0, 0, 0, 0)
        self._command_fields_row.addWidget(self.command_input, 1)
        self._command_fields_row.addWidget(self.subcommand_combo)
        self._command_fields_row.addWidget(self.discover_button)
        self._command_fields_row.addWidget(self.help_text_button)
        self._command_fields_row.addWidget(self.clear_inputs_button)
        # macOS layout-item margins differ between combo boxes and buttons.
        for widget in (
            self.command_input,
            self.subcommand_combo,
            self.discover_button,
            self.help_text_button,
            self.clear_inputs_button,
        ):
            widget.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect)
            widget.setFixedHeight(command_field_height)

        command_row = QVBoxLayout()
        command_row.setContentsMargins(0, 0, 0, 0)
        command_row.setSpacing(6)
        command_row.addLayout(self._command_fields_row)
        command_row.addWidget(self.command_description)

        self.form = FormView()

        self.command_editor = QPlainTextEdit()
        self.command_editor.setTabChangesFocus(True)
        self.command_editor.setFixedHeight(84)
        self.command_editor.setStyleSheet(ROUNDED_FIELD_STYLE)

        self.cwd_input = QLineEdit()
        self.cwd_input.setPlaceholderText("Working directory (defaults to your home)")
        self.cwd_input.setStyleSheet(ROUNDED_FIELD_STYLE)
        self.cwd_button = QPushButton("Choose…")
        self.copy_button = QPushButton("Copy")
        self.run_button = QPushButton("Run")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)

        cwd_row = QHBoxLayout()
        cwd_row.addWidget(self.cwd_input, 1)
        cwd_row.addWidget(self.cwd_button)
        cwd_field_height = self.cwd_input.sizeHint().height()
        for widget in (self.cwd_input, self.cwd_button):
            widget.setAttribute(Qt.WidgetAttribute.WA_LayoutUsesWidgetRect)
            widget.setFixedHeight(cwd_field_height)

        run_row = QHBoxLayout()
        run_row.addStretch(1)
        run_row.addWidget(self.copy_button)
        run_row.addWidget(self.run_button)
        run_row.addWidget(self.cancel_button)

        upper = QWidget()
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.addWidget(self.form, 1)

        self.command_line_heading = QLabel("Command Line Interface")
        self.output_heading = QLabel("Output")
        self.explore_heading = QLabel("Explore CLI commands")
        self.explore_heading.setIndent(self._command_field_text_inset)
        for heading in (
            self.explore_heading,
            self.command_line_heading,
            self.output_heading,
        ):
            heading_font = heading.font()
            heading_font.setBold(True)
            heading.setFont(heading_font)

        lower = QWidget()
        lower_layout = QVBoxLayout(lower)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(10)
        lower_layout.addLayout(cwd_row)
        lower_layout.addWidget(self.command_line_heading)
        lower_layout.addWidget(self.command_editor)
        lower_layout.addLayout(run_row)

        self.clear_output_button = QPushButton("Clear")
        self.clear_output_button.setToolTip("Clear the output below")
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_heading)
        output_row.addStretch(1)
        output_row.addWidget(self.clear_output_button)

        output_section = QWidget()
        output_layout = QVBoxLayout(output_section)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(2)
        output_layout.addLayout(output_row)
        self.output = OutputView()
        output_layout.addWidget(self.output, 1)
        lower_layout.addWidget(output_section, 1)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(upper)
        splitter.addWidget(lower)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        workspace = QWidget()
        layout = QVBoxLayout(workspace)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(self.explore_heading)
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
        self.history_list.itemClicked.connect(self._open_history_command)
        self.history_list.itemDoubleClicked.connect(self._open_history_command)
        self.history_list.itemActivated.connect(self._open_history_command)
        self.settings_button.clicked.connect(self._open_settings)
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
        self.command_input.activated.connect(
            lambda _: self._discover_selected_command()
        )
        self.discover_button.clicked.connect(self.discover)
        self.clear_inputs_button.clicked.connect(self._clear_inputs)
        self.subcommand_combo.activated.connect(
            lambda index: self._open_subcommand_from(self.subcommand_combo, index)
        )
        self.form.changed.connect(self._update_preview)
        self.command_editor.textChanged.connect(self._on_command_editor_changed)
        self.help_text_button.clicked.connect(self._show_help_text)
        self.cwd_button.clicked.connect(self._choose_cwd)
        self.copy_button.clicked.connect(self._copy_command)
        self.run_button.clicked.connect(self.run)
        self.cancel_button.clicked.connect(self.runner.cancel)
        self.clear_output_button.clicked.connect(self.output.clear)
        self.output.textChanged.connect(self._save_session_output)

        self.runner.output.connect(self._on_run_output)
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
        parent_argvs = [
            argv[:length]
            for length in range(1, len(argv))
        ]
        parent_argv = parent_argvs[-1] if parent_argvs else None

        thread = QThread(self)
        worker = _DiscoveryWorker(
            self.service, argv, refresh, parent_argv, parent_argvs
        )
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
        self._subcommand_specs.clear()
        self._selected_command_path = []
        self._populate_subcommand_combos([])
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
        if busy:
            self.statusBar().showMessage("Reading --help…")

    def _on_thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None
        self._worker = None
        self._set_discovering(False)

    def _on_discovered(self, spec: CommandSpec, result, parent_result=None) -> None:
        self.history.add(spec.display_name)
        self._activate_session(spec.display_name)
        self._spec = spec
        self._keep_typed_command = self._editor_typed
        try:
            self.form.load(spec)
        finally:
            self._keep_typed_command = False
        self.help_text_button.setEnabled(bool(spec.raw_help))
        self._refresh_history()
        selected_argv = list(spec.argv_prefix)
        try:
            entered_argv = split_command(self.command_input.currentText())
        except DiscoveryError:
            entered_argv = []
        parent_results = (
            parent_result
            if isinstance(parent_result, (list, tuple))
            else [parent_result]
            if parent_result is not None
            else []
        )
        complete_parent_chain = len(parent_results) == len(selected_argv) - 1 and all(
            parent.spec.argv_prefix == selected_argv[: index + 1]
            and selected_argv[index + 1]
            in {subcommand.name for subcommand in parent.spec.subcommands}
            for index, parent in enumerate(parent_results)
        )
        if (
            len(selected_argv) > 1
            and entered_argv == selected_argv
            and complete_parent_chain
        ):
            self.command_input.setCurrentText(shlex.quote(selected_argv[0]))

        for parent in parent_results:
            self._refresh_subcommands(parent.spec, selected_argv)
        self._refresh_subcommands(spec, selected_argv)
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

    def _ensure_subcommand_combo(self, level: int) -> QComboBox:
        while len(self._subcommand_combos) <= level:
            combo = QComboBox()
            combo.setMinimumWidth(180)
            combo.setMaxVisibleItems(25)
            combo.setFixedHeight(self.command_input.height())
            combo.hide()
            combo.activated.connect(
                lambda index, selected_combo=combo: self._open_subcommand_from(
                    selected_combo, index
                )
            )
            self._command_fields_row.insertWidget(
                1 + len(self._subcommand_combos), combo
            )
            self._subcommand_combos.append(combo)
            self._subcommand_combo_owners.append(None)
        return self._subcommand_combos[level]

    def _refresh_subcommands(
        self, spec: CommandSpec, selected_argv: list[str] | None = None
    ) -> None:
        prefix = tuple(spec.argv_prefix)
        if selected_argv is None:
            try:
                current_argv = split_command(self.command_input.currentText())
            except DiscoveryError:
                current_argv = []
            selected_argv = self._selected_command_path.copy()
            if current_argv and (
                not selected_argv
                or current_argv[0] != selected_argv[0]
                or len(current_argv) > len(selected_argv)
            ):
                selected_argv = current_argv
            if not selected_argv or selected_argv[0] != spec.argv_prefix[0]:
                selected_argv = list(spec.argv_prefix)

        if len(prefix) == 1:
            self._subcommand_specs = {prefix: spec}
        else:
            self._subcommand_specs = {
                parent: parent_spec
                for parent, parent_spec in self._subcommand_specs.items()
                if len(parent) < len(prefix) and prefix[: len(parent)] == parent
            }
            self._subcommand_specs[prefix] = spec
        self._selected_command_path = list(selected_argv)
        self._populate_subcommand_combos(selected_argv)

    def _populate_subcommand_combos(self, selected_argv: list[str]) -> None:
        if not selected_argv:
            active_count = 0
        else:
            owner = selected_argv[:1]
            active_count = 0
            while True:
                spec = self._subcommand_specs.get(tuple(owner))
                if spec is None or not spec.subcommands:
                    break
                combo = self._ensure_subcommand_combo(active_count)
                self._subcommand_combo_owners[active_count] = list(owner)
                combo.blockSignals(True)
                combo.clear()
                combo.addItem(
                    f"{owner[-1]} subcommands ({len(spec.subcommands)})…",
                    userData=None,
                )
                for subcommand in spec.subcommands:
                    combo.addItem(subcommand.display, userData=subcommand.name)
                if len(selected_argv) > len(owner):
                    selected_index = combo.findData(selected_argv[len(owner)])
                    if selected_index >= 0:
                        combo.setCurrentIndex(selected_index)
                combo.blockSignals(False)
                combo.setToolTip(f"Open a subcommand of {shlex.join(owner)}")
                combo.setVisible(True)
                active_count += 1

                selected = combo.currentData()
                if not selected:
                    break
                owner = [*owner, selected]

        for combo in self._subcommand_combos[active_count:]:
            combo.hide()
            combo.blockSignals(True)
            combo.clear()
            combo.blockSignals(False)
            self._subcommand_combo_owners[self._subcommand_combos.index(combo)] = None
        self._subcommand_owner = (
            self._subcommand_combo_owners[active_count - 1]
            if active_count
            else None
        )

    def _update_command_description(self) -> None:
        try:
            argv = split_command(self.command_input.currentText())
        except DiscoveryError:
            argv = []

        description = COMMAND_DESCRIPTIONS.get(argv[0], "") if argv else ""

        self.command_description.setText(description)
        self.command_description.setToolTip(description)
        self.command_description.setVisible(bool(description))

    def _open_subcommand(self, index: int) -> None:
        self._open_subcommand_from(self.subcommand_combo, index)

    def _open_subcommand_from(self, combo: QComboBox, index: int) -> None:
        name = combo.itemData(index)
        level = self._subcommand_combos.index(combo)
        owner = self._subcommand_combo_owners[level]
        if not name or owner is None:
            return
        argv = [*owner, name]
        self._selected_command_path = argv
        self._subcommand_specs = {
            prefix: spec
            for prefix, spec in self._subcommand_specs.items()
            if len(prefix) <= len(owner)
        }
        self.command_input.setCurrentText(shlex.quote(argv[0]))
        self._populate_subcommand_combos(argv)
        self._set_command_preview(argv)
        self.discover(argv=argv)

    def _discover_selected_command(self) -> None:
        try:
            argv = split_command(self.command_input.currentText())
        except DiscoveryError:
            self.discover()
            return
        self._set_command_preview(argv)
        self.discover(argv=argv)

    def _set_command_preview(self, argv: list[str]) -> None:
        self._updating_preview = True
        try:
            self.command_editor.setPlainText(preview(argv))
        finally:
            self._updating_preview = False
        self._editor_typed = False
        self._on_command_edited()

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
            item.setSizeHint(QSize(0, 30))
            if command == active:
                self.history_list.setCurrentItem(item)
        self.history_empty.setVisible(not recent_commands)

    def _open_history_command(self, item: QListWidgetItem | None) -> None:
        if item is None or self._thread is not None:
            return
        command = item.text()
        self.command_input.setCurrentText(command)
        self._activate_session(command)
        session = self.history.session(command)
        self._updating_preview = True
        try:
            self.command_editor.setPlainText(session["command_line"])
        finally:
            self._updating_preview = False
        self._editor_typed = bool(session["command_line"])

    def _activate_session(self, command: str) -> None:
        if command == self._active_session:
            return
        session = self.history.session(command)
        self._active_session = command
        self.output.setPlainText(session["output"])
        self.cwd_input.setText(session["cwd"])
        self.output.verticalScrollBar().setValue(
            self.output.verticalScrollBar().maximum()
        )

    def _save_session_output(self) -> None:
        if self._active_session is not None:
            self.history.update_session(
                self._active_session, output=self.output.toPlainText()
            )

    def _on_run_output(self, text: str) -> None:
        if self._running_session == self._active_session:
            self.output.append_text(text)
        elif self._running_session is not None:
            session = self.history.session(self._running_session)
            output = "\n".join((session["output"] + text).split("\n")[-MAX_BLOCKS:])
            self.history.update_session(self._running_session, output=output)

    def _append_run_notice(self, text: str) -> None:
        if self._running_session == self._active_session:
            self.output.append_notice(text)
        elif self._running_session is not None:
            output = self.history.session(self._running_session)["output"]
            prefix = "" if not output or output.endswith("\n") else "\n"
            self._on_run_output(f"{prefix}── {text} ──\n")

    def _clear_history(self) -> None:
        self.history.clear()
        self._refresh_history()
        self.statusBar().showMessage("Command history cleared")

    def _clear_inputs(self) -> None:
        self._search_timer.stop()
        self.command_input.setCurrentIndex(-1)
        self.command_input.clearEditText()
        self._set_command_input_invalid(False)
        self._spec = None
        self._active_session = None
        self._editor_typed = False
        self._keep_typed_command = False
        self.form.clear()
        self._update_preview()
        self.help_text_button.setEnabled(False)
        self.command_description.clear()
        self.command_description.hide()
        self.cwd_input.clear()
        self.output.clear()
        self._refresh_history()
        self._subcommand_specs.clear()
        self._selected_command_path = []
        self._populate_subcommand_combos([])
        self._subcommand_owner = None
        self.statusBar().showMessage("Ready")

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
    def run(self) -> None:
        argv = self._current_argv()
        if argv is None or self.runner.running:
            return

        command = (
            self._spec.display_name
            if self._spec is not None
            and argv[: len(self._spec.argv_prefix)] == self._spec.argv_prefix
            else preview(argv[:1])
        )
        cwd = self.cwd_input.text().strip()
        self.history.add(command)
        self._activate_session(command)
        self.cwd_input.setText(cwd)
        self.history.update_session(command, command_line=preview(argv), cwd=cwd)
        self._refresh_history()
        self._running_session = command
        self._append_run_notice(f"$ {preview(argv)}")
        try:
            self.runner.start(argv, cwd or None)
        except (RuntimeError, ValueError) as exc:
            self._append_run_notice(str(exc))
            self._running_session = None
            self._warn("Could not start", str(exc))
            return

        self._set_run_ready(False)
        self.cancel_button.setEnabled(True)
        self.statusBar().showMessage("Running…")

    def _on_run_failed(self, message: str) -> None:
        self._append_run_notice(message)

    def _on_run_finished(self, code: int) -> None:
        self.cancel_button.setEnabled(False)
        if code == -1:
            summary = "Cancelled"
        elif code == 0:
            summary = "Finished successfully"
        else:
            summary = f"Exited with code {code}"
        self._append_run_notice(summary)
        self._running_session = None
        self.statusBar().showMessage(summary)
        self._on_command_edited()

    # ----- misc ---------------------------------------------------------

    def _open_settings(self) -> None:
        if SettingsDialog(self.settings, self).exec() == SettingsDialog.Accepted:
            self.service.settings = self.settings
            application = QApplication.instance()
            if application is not None:
                apply_theme(application, self.settings.dark_mode)
                palette = QPalette(application.palette())
                self.command_input.lineEdit().setPalette(palette)
                self._command_input_palette = QPalette(palette)
                self._set_command_input_invalid(False)
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
