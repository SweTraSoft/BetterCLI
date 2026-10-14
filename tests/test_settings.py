import json

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from cligui import settings as settings_module
from cligui.settings import Settings
from cligui.ui import dialogs, theme
from cligui.ui.dialogs import SettingsDialog
from cligui.ui.theme import apply_theme


def test_appearance_defaults_to_system_and_round_trips(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module, "data_dir", lambda: tmp_path)

    settings = Settings.load()
    assert settings.appearance == "system"

    settings.appearance = "dark"
    settings.save()

    assert Settings.load().appearance == "dark"


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ({"dark_mode": True}, "dark"),
        ({"dark_mode": False}, "system"),
        ({"dark_mode": True, "appearance": "light"}, "light"),
        ({"appearance": "purple"}, "system"),
    ],
)
def test_appearance_migrates_and_validates(monkeypatch, tmp_path, stored, expected):
    monkeypatch.setattr(settings_module, "data_dir", lambda: tmp_path)
    (tmp_path / "settings.json").write_text(json.dumps(stored), encoding="utf-8")

    assert Settings.load().appearance == expected


def test_settings_dialog_offers_and_saves_appearance(monkeypatch, tmp_path):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr(settings_module, "data_dir", lambda: tmp_path)
    settings = Settings()

    dialog = SettingsDialog(settings)
    combo = dialog._appearance
    assert [combo.itemText(i) for i in range(combo.count())] == [
        "Light",
        "Dark",
        "Follow system",
    ]
    assert combo.currentData() == "system"

    combo.setCurrentIndex(combo.findData("dark"))
    dialog.accept()

    assert settings.appearance == "dark"
    assert Settings.load().appearance == "dark"
    dialog.close()
    application.processEvents()


def test_settings_dialog_shows_appearance_then_version():
    application = QApplication.instance() or QApplication([])
    dialog = SettingsDialog(Settings())

    form = dialog.layout().itemAt(0).layout()
    labels = [
        form.itemAt(row, dialogs.QFormLayout.LabelRole).widget().text()
        for row in range(form.rowCount())
    ]
    assert labels == ["Appearance", "Version"]
    version = form.itemAt(1, dialogs.QFormLayout.FieldRole).widget()
    assert version.text() == "1.00"
    assert not dialog.findChildren(dialogs.QLineEdit)
    dialog.close()
    application.processEvents()


def test_apply_theme_updates_application_palette():
    application = QApplication.instance() or QApplication([])
    original_palette = QPalette(application.palette())
    original_icon = application.windowIcon()
    try:
        apply_theme(application, "dark")
        dark_palette = application.palette()
        assert dark_palette.color(QPalette.ColorRole.Window).name() == "#171b24"
        assert dark_palette.color(QPalette.ColorRole.Text).name() == "#e6eaf2"
        dark_icon = application.windowIcon()
        assert not dark_icon.isNull()

        apply_theme(application, "light")
        assert application.palette() == application.style().standardPalette()
        light_icon = application.windowIcon()
        assert not light_icon.isNull()
        assert dark_icon.cacheKey() != light_icon.cacheKey()
    finally:
        application.setPalette(original_palette)
        application.setWindowIcon(original_icon)


@pytest.mark.parametrize("system_dark", [True, False])
def test_apply_theme_follows_system(monkeypatch, system_dark):
    application = QApplication.instance() or QApplication([])
    original_palette = QPalette(application.palette())
    monkeypatch.setattr(theme, "system_prefers_dark", lambda _app: system_dark)
    try:
        apply_theme(application, "system")
        window = application.palette().color(QPalette.ColorRole.Window).name()
        assert (window == "#171b24") is system_dark
    finally:
        apply_theme(application, "light")
        application.setPalette(original_palette)


def test_system_appearance_reacts_to_color_scheme_changes():
    application = QApplication.instance() or QApplication([])
    original_palette = QPalette(application.palette())
    style_hints = application.styleHints()
    try:
        apply_theme(application, "system")
        style_hints.colorSchemeChanged.emit(Qt.ColorScheme.Dark)
        assert application.palette().color(QPalette.ColorRole.Window).name() == "#171b24"
        style_hints.colorSchemeChanged.emit(Qt.ColorScheme.Light)
        assert application.palette() == application.style().standardPalette()

        apply_theme(application, "light")
        style_hints.colorSchemeChanged.emit(Qt.ColorScheme.Dark)
        assert application.palette() == application.style().standardPalette()
    finally:
        apply_theme(application, "light")
        application.setPalette(original_palette)
