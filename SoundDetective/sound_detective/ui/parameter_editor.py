"""Registry-driven controls; only unlocked parameters are editable."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QDoubleSpinBox, QAbstractSpinBox,
    QSpinBox, QComboBox, QCheckBox, QScrollArea, QTabWidget, QGridLayout)

from ..game.parameters import PARAMETERS, GROUPS
from .hardware import HardwareFader, InlineChoices, PowerToggle, RackFace, RotaryKnob
from .hover_help import set_parameter_help


class ParameterEditor(QWidget):
    changed = Signal()

    def __init__(self, case, parent=None):
        super().__init__(parent)
        self.case = case
        self.controls, self.labels, self.sliders = {}, {}, {}
        self.knobs = {}
        self._rows = {}
        self._locked = False
        self._settings = case.initial
        self._group_enabled = {group: getattr(case.initial.effects, group).enabled for group in ("filter", "delay", "reverb")}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        groups = list(dict.fromkeys(PARAMETERS[key].group for key in case.editable_parameters))
        self.tabs = QTabWidget() if len(groups) > 1 and len(case.editable_parameters) > 4 else None
        self._tab_groups = groups
        if self.tabs is not None:
            layout.addWidget(self.tabs)
        batches = [(group, [key for key in case.editable_parameters if PARAMETERS[key].group == group]) for group in groups] if self.tabs else [(None, case.editable_parameters)]
        for group, keys in batches:
            body = QWidget()
            form = QFormLayout(body)
            form.setContentsMargins(6, 6, 6, 6)
            for key in keys:
                spec = PARAMETERS[key]
                label = QLabel()
                self.labels[key] = label
                if spec.kind == "bool":
                    control = QCheckBox()
                    signal = control.toggled
                elif spec.kind == "choice":
                    control = QComboBox()
                    for choice in spec.choices:
                        control.addItem(choice, choice)
                    signal = control.currentIndexChanged
                else:
                    control = QSpinBox() if spec.kind == "int" else QDoubleSpinBox()
                    control.setRange(spec.low, spec.high)
                    control.setSingleStep(spec.step)
                    if isinstance(control, QDoubleSpinBox):
                        control.setDecimals(spec.decimals)
                    signal = control.valueChanged
                control.setObjectName(key)
                self.controls[key] = control
                if spec.group == "harmonics":
                    row = QWidget()
                    row_layout = QHBoxLayout(row)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    slider = HardwareFader(Qt.Orientation.Horizontal)
                    slider.setRange(0, 100)
                    slider.setObjectName(f"{key}_slider")
                    slider.valueChanged.connect(lambda value, spin=control: spin.setValue(value / 100))
                    self.sliders[key] = slider
                    row_layout.addWidget(slider, 1)
                    row_layout.addWidget(control)
                    form.addRow(label, row)
                    self._rows[key] = (label, row)
                else:
                    form.addRow(label, control)
                    self._rows[key] = (label, control)
                signal.connect(lambda *_, name=key: self._changed(name))
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(body)
            scroll.setMinimumHeight(130)
            if self.tabs:
                self.tabs.addTab(scroll, group)
            else:
                layout.addWidget(scroll)
        self.set_settings(case.initial)
        self.translate("en")

    def show_groups(self, groups):
        """Choose a machine's visible controls without changing any values."""
        groups = set(groups)
        for key, widgets in self._rows.items():
            for widget in widgets:
                widget.setVisible(PARAMETERS[key].group in groups)
        if self.tabs:
            visible = []
            for index, group in enumerate(self._tab_groups):
                self.tabs.setTabVisible(index, group in groups)
                if group in groups:
                    visible.append(index)
            if visible and self.tabs.currentIndex() not in visible:
                self.tabs.setCurrentIndex(visible[0])
        return any(PARAMETERS[key].group in groups for key in self.controls)

    def use_hardware_controls(self):
        """Rehouse the same numeric fields in fader/knob faceplates.

        The spin boxes remain authoritative, including validation, precision and
        game locking. No second patch or audio-generation path is introduced.
        """
        if getattr(self, "_hardware", False):
            return
        self._hardware = self._harmonic_bank = True
        batches = [(group, self.tabs.widget(index)) for index, group in enumerate(self._tab_groups)] if self.tabs else [(None, self.layout().itemAt(0).widget())]
        for group, scroll in batches:
            keys = [key for key in self.controls if group is None or PARAMETERS[key].group == group]
            old_body = scroll.takeWidget()
            body = RackFace()
            grid = QGridLayout(body)
            grid.setContentsMargins(22, 20, 22, 20)
            grid.setSpacing(12)
            number = header = 0
            for key in keys:
                spec = PARAMETERS[key]
                control, label = self.controls[key], self.labels[key]
                column = QWidget()
                layout = QVBoxLayout(column)
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(3)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setWordWrap(True)
                label.setBuddy(control)
                layout.addWidget(label)
                if key in self.sliders:
                    slider = self.sliders[key]
                    slider.setOrientation(Qt.Orientation.Vertical)
                    slider.setMinimumHeight(180)
                    slider.setFixedWidth(44)
                    control.setFixedWidth(58)
                    control.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                    layout.addWidget(slider, 1, Qt.AlignmentFlag.AlignHCenter)
                elif spec.kind in ("float", "int"):
                    knob = RotaryKnob()
                    factor = 10 ** spec.decimals
                    knob.setRange(0, round((spec.high - spec.low) * factor))
                    knob.setSingleStep(max(1, round(spec.step * factor)))
                    knob.setPageStep(max(1, round((spec.high-spec.low)*factor / 10)))
                    knob.setValue(round((control.value()-spec.low)*factor))
                    knob.setObjectName(f"{key}_knob")
                    knob.valueChanged.connect(lambda value, spin=control, param=spec, scale=factor:
                        spin.setValue(round(param.low + value / scale, param.decimals)))
                    self.knobs[key] = knob
                    control.setFixedWidth(100)
                    control.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                    layout.addWidget(knob, 0, Qt.AlignmentFlag.AlignHCenter)
                elif spec.kind == "bool":
                    replacement = PowerToggle()
                    replacement.setChecked(control.isChecked())
                    replacement.setObjectName(key)
                    replacement.toggled.connect(lambda _, name=key: self._changed(name))
                    control.hide()
                    control.deleteLater()
                    control = self.controls[key] = replacement
                elif spec.kind == "choice":
                    # Filter type has the same popup problem as scene settings.
                    replacement = InlineChoices()
                    for choice in spec.choices:
                        replacement.addItem(choice, choice)
                    replacement.setCurrentIndex(control.currentIndex())
                    replacement.setObjectName(key)
                    replacement.currentIndexChanged.connect(lambda _, name=key: self._changed(name))
                    control.hide()
                    control.deleteLater()
                    control = self.controls[key] = replacement
                layout.addWidget(control, 0, Qt.AlignmentFlag.AlignHCenter)
                label.setBuddy(control)
                self._rows[key] = (label, column)
                if spec.kind in ("bool", "choice"):
                    grid.addWidget(column, header, 0, 1, 3)
                    header += 1
                else:
                    count = 8 if group == "harmonics" or (self.sliders and not self.tabs) else 4 if group == "envelope" else 3
                    # Boolean/choice controls occupy their own row above knobs.
                    offset = int(any(PARAMETERS[item].kind == "bool" for item in keys)) + int(any(PARAMETERS[item].kind == "choice" for item in keys))
                    grid.addWidget(column, offset + number // count, number % count)
                    number += 1
                if spec.kind in ("float", "int"):
                    control.setStyleSheet("""
                        QAbstractSpinBox { background: #14231c; color: #efdb9e;
                            border: 1px solid #8b7853; border-radius: 2px; padding: 5px; }
                        QAbstractSpinBox:disabled { color: #8e8b75; background: #283129; }
                        QLineEdit { background: transparent; border: 0; padding: 0; }
                    """)
            grid.setRowStretch(grid.rowCount(), 1)
            scroll.setWidget(body)
            old_body.deleteLater()
        self.set_locked(self._locked)
        self.translate("en")

    use_harmonic_bank = use_hardware_controls

    def _changed(self, key):
        if key in self.sliders:
            slider = self.sliders[key]
            slider.blockSignals(True)
            slider.setValue(round(self.controls[key].value() * 100))
            slider.blockSignals(False)
        if key in self.knobs:
            self._sync_knob(key)
        self.set_locked(self._locked)
        self.changed.emit()

    def values(self):
        result = {}
        for key, control in self.controls.items():
            kind = PARAMETERS[key].kind
            result[key] = control.isChecked() if kind == "bool" else control.currentData() if kind == "choice" else control.value()
        return result

    def set_settings(self, settings):
        self._settings = settings
        self._group_enabled = {group: getattr(settings.effects, group).enabled for group in ("filter", "delay", "reverb")}
        for key, control in self.controls.items():
            spec = PARAMETERS[key]
            value = spec.get(settings)
            control.blockSignals(True)
            if spec.kind == "bool":
                control.setChecked(value)
            elif spec.kind == "choice":
                control.setCurrentIndex(control.findData(value))
            else:
                control.setValue(int(value) if spec.kind == "int" else value)
            control.blockSignals(False)
            if key in self.sliders:
                slider = self.sliders[key]
                slider.blockSignals(True)
                slider.setValue(round(value * 100))
                slider.blockSignals(False)
            if key in self.knobs:
                self._sync_knob(key)
        self.set_locked(self._locked)

    def _sync_knob(self, key):
        spec, knob = PARAMETERS[key], self.knobs[key]
        knob.blockSignals(True)
        knob.setValue(round((self.controls[key].value() - spec.low) * 10 ** spec.decimals))
        knob.blockSignals(False)

    def set_locked(self, locked):
        self._locked = locked
        for key, control in self.controls.items():
            group = PARAMETERS[key].group
            enabled_key = f"{group}_enabled"
            active = self.controls[enabled_key].isChecked() if enabled_key in self.controls else self._group_enabled.get(group, True)
            enabled = not locked and (active or key == enabled_key)
            control.setEnabled(enabled)
            if key in self.sliders:
                self.sliders[key].setEnabled(enabled)
            if key in self.knobs:
                self.knobs[key].setEnabled(enabled)

    def translate(self, language):
        for key, label in self.labels.items():
            spec = PARAMETERS[key]
            text = spec.label(language)
            if spec.group == "harmonics" and getattr(self, "_harmonic_bank", False):
                text = key.upper()
            if key == "cutoff_hz" and "filter_mode" in self.controls:
                text = "Cutoff (Hz)" if language == "en" else "截止頻率（Hz）"
            label.setText(text)
            self.controls[key].setAccessibleName(text)
            if isinstance(self.controls[key], PowerToggle):
                self.controls[key].language = language
                self.controls[key].update()
            if key in self.sliders:
                self.sliders[key].setAccessibleName(spec.label(language))
            if key in self.knobs:
                knob = self.knobs[key]
                knob.setAccessibleName(text)
        if "filter_mode" in self.controls:
            control = self.controls["filter_mode"]
            for index, text in enumerate(("Low-pass", "High-pass") if language == "en" else ("低通", "高通")):
                if isinstance(control, InlineChoices):
                    control.buttons[index].setText(text)
                else:
                    control.setItemText(index, text)
        if self.tabs:
            for index, group in enumerate(self._tab_groups):
                self.tabs.setTabText(index, GROUPS[group][language == "zh-Hant"])
        set_parameter_help(self, language)
