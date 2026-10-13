from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication

from cligui import settings as settings_module
from cligui.settings import Settings
from cligui.ui import dialogs
from cligui.ui.dialogs import SettingsDialog
from cligui.ui.theme import apply_theme


def test_dark_mode_setting_round_trips(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_module, "data_dir", lambda: tmp_path)

    settings = Settings.load()
    assert settings.dark_mode is False

    settings.dark_mode = True
    settings.save()

    assert Settings.load().dark_mode is True


def test_settings_dialog_saves_dark_mode(monkeypatch, tmp_path):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr(settings_module, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(dialogs, "get_api_key", lambda: None)
    settings = Settings()

    dialog = SettingsDialog(settings)
    assert not dialog._dark_mode.isChecked()

    dialog._dark_mode.setChecked(True)
    dialog.accept()

    assert settings.dark_mode is True
    assert Settings.load().dark_mode is True
    dialog.close()
    application.processEvents()


def test_apply_theme_updates_application_palette():
    application = QApplication.instance() or QApplication([])
    original_palette = QPalette(application.palette())
    original_icon = application.windowIcon()
    try:
        apply_theme(application, True)
        dark_palette = application.palette()
        assert dark_palette.color(QPalette.ColorRole.Window).name() == "#171b24"
        assert dark_palette.color(QPalette.ColorRole.Text).name() == "#e6eaf2"
        dark_icon = application.windowIcon()
        assert not dark_icon.isNull()

        apply_theme(application, False)
        assert application.palette() == application.style().standardPalette()
        light_icon = application.windowIcon()
        assert not light_icon.isNull()
        assert dark_icon.cacheKey() != light_icon.cacheKey()
    finally:
        application.setPalette(original_palette)
        application.setWindowIcon(original_icon)