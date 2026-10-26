"""One control registry shared by case validation, sessions and Qt editors."""

from dataclasses import dataclass
from typing import Any

from ..audio.models import SoundSettings, bounded


@dataclass(frozen=True)
class Parameter:
    key: str
    path: tuple
    group: str
    labels: tuple[str, str]
    kind: str = "float"
    low: float = 0.
    high: float = 1.
    step: float = .01
    decimals: int = 2
    choices: tuple = ()

    def label(self, language):
        return self.labels[language == "zh-Hant"]

    def validate(self, value):
        if self.kind == "bool":
            if type(value) is not bool:
                raise ValueError(f"{self.key} must be true or false")
        elif self.kind == "choice":
            if not isinstance(value, str) or value not in self.choices:
                raise ValueError(f"Invalid choice for {self.key}")
        else:
            bounded(self.key, value, self.low, self.high)
            if abs(value - round(value, self.decimals)) > 1e-8:
                raise ValueError(f"{self.key} supports {self.decimals} decimal places")

    def get(self, settings):
        value = settings.to_dict()
        for part in self.path:
            value = value[part]
        return value


GROUPS = {
    "harmonics": ("Harmonics", "諧波"), "envelope": ("ADSR", "ADSR"),
    "filter": ("Filter", "濾波"), "delay": ("Delay", "回聲"), "reverb": ("Reverb", "混響"),
}
PARAMETERS = {}
for k in range(1, 9):
    PARAMETERS[f"h{k}"] = Parameter(f"h{k}", ("patch", "harmonics", k - 1), "harmonics", (f"H{k} · relative strength", f"H{k} · 相對強度"))
for key, low, high in (("attack", .01, .4), ("decay", .02, .6), ("sustain", 0, 1), ("release", .02, 1.2)):
    unit = "" if key == "sustain" else " (s)"
    zh_unit = "" if key == "sustain" else "（秒）"
    PARAMETERS[key] = Parameter(key, ("patch", key), "envelope", (key.title() + unit, key.title() + zh_unit), low=low, high=high)
PARAMETERS.update({
    "filter_enabled": Parameter("filter_enabled", ("effects", "filter", "enabled"), "filter", ("Filter enabled", "啟用濾波"), "bool"),
    "filter_mode": Parameter("filter_mode", ("effects", "filter", "mode"), "filter", ("Filter type", "濾波類型"), "choice", choices=("lowpass", "highpass")),
    "cutoff_hz": Parameter("cutoff_hz", ("effects", "filter", "cutoff_hz"), "filter", ("Low-pass cutoff (Hz)", "低通截止頻率（Hz）"), "int", 120, 4000, 100, 0),
    "resonance": Parameter("resonance", ("effects", "filter", "resonance"), "filter", ("Resonance", "共振")),
})
for group, definitions in (
    ("delay", (("time", "time_seconds", "Echo spacing (s)", "回聲間隔（秒）", .08, .6),
               ("decay", "decay_seconds", "Decay time (s)", "衰減時間（秒）", .2, 3),
               ("mix", "mix", "Wet mix", "濕聲比例", 0, .5))),
    ("reverb", (("room", "room", "Room size", "空間大小", 0, .85),
                ("damping", "damping", "Damping", "阻尼", 0, 1),
                ("mix", "mix", "Wet mix", "濕聲比例", 0, .5))),
):
    PARAMETERS[f"{group}_enabled"] = Parameter(f"{group}_enabled", ("effects", group, "enabled"), group,
        (f"{group.title()} enabled", "啟用回聲" if group == "delay" else "啟用混響"), "bool")
    for suffix, field, en, zh, low, high in definitions:
        key = f"{group}_{suffix}"
        PARAMETERS[key] = Parameter(key, ("effects", group, field), group, (en, zh), low=low, high=high)


def replace_parameters(settings: SoundSettings, changes: dict[str, Any]):
    data = settings.to_dict()
    data["patch"]["harmonics"] = list(data["patch"]["harmonics"])
    for key, value in changes.items():
        if key not in PARAMETERS:
            raise ValueError(f"Unknown sound control: {key}")
        parameter = PARAMETERS[key]
        parameter.validate(value)
        node = data
        for part in parameter.path[:-1]:
            node = node[part]
        node[parameter.path[-1]] = value
    return SoundSettings.from_dict(data)
