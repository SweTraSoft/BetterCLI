"""Maps each :class:`OptionKind` to an editor widget.

Every editor exposes the same tiny interface - ``value()``, ``set_value()`` and
a ``changed`` signal - so the form can treat them uniformly.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from cligui.model.spec import OptionKind, OptionSpec, PositionalSpec


class Editor(QObject):
    """Common interface over a concrete Qt widget."""

    changed = Signal()

    def __init__(self, widget: QWidget) -> None:
        super().__init__()
        self.widget = widget

    def value(self) -> Any:  # pragma: no cover - overridden
        raise NotImplementedError

    def set_value(self, value: Any) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def clear(self) -> None:
        self.set_value(None)


class FlagEditor(Editor):
    def __init__(self, negatable: bool) -> None:
        box = QCheckBox()
        super().__init__(box)
        self._negatable = negatable
        if negatable:
            box.setTristate(True)
            box.setCheckState(Qt.PartiallyChecked)
            box.setToolTip("Unset / on / explicitly off")
        box.checkStateChanged.connect(lambda _: self.changed.emit())

    def value(self) -> Any:
        state = self.widget.checkState()
        if self._negatable and state is Qt.PartiallyChecked:
            return None
        if state is Qt.Checked:
            return True
        return False if self._negatable else None

    def set_value(self, value: Any) -> None:
        if value is None:
            self.widget.setCheckState(
                Qt.PartiallyChecked if self._negatable else Qt.Unchecked
            )
        else:
            self.widget.setCheckState(Qt.Checked if value else Qt.Unchecked)


class CountEditor(Editor):
    def __init__(self) -> None:
        spin = QSpinBox()
        spin.setRange(0, 20)
        spin.setSpecialValueText("off")
        super().__init__(spin)
        spin.valueChanged.connect(lambda _: self.changed.emit())

    def value(self) -> Any:
        return self.widget.value() or None

    def set_value(self, value: Any) -> None:
        self.widget.setValue(int(value or 0))


class NumberEditor(Editor):
    def __init__(self, decimal: bool) -> None:
        spin = QDoubleSpinBox() if decimal else QSpinBox()
        spin.setRange(-1_000_000_000, 1_000_000_000)
        if decimal:
            spin.setDecimals(4)
        # A dedicated "unset" sentinel keeps zero a usable value.
        self._unset = spin.minimum()
        spin.setSpecialValueText("unset")
        spin.setValue(self._unset)
        super().__init__(spin)
        spin.valueChanged.connect(lambda _: self.changed.emit())

    def value(self) -> Any:
        current = self.widget.value()
        if current == self._unset:
            return None
        return str(int(current)) if isinstance(self.widget, QSpinBox) else str(current)

    def set_value(self, value: Any) -> None:
        if value in (None, ""):
            self.widget.setValue(self._unset)
            return
        try:
            self.widget.setValue(float(value))
        except (TypeError, ValueError):
            self.widget.setValue(self._unset)


class ChoiceEditor(Editor):
    def __init__(self, choices: list[str]) -> None:
        combo = QComboBox()
        combo.addItem("unset", userData=None)
        for choice in choices:
            combo.addItem(choice, userData=choice)
        super().__init__(combo)
        combo.currentIndexChanged.connect(lambda _: self.changed.emit())

    def value(self) -> Any:
        return self.widget.currentData()

    def set_value(self, value: Any) -> None:
        index = self.widget.findData(value)
        self.widget.setCurrentIndex(max(index, 0))


class TextEditor(Editor):
    def __init__(self, placeholder: str = "") -> None:
        line = QLineEdit()
        line.setPlaceholderText(placeholder)
        super().__init__(line)
        line.textChanged.connect(lambda _: self.changed.emit())

    def value(self) -> Any:
        return self.widget.text().strip() or None

    def set_value(self, value: Any) -> None:
        self.widget.setText("" if value is None else str(value))


class ListEditor(Editor):
    """Comma-separated entry for options that accept several values."""

    def __init__(self) -> None:
        line = QLineEdit()
        line.setPlaceholderText("comma-separated values")
        super().__init__(line)
        line.textChanged.connect(lambda _: self.changed.emit())

    def value(self) -> Any:
        items = [part.strip() for part in self.widget.text().split(",")]
        return [item for item in items if item] or None

    def set_value(self, value: Any) -> None:
        if isinstance(value, (list, tuple)):
            self.widget.setText(", ".join(str(v) for v in value))
        else:
            self.widget.setText("" if value is None else str(value))


class PathEditor(Editor):
    def __init__(self, directory: bool, multiple: bool = False) -> None:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.line = QLineEdit()
        self.line.setPlaceholderText("directory path" if directory else "file path")
        browse = QPushButton("Browse…")
        browse.setAutoDefault(False)
        layout.addWidget(self.line, 1)
        layout.addWidget(browse)

        super().__init__(container)
        self._directory = directory
        self._multiple = multiple
        self.line.textChanged.connect(lambda _: self.changed.emit())
        browse.clicked.connect(self._browse)

    def _browse(self) -> None:
        if self._directory:
            chosen = QFileDialog.getExistingDirectory(self.widget, "Choose a directory")
            paths = [chosen] if chosen else []
        elif self._multiple:
            paths, _ = QFileDialog.getOpenFileNames(self.widget, "Choose files")
        else:
            chosen, _ = QFileDialog.getOpenFileName(self.widget, "Choose a file")
            paths = [chosen] if chosen else []
        if paths:
            self.line.setText(", ".join(paths) if self._multiple else paths[0])

    def value(self) -> Any:
        text = self.line.text().strip()
        if not text:
            return None
        if self._multiple:
            return [p.strip() for p in text.split(",") if p.strip()]
        return text

    def set_value(self, value: Any) -> None:
        if isinstance(value, (list, tuple)):
            self.line.setText(", ".join(str(v) for v in value))
        else:
            self.line.setText("" if value is None else str(value))


def editor_for_kind(
    kind: OptionKind, choices: list[str], negatable: bool = False, variadic: bool = False
) -> Editor:
    if kind is OptionKind.FLAG:
        return FlagEditor(negatable)
    if kind is OptionKind.COUNT:
        return CountEditor()
    if kind is OptionKind.CHOICE and choices:
        return ChoiceEditor(choices)
    if kind is OptionKind.INT:
        return NumberEditor(decimal=False)
    if kind is OptionKind.FLOAT:
        return NumberEditor(decimal=True)
    if kind is OptionKind.PATH_DIR:
        return PathEditor(directory=True, multiple=variadic)
    if kind is OptionKind.PATH_FILE:
        return PathEditor(directory=False, multiple=variadic)
    if kind is OptionKind.MULTI:
        return ListEditor()
    return ListEditor() if variadic else TextEditor()


def editor_for_option(option: OptionSpec) -> Editor:
    editor = editor_for_kind(
        option.kind, option.choices, option.negatable, option.repeatable
    )
    if option.default is not None and option.kind not in {
        OptionKind.FLAG,
        OptionKind.COUNT,
    }:
        editor.widget.setToolTip(f"Default: {option.default}")
    return editor


def editor_for_positional(positional: PositionalSpec) -> Editor:
    return editor_for_kind(positional.kind, [], False, positional.variadic)
