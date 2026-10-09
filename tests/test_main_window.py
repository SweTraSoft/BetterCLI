from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from cligui.builder import build_argv
from cligui.discovery import CommandNotFoundError
from cligui.model.spec import CommandSpec, OptionKind, PositionalSpec, SubcommandSpec
from cligui.ui import main_window
from cligui.ui.widgets import PathDialog, PathEditor


@pytest.fixture
def window(monkeypatch):
    application = QApplication.instance() or QApplication([])
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
    command_edit.setFocus()
    QTest.keyClicks(command_edit, "git")
    QTest.qWait(300)
    QTest.keyClicks(command_edit, " log")
    QTest.qWait(300)
    preflight.assert_not_called()

    QTest.qWait(250)
    preflight.assert_called_once_with(["git", "log"])
    start.assert_called_once_with()
    assert window.command_input.currentText() == "git"


def test_initial_child_command_discovers_parent_subcommands(window, monkeypatch):
    preflight = Mock(return_value="/usr/bin/git")
    start = Mock()
    monkeypatch.setattr(window.service, "preflight", preflight)
    monkeypatch.setattr(main_window.QThread, "start", start)
    window.command_input.setCurrentText("git clone")

    window.discover()

    preflight.assert_called_once_with(["git", "clone"])
    assert window.command_input.currentText() == "git"
    assert window._worker._parent_argv == ["git"]
    start.assert_called_once_with()


def test_initial_child_discovery_populates_and_selects_parent_subcommand(window):
    parent_spec = CommandSpec(
        argv_prefix=["git"],
        subcommands=[SubcommandSpec(name="clone"), SubcommandSpec(name="commit")],
    )
    child_spec = CommandSpec(argv_prefix=["git", "clone"])
    result = SimpleNamespace(from_cache=False, note=None)
    window.command_input.setCurrentText("git")

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