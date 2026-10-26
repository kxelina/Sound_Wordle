"""Repair-device faceplates using the existing validated knob/numeric widgets."""

from ..game.music_repair import GROUP_NAMES
from .parameter_editor import ParameterEditor
from .hover_help import REPAIR_LABELS, help_text, set_help


class MusicRepairEditor(ParameterEditor):
    def __init__(self, *args, **kwargs):
        self._stage_group = None
        super().__init__(*args, **kwargs)

    def set_stage(self, group):
        self._stage_group = group
        self.set_locked(False)

    def set_locked(self, locked):
        super().set_locked(locked)
        from ..game.parameters import PARAMETERS
        for key, control in self.controls.items():
            if PARAMETERS[key].group != self._stage_group:
                control.setEnabled(False)
                if key in self.knobs:
                    self.knobs[key].setEnabled(False)

    def translate(self, language):
        super().translate(language)
        for key, control in self.controls.items():
            label = REPAIR_LABELS[key][language == "zh-Hant"]
            self.labels[key].setText(label)
            control.setAccessibleName(label)
            gesture = (" 上下拖曳旋鈕，或輸入精確數值。" if language == "zh-Hant" else
                       " Drag the knob up/down or type an exact value.") if key in self.knobs else ""
            for widget in (control, self.labels[key], self.knobs.get(key)):
                if widget is not None:
                    set_help(widget, f"repair_{key}", language, suffix=gesture)
            if key == "filter_mode" and hasattr(control, "buttons"):
                for button in control.buttons:
                    set_help(button, "repair_filter_mode", language)
        if self.tabs:
            for index, group in enumerate(self._tab_groups):
                self.tabs.setTabText(index, GROUP_NAMES[group][language == "zh-Hant"])
                self.tabs.setTabToolTip(index, help_text("repair_tab", language))
