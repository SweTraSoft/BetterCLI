from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from cligui.builder import build_argv
from cligui.discovery import CommandNotFoundError
from cligui.history import CommandHistory
from cligui.model.spec import CommandSpec, OptionKind, PositionalSpec, SubcommandSpec
from cligui.ui import main_window
from cligui.ui.widgets import PathDialog, PathEditor


@pytest.fixture
def window(monkeypatch, tmp_path):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        main_window, "CommandHistory", lambda: CommandHistory(tmp_path / "history.json")
    )
    widget = main_window.MainWindow()
    monkeypatch.setattr(widget.runner, "start", Mock())
    yield widget
    widget.close()
    application.processEvents()


def test_discovery_starts_without_confirmation(window, monkeypatch):
    window.command_input.setCurrentText("git")
    window.settings.confirm_unknown_binaries = True
    preflight = Mock(return_value="/usr/bin/git")
    question = Mock(side_effect=AssertionError("Unexpected discovery confirmation"))
    start = Mock()
    monkeypatch.setattr(window.service, "preflight", preflight)
    monkeypatch.setattr(main_window.QMessageBox, "question", question)
    monkeypatch.setattr(main_window.QThread, "start", start)

    window.discover()

    preflight.assert_called_once_with(["git"])
    question.assert_not_called()
    start.assert_called_once_with()
    assert window._thread is not None
    assert not window.discover_button.isEnabled()


def test_window_title_is_bettercli(window):
    assert window.windowTitle() == "BetterCLI"


@pytest.mark.parametrize("command", ["openclaw", "/usr/local/bin/my-long-command-name"])
def test_command_input_remains_readable_with_subcommands(window, command):
    window.command_input.setCurrentText(command)
    window._refresh_subcommands(
        CommandSpec(
            argv_prefix=[command],
            subcommands=[SubcommandSpec(name="configure", help="Configure the tool")],
        )
    )
    window.resize(800, 760)
    window.show()
    QApplication.processEvents()

    editor = window.command_input.lineEdit()
    text_width = editor.fontMetrics().horizontalAdvance(command)
    assert editor.contentsRect().width() >= text_width + 30


def test_history_sidebar_shows_latest_commands_and_preserves_input(window):
    assert not window.history_empty.isHidden()
    window.command_input.setCurrentText("unfinished input")
    window.command_input.lineEdit().setCursorPosition(5)
    for command in ["curl", "git log", "curl"]:
        window.history.add(command)

    window._refresh_history()
    QApplication.processEvents()
    assert window.command_input.lineEdit().cursorPosition() == 5

    assert [window.history_list.item(index).text() for index in range(2)] == [
        "curl", "git log"
    ]
    assert window.history_list.item(1).toolTip() == "git log"
    assert [window.command_input.itemText(index) for index in range(window.command_input.count())] == list(
        main_window.COMMON_COMMANDS
    )
    assert window.command_input.currentText() == "unfinished input"
    assert window.history_empty.isHidden()


def test_unavailable_common_commands_are_disabled(window, monkeypatch):
    unavailable_command = "docker"

    def resolve_binary(command):
        if command == unavailable_command:
            raise CommandNotFoundError(f"{command} was not found")

    monkeypatch.setattr(main_window, "resolve_binary", resolve_binary)
    widget = main_window.MainWindow()

    try:
        widget.command_input.setCurrentText("unfinished input")
        model = widget.command_input.model()
        unavailable_index = main_window.COMMON_COMMANDS.index(unavailable_command)
        available_index = main_window.COMMON_COMMANDS.index("git")
        assert not model.flags(model.index(unavailable_index, 0)) & Qt.ItemFlag.ItemIsEnabled
        assert model.flags(model.index(available_index, 0)) & Qt.ItemFlag.ItemIsEnabled
        assert widget.command_input.currentText() == "unfinished input"

        widget._refresh_history()

        assert widget.command_input.currentText() == "unfinished input"
    finally:
        widget.close()


def test_command_dropdown_rows_include_descriptions(window):
    from PySide6.QtWidgets import QStyleOptionViewItem

    index = main_window.COMMON_COMMANDS.index("git")
    model = window.command_input.model()
    item = model.item(index)
    delegate = window.command_input.view().itemDelegate()

    assert item.text() == "git"
    assert item.data(main_window.COMMAND_DESCRIPTION_ROLE) == (
        "Track changes and manage version history"
    )
    assert isinstance(delegate, main_window._CommandSuggestionDelegate)
    assert window.command_input.view().minimumWidth() >= 440
    option = QStyleOptionViewItem()
    option.font = window.command_input.font()
    row_height = delegate.sizeHint(option, model.index(index, 0)).height()
    assert 30 <= row_height < 42

    window.command_input.setCurrentIndex(index)
    assert window.command_input.currentText() == "git"
    window.command_input.showPopup()
    QApplication.processEvents()
    window.command_input.hidePopup()


def test_every_common_command_suggestion_has_a_description():
    assert set(main_window.COMMON_COMMANDS) <= set(main_window.COMMAND_DESCRIPTIONS)


def test_history_sidebar_loads_saved_commands_on_reopen(window):
    window.history.add("git log")
    reopened = main_window.MainWindow()
    try:
        assert reopened.history_list.count() == 1
        assert reopened.history_list.item(0).text() == "git log"
    finally:
        reopened.close()


def test_history_sidebar_single_click_only_selects_command(window, monkeypatch):
    window.history.add("git log")
    window._refresh_history()
    discover = Mock()
    monkeypatch.setattr(window, "discover", discover)
    window.show()
    QApplication.processEvents()
    item = window.history_list.item(0)

    QTest.mouseClick(
        window.history_list.viewport(),
        Qt.LeftButton,
        pos=window.history_list.visualItemRect(item).center(),
    )

    assert window.history_list.currentItem() is item
    discover.assert_not_called()


@pytest.mark.parametrize("keyboard", [False, True])
def test_history_sidebar_opens_subcommand_without_running(window, monkeypatch, keyboard):
    window.history.add("git log")
    window._refresh_history()
    preflight = Mock(return_value="/usr/bin/git")
    monkeypatch.setattr(window.service, "preflight", preflight)
    monkeypatch.setattr(main_window.QThread, "start", Mock())
    window.show()
    QApplication.processEvents()
    item = window.history_list.item(0)

    if keyboard:
        window.history_list.setCurrentItem(item)
        window.history_list.setFocus()
        QTest.keyClick(window.history_list, Qt.Key_Return)
    else:
        position = window.history_list.visualItemRect(item).center()
        QTest.mouseClick(window.history_list.viewport(), Qt.LeftButton, pos=position)
        QTest.mouseDClick(
            window.history_list.viewport(),
            Qt.LeftButton,
            pos=position,
        )

    preflight.assert_called_once_with(["git", "log"])
    window.runner.start.assert_not_called()
    assert not window.history_list.isEnabled()
    window._on_thread_finished()
    assert window.history_list.isEnabled()


def test_discovery_updates_and_selects_history_sidebar(window):
    spec = CommandSpec(argv_prefix=["git", "log"])

    window._on_discovered(spec, SimpleNamespace(from_cache=False, note=None))

    assert window.history_list.currentItem().text() == "git log"
    assert window.history.items() == ["git log"]


def test_command_description_shows_top_level_and_subcommand_help(window):
    window.command_input.setCurrentText("git")

    assert window.command_description.text() == "Track changes and manage version history"

    parent_spec = CommandSpec(
        argv_prefix=["git"],
        subcommands=[SubcommandSpec(name="log", help="Show commit logs")],
    )
    child_spec = CommandSpec(argv_prefix=["git", "log"])
    window._on_discovered(
        child_spec,
        SimpleNamespace(from_cache=False, note=None),
        parent_result=SimpleNamespace(spec=parent_spec),
    )

    assert window.command_description.text() == "Show commit logs"


def test_clear_history_updates_sidebar_and_saved_history(window):
    window.history.add("curl")
    window._refresh_history()

    window._clear_history()

    assert window.history_list.count() == 0
    assert not window.history_empty.isHidden()
    assert CommandHistory(window.history.path).items() == []


def test_clear_inputs_clears_top_command_and_command_line(window):
    window.command_input.setCurrentText("git log")
    window.command_editor.setPlainText("git log --oneline")
    window._search_timer.start()

    window.clear_inputs_button.click()

    assert window.command_input.currentText() == ""
    assert window.command_editor.toPlainText() == ""
    assert not window._search_timer.isActive()
    assert window.subcommand_combo.isHidden()


def test_missing_command_tints_entry_without_popup(window, monkeypatch):
    warning = Mock(side_effect=AssertionError("Unexpected popup"))
    monkeypatch.setattr(
        window.service,
        "preflight",
        Mock(side_effect=CommandNotFoundError("missing was not found on your PATH")),
    )
    monkeypatch.setattr(main_window.QMessageBox, "warning", warning)
    line_edit = window.command_input.lineEdit()
    original_color = line_edit.palette().color(QPalette.ColorRole.Base)

    window.command_input.setCurrentText("missing")
    window.discover()

    tinted_color = line_edit.palette().color(QPalette.ColorRole.Base)
    assert tinted_color.red() - tinted_color.green() > (
        original_color.red() - original_color.green()
    )
    warning.assert_not_called()

    window._on_command_text_edited("missingo")
    assert line_edit.palette().color(QPalette.ColorRole.Base) == original_color


def test_command_entry_discovers_after_typing_pauses(window, monkeypatch):
    preflight = Mock(return_value="/usr/bin/git")
    start = Mock()
    monkeypatch.setattr(window.service, "preflight", preflight)
    monkeypatch.setattr(main_window.QThread, "start", start)

    command_edit = window.command_input.lineEdit()
    assert command_edit.text() == ""
    command_edit.setFocus()
    QTest.keyClicks(command_edit, "git")
    QTest.qWait(300)
    QTest.keyClicks(command_edit, " log")
    QTest.qWait(300)
    preflight.assert_not_called()

    QTest.qWait(250)
    preflight.assert_called_once_with(["git", "log"])
    start.assert_called_once_with()
    assert window.command_input.currentText() == "git log"
    assert command_edit.cursorPosition() == len("git log")

    window._on_discovered(
        CommandSpec(argv_prefix=["git", "log"]),
        SimpleNamespace(from_cache=False, note=None),
    )
    QApplication.processEvents()
    assert command_edit.cursorPosition() == len("git log")


def test_command_entry_can_continue_typing_after_discovery(window, monkeypatch):
    preflight = Mock(return_value="/usr/bin/git")
    start = Mock()
    monkeypatch.setattr(window.service, "preflight", preflight)
    monkeypatch.setattr(main_window.QThread, "start", start)

    command_edit = window.command_input.lineEdit()
    command_edit.setFocus()
    QTest.keyClicks(command_edit, "git")
    QTest.qWait(600)

    preflight.assert_called_once_with(["git"])
    start.assert_called_once_with()
    window._on_discovered(
        CommandSpec(argv_prefix=["git"]),
        SimpleNamespace(from_cache=False, note=None),
    )
    QApplication.processEvents()
    QTest.keyClicks(command_edit, " log")

    assert window.command_input.currentText() == "git log"
    window._search_timer.stop()


def test_command_entry_can_continue_typing_after_worker_discovery(window, monkeypatch):
    spec = CommandSpec(argv_prefix=["git"])
    result = SimpleNamespace(spec=spec, from_cache=False, note=None)
    monkeypatch.setattr(window.service, "preflight", Mock(return_value="/usr/bin/git"))
    monkeypatch.setattr(window.service, "discover", Mock(return_value=result))

    window.show()
    QApplication.processEvents()
    command_edit = window.command_input.lineEdit()
    command_edit.setFocus()
    QApplication.processEvents()
    QTest.keyClicks(command_edit, "git")
    QTest.qWait(600)
    for _ in range(20):
        if window._thread is None:
            break
        QTest.qWait(20)

    assert window._thread is None
    assert command_edit.text() == "git"
    assert command_edit.cursorPosition() == len("git")
    QTest.keyClicks(command_edit, " log")

    assert window.command_input.currentText() == "git log"
    window._search_timer.stop()


def test_command_entry_never_completes_or_moves_typed_text(window):
    window.show()
    QApplication.processEvents()
    command_edit = window.command_input.lineEdit()
    command_edit.setFocus()
    QApplication.processEvents()

    QTest.keyClicks(command_edit, "g")

    assert command_edit.text() == "g"
    assert command_edit.selectedText() == ""
    assert command_edit.cursorPosition() == 1

    QTest.keyClicks(command_edit, "i")

    assert command_edit.text() == "gi"
    assert command_edit.selectedText() == ""
    assert command_edit.cursorPosition() == 2
    window._search_timer.stop()


def test_focused_command_entry_is_never_overwritten(window):
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    command_edit = window.command_input.lineEdit()
    command_edit.setFocus(Qt.FocusReason.MouseFocusReason)
    QApplication.processEvents()
    QTest.keyClicks(command_edit, "git lo")
    window._search_timer.stop()
    assert command_edit.hasFocus()

    window._set_command_text("git")
    window._refresh_history()
    window._on_discovered(
        CommandSpec(argv_prefix=["git"], subcommands=[SubcommandSpec(name="log")]),
        SimpleNamespace(from_cache=False, note=None),
    )
    QApplication.processEvents()

    assert command_edit.text() == "git lo"
    assert command_edit.cursorPosition() == len("git lo")
    window._search_timer.stop()


def test_command_editor_discovers_after_typing_pauses(window, monkeypatch):
    preflight = Mock(return_value="/usr/bin/git")
    start = Mock()
    monkeypatch.setattr(window.service, "preflight", preflight)
    monkeypatch.setattr(main_window.QThread, "start", start)

    window.command_editor.setPlainText("git status --short")
    QTest.qWait(600)

    preflight.assert_called_once_with(["git"])
    start.assert_called_once_with()
    assert window.command_input.currentText() == "git"


def test_command_editor_keeps_loaded_subcommand_when_editing_arguments(window):
    window._spec = CommandSpec(argv_prefix=["git", "log"])

    window.command_editor.setPlainText("git log --oneline")

    assert not window._search_timer.isActive()


def test_discovery_keeps_text_and_cursor_typed_in_command_editor(window, monkeypatch):
    monkeypatch.setattr(window.service, "preflight", Mock(return_value="/usr/bin/git"))
    monkeypatch.setattr(main_window.QThread, "start", Mock())
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    window.command_editor.setFocus()
    QApplication.processEvents()
    QTest.keyClicks(window.command_editor, "git")
    QTest.qWait(600)

    window._on_discovered(
        CommandSpec(argv_prefix=["git"]),
        SimpleNamespace(from_cache=False, note=None),
    )
    QApplication.processEvents()

    assert window.command_editor.toPlainText() == "git"
    assert window.command_editor.textCursor().position() == len("git")
    QTest.keyClicks(window.command_editor, " status")
    assert window.command_editor.toPlainText() == "git status"
    window._search_timer.stop()

    window.form.changed.emit()
    assert window.command_editor.toPlainText() == "git"


def test_initial_child_command_discovers_parent_subcommands(window, monkeypatch):
    preflight = Mock(return_value="/usr/bin/git")
    start = Mock()
    monkeypatch.setattr(window.service, "preflight", preflight)
    monkeypatch.setattr(main_window.QThread, "start", start)
    window.command_input.setCurrentText("git clone")

    window.discover()

    preflight.assert_called_once_with(["git", "clone"])
    assert window.command_input.currentText() == "git clone"
    assert window._worker._parent_argv == ["git"]
    start.assert_called_once_with()


def test_initial_child_discovery_populates_and_selects_parent_subcommand(window):
    parent_spec = CommandSpec(
        argv_prefix=["git"],
        subcommands=[SubcommandSpec(name="clone"), SubcommandSpec(name="commit")],
    )
    child_spec = CommandSpec(argv_prefix=["git", "clone"])
    result = SimpleNamespace(from_cache=False, note=None)
    window.command_input.setCurrentText("git clone")

    window._on_discovered(
        child_spec,
        result,
        parent_result=SimpleNamespace(spec=parent_spec),
    )

    assert not window.subcommand_combo.isHidden()
    assert window.subcommand_combo.currentText() == "clone"
    assert [window.subcommand_combo.itemData(index) for index in range(1, 3)] == [
        "clone",
        "commit",
    ]
    assert window.command_input.currentText() == "git clone"


def test_subcommand_selection_keeps_only_top_command_in_entry(window, monkeypatch):
    spec = CommandSpec(
        argv_prefix=["git"],
        subcommands=[SubcommandSpec(name="clone"), SubcommandSpec(name="commit")],
    )
    window._spec = spec
    window._refresh_subcommands(spec)
    preflight = Mock(return_value="/usr/bin/git")
    start = Mock()
    monkeypatch.setattr(window.service, "preflight", preflight)
    monkeypatch.setattr(main_window.QThread, "start", start)

    window._open_subcommand(1)

    assert window.command_input.currentText() == "git"
    preflight.assert_called_once_with(["git", "clone"])
    start.assert_called_once_with()
    assert window.subcommand_combo.currentText() == "clone"


def test_subcommand_dropdown_stays_available_for_typed_child_command(window):
    window._refresh_subcommands(
        CommandSpec(
            argv_prefix=["git"],
            subcommands=[SubcommandSpec(name="clone"), SubcommandSpec(name="commit")],
        )
    )
    window.command_input.setCurrentText("git clone")

    window._refresh_subcommands(CommandSpec(argv_prefix=["git", "clone"]))

    assert not window.subcommand_combo.isHidden()
    assert [window.subcommand_combo.itemData(index) for index in range(1, 3)] == [
        "clone",
        "commit",
    ]
    assert window.subcommand_combo.currentText() == "clone"


def test_subcommand_dropdown_hides_for_unrelated_command(window):
    window._refresh_subcommands(
        CommandSpec(
            argv_prefix=["git"],
            subcommands=[SubcommandSpec(name="clone")],
        )
    )
    window.command_input.setCurrentText("curl")

    window._refresh_subcommands(CommandSpec(argv_prefix=["curl"]))

    assert window.subcommand_combo.isHidden()


def test_manual_command_runs_and_copies_quoted_arguments(window):
    window.command_editor.setPlainText('echo -- "hello world"')

    assert window.run_button.isEnabled()
    assert window.copy_button.isEnabled()
    assert window._current_argv() == ["echo", "--", "hello world"]
    window._copy_command()
    assert QApplication.clipboard().text() == "echo -- 'hello world'"
    window.run()
    window.runner.start.assert_called_once_with(["echo", "--", "hello world"], None)


def test_risky_command_runs_without_confirmation(window):
    window.command_editor.setPlainText("rm -rf ./build")

    window.run()

    window.runner.start.assert_called_once_with(["rm", "-rf", "./build"], None)


@pytest.mark.parametrize("text", ["", "   ", "echo 'unfinished"])
def test_invalid_or_empty_command_cannot_run(window, text):
    window.command_editor.setPlainText(text)

    assert not window.run_button.isEnabled()
    assert not window.copy_button.isEnabled()
    window.run()
    window.runner.start.assert_not_called()


def test_form_refreshes_command_but_execution_preserves_manual_edits(window, monkeypatch):
    window._spec = SimpleNamespace(display_name="echo")
    monkeypatch.setattr(main_window, "missing_required", lambda spec, values: [])
    monkeypatch.setattr(main_window, "build_argv", lambda spec, values: ["echo", "generated"])

    window._update_preview()
    assert window.command_editor.toPlainText() == "echo generated"
    window.command_editor.setPlainText("echo edited")
    window._on_run_finished(0)
    assert window.command_editor.toPlainText() == "echo edited"
    assert window.run_button.isEnabled()
    window.form.changed.emit()
    assert window.command_editor.toPlainText() == "echo generated"


def test_missing_form_argument_can_be_supplied_manually(window, monkeypatch):
    window._spec = SimpleNamespace(display_name="echo")
    monkeypatch.setattr(main_window, "missing_required", lambda spec, values: ["message"])

    window._update_preview()
    assert not window.run_button.isEnabled()
    window.command_editor.setPlainText('echo "manual message"')
    assert window.run_button.isEnabled()
    assert window._current_argv() == ["echo", "manual message"]


@pytest.mark.parametrize("binary", ["mv", "/bin/mv"])
@pytest.mark.parametrize("variadic", [False, True])
def test_mv_arguments_offer_files_and_folders(window, monkeypatch, binary, variadic):
    spec = CommandSpec(
        argv_prefix=[binary],
        positionals=[
            PositionalSpec(name="source", kind=OptionKind.PATH_FILE, variadic=variadic),
            PositionalSpec(name="target", kind=OptionKind.PATH_FILE),
        ],
    )
    window.form.load(spec)
    source = window.form._positional_editors["source"]
    target = window.form._positional_editors["target"]
    assert isinstance(source, PathEditor)
    assert isinstance(target, PathEditor)
    from PySide6.QtWidgets import QDialog, QPushButton

    selections = iter([["/tmp/source folder"], ["/tmp/target folder"], [], ["/tmp/file.txt"]])

    def choose(dialog):
        dialog.paths = next(selections)
        return QDialog.Accepted if dialog.paths else QDialog.Rejected

    monkeypatch.setattr(PathDialog, "exec", choose)
    for editor in (source, target):
        button = editor.widget.findChild(QPushButton)
        assert button.menu() is None
        button.click()
    assert build_argv(spec, window.form.values()) == [
        binary, "/tmp/source folder", "/tmp/target folder"
    ]
    source._browse()
    assert source.value() == (["/tmp/source folder"] if variadic else "/tmp/source folder")

    source.widget.findChild(QPushButton).click()
    assert source.value() == (["/tmp/file.txt"] if variadic else "/tmp/file.txt")


@pytest.mark.parametrize("multiple", [False, True])
def test_generic_path_editor_accepts_typed_and_browsed_directories(
    window, tmp_path, monkeypatch, multiple
):
    from PySide6.QtWidgets import QDialog

    folder = tmp_path / "search folder"
    folder.mkdir()
    editor = PathEditor(directory=False, multiple=multiple)
    editor.line.setText(str(folder))
    assert editor.value() == ([str(folder)] if multiple else str(folder))
    assert editor.line.placeholderText() == "file or directory path"

    def choose(dialog):
        dialog.paths = [str(folder)]
        return QDialog.Accepted

    monkeypatch.setattr(PathDialog, "exec", choose)
    editor._browse()
    assert editor.value() == ([str(folder)] if multiple else str(folder))


@pytest.mark.parametrize("directory", [False, True])
def test_generic_picker_accepts_existing_file_or_folder(window, tmp_path, directory):
    from PySide6.QtWidgets import QDialog

    path = tmp_path / "selected path"
    if directory:
        path.mkdir()
    else:
        path.touch()
    dialog = PathDialog(window, multiple=False)
    dialog.setDirectory(str(tmp_path))
    dialog.selectFile(str(path))
    dialog.accept()

    assert dialog.result() == QDialog.Accepted
    assert dialog.paths == [str(path)]


@pytest.mark.parametrize("mixed", [False, True])
def test_generic_picker_choose_button_accepts_folder_and_mixed_selection(window, tmp_path, mixed):
    from PySide6.QtCore import QItemSelectionModel
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTreeView

    folder = tmp_path / "folder"
    folder.mkdir()
    file = tmp_path / "file.txt"
    file.touch()
    dialog = PathDialog(window, multiple=mixed)
    dialog.setDirectory(str(tmp_path))
    dialog.show()
    QApplication.processEvents()
    tree = dialog.findChild(QTreeView, "treeView")
    selection = tree.selectionModel()
    selection.select(
        tree.model().index(str(folder)),
        QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows,
    )
    if mixed:
        selection.select(
            tree.model().index(str(file)),
            QItemSelectionModel.Select | QItemSelectionModel.Rows,
        )
    QApplication.processEvents()
    buttons = dialog.findChild(QDialogButtonBox)
    choose = next(
        button for button in buttons.buttons()
        if buttons.buttonRole(button) == QDialogButtonBox.AcceptRole
    )
    assert choose.isEnabled()
    choose.click()
    assert dialog.result() == QDialog.Accepted
    assert set(dialog.paths) == ({str(folder), str(file)} if mixed else {str(folder)})