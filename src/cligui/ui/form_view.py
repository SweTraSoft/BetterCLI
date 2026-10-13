"""Builds a scrollable form for a :class:`CommandSpec` and reads values back."""

from __future__ import annotations

import shlex
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cligui.builder import FormValues
from cligui.model.spec import CommandSpec
from cligui.ui.widgets import Editor, editor_for_option, editor_for_positional

#: Man-page descriptions run to paragraphs; show a lead-in and keep the rest on hover.
DESCRIPTION_LIMIT = 220


def _shorten(text: str) -> str:
    if len(text) <= DESCRIPTION_LIMIT:
        return text
    cut = text[:DESCRIPTION_LIMIT].rsplit(" ", 1)[0]
    return f"{cut} …"


class _Row:
    __slots__ = ("label", "editor", "field", "group", "haystack")

    def __init__(
        self,
        label: QWidget,
        editor: Editor,
        field: QWidget,
        group: QWidget | None,
        haystack: str,
    ) -> None:
        self.label = label
        self.editor = editor
        self.field = field
        self.group = group
        self.haystack = haystack


class FormView(QScrollArea):
    """Renders one command's options and emits ``changed`` on every edit."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)

        self._spec: CommandSpec | None = None
        self._option_editors: dict[str, Editor] = {}
        self._positional_editors: dict[str, Editor] = {}
        self._rows: list[_Row] = []
        self._groups: list[QGroupBox] = []
        self._extra_group: QWidget | None = None
        self._extra = QLineEdit()

        self._body = QWidget()
        self._layout = QVBoxLayout(self._body)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(12)
        self.setWidget(self._body)
        self._show_placeholder("Enter a command above and press Discover.")

    @property
    def spec(self) -> CommandSpec | None:
        return self._spec

    def _reset(self) -> None:
        self._option_editors.clear()
        self._positional_editors.clear()
        self._rows.clear()
        self._groups.clear()
        self._extra_group = None
        while (item := self._layout.takeAt(0)) is not None:
            if widget := item.widget():
                widget.deleteLater()

    def _show_placeholder(self, message: str) -> None:
        self._reset()
        self._spec = None
        label = QLabel(message)
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("color: palette(mid);")
        self._layout.addWidget(label)
        self._layout.addStretch(1)

    def _add_group(self, title: str) -> QFormLayout:
        group = QGroupBox(title)
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self._layout.addWidget(group)
        self._groups.append(group)
        return form

    def _add_row(self, form: QFormLayout, title: str, help_text: str, editor: Editor):
        label = QLabel(title)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setStyleSheet("font-family: Menlo, monospace;")

        field = QWidget()
        field_layout = QVBoxLayout(field)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(2)
        field_layout.addWidget(editor.widget)

        if help_text:
            label.setToolTip(help_text)
            editor.widget.setToolTip(help_text)
            description = QLabel(_shorten(help_text))
            description.setWordWrap(True)
            description.setTextInteractionFlags(Qt.TextSelectableByMouse)
            description.setStyleSheet("color: palette(mid); font-size: 11px;")
            if len(help_text) > DESCRIPTION_LIMIT:
                description.setToolTip(help_text)
            field_layout.addWidget(description)

        editor.changed.connect(self.changed)
        form.addRow(label, field)
        self._rows.append(
            _Row(label, editor, field, form.parentWidget(), f"{title} {help_text}".lower())
        )

    def load(self, spec: CommandSpec) -> None:
        self._reset()
        self._spec = spec

        if spec.positionals:
            form = self._add_group("Arguments")
            for positional in spec.positionals:
                editor = editor_for_positional(
                    positional, allow_directory=Path(spec.argv_prefix[0]).name == "mv"
                )
                self._positional_editors[positional.name] = editor
                suffix = "" if positional.required else " (optional)"
                self._add_row(form, positional.name + suffix, positional.help, editor)

        required = [opt for opt in spec.options if opt.required]
        optional = [opt for opt in spec.options if not opt.required]

        for title, group in (("Required options", required), ("Options", optional)):
            if not group:
                continue
            form = self._add_group(title)
            for option in group:
                editor = editor_for_option(option)
                self._option_editors[option.name] = editor
                self._add_row(form, option.display, option.help, editor)

        extra_form = self._add_group("Additional arguments")
        self._extra_group = extra_form.parentWidget()
        self._extra = QLineEdit()
        self._extra.setPlaceholderText("Anything not listed above, e.g. --flag value")
        self._extra.textChanged.connect(self.changed)
        extra_form.addRow(QLabel("extra"), self._extra)

        if not spec.options and not spec.positionals:
            hint = QLabel(
                "No options were discovered for this command. You can still pass "
                "arguments using the field above."
            )
            hint.setWordWrap(True)
            hint.setStyleSheet("color: palette(mid);")
            self._layout.addWidget(hint)

        self._layout.addStretch(1)
        self.changed.emit()

    def apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        matched: set[int] = set()
        for row in self._rows:
            visible = needle in row.haystack if needle else True
            row.label.setVisible(visible)
            row.field.setVisible(visible)
            if visible and row.group is not None:
                matched.add(id(row.group))
        for group in self._groups:
            # The extras group holds no rows, so it must never be filtered away.
            keep = not needle or id(group) in matched or group is self._extra_group
            group.setVisible(keep)

    def values(self) -> FormValues:
        options = {
            name: editor.value()
            for name, editor in self._option_editors.items()
            if editor.value() is not None
        }
        positionals = {
            name: editor.value()
            for name, editor in self._positional_editors.items()
            if editor.value() is not None
        }
        try:
            extra = shlex.split(self._extra.text())
        except ValueError:
            # Unbalanced quotes while still typing; fall back to whitespace split.
            extra = self._extra.text().split()
        return FormValues(options=options, positionals=positionals, extra=extra)

    def reset_values(self) -> None:
        for editor in (*self._option_editors.values(), *self._positional_editors.values()):
            editor.clear()
        self._extra.clear()
        self.changed.emit()

    def clear(self) -> None:
        self._show_placeholder("Enter a command above and press Discover.")
