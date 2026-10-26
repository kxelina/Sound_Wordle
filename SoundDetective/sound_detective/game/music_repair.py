"""Known-source simulated restoration, not blind inverse audio processing.

Device values estimate a fixed damage recipe. Their calibration determines how
much of that damage remains when the clean source is rendered again. Bypassing
a repair device leaves its damage intact; it never bypasses the evidence FX.
"""

from dataclasses import asdict, dataclass, field, replace
import math

from ..audio.models import (DelaySettings, EffectSettings, FilterSettings,
                            ReverbSettings, SoundSettings)


REPAIR_VERSION = "simulated-repair-v1"
PITCH_TOLERANCE_CENTS = 12
GROUP_NAMES = {
    "pitch": ("Pitch", "音高"), "filter": ("Filter recovery", "頻段修復"),
    "delay": ("Echo cancellation", "回聲抵消"), "reverb": ("Room recovery", "空間修復"),
}


def initial_estimates():
    # Deliberately independent of the case's hidden corruption recipe.
    return EffectSettings(filter=FilterSettings(False, "lowpass", 2400, .05),
        delay=DelaySettings(False, .18, .8, .20),
        reverb=ReverbSettings(False, .65, .25, .35))


@dataclass(frozen=True)
class RepairSettings:
    """Reuses validated FX-shaped fields as *estimates*, never forward FX."""

    estimates: EffectSettings = field(default_factory=initial_estimates)

    def __post_init__(self):
        if not isinstance(self.estimates, EffectSettings) or self.estimates.bypass:
            raise ValueError("Repair estimates require individual device switches, without global bypass")

    def to_dict(self):
        return {"estimates": asdict(self.estimates)}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {"estimates"} or not isinstance(data["estimates"], dict):
            raise ValueError("Invalid repair estimates")
        return cls(SoundSettings.from_dict({"effects": data["estimates"]}).effects)


# Parameter key, model attribute, acceptance tolerance, broad tuning scale,
# logarithmic distance (octaves) for frequency. These are gameplay constants,
# not measurements of perceptual similarity.
FIELDS = {
    "filter": (("cutoff_hz", "cutoff_hz", .06, 1.2, True),
               ("resonance", "resonance", .025, .35, False)),
    "delay": (("delay_time", "time_seconds", .015, .20, False),
              ("delay_decay", "decay_seconds", .06, 1.4, False),
              ("delay_mix", "mix", .02, .35, False)),
    "reverb": (("reverb_room", "room", .03, .45, False),
               ("reverb_damping", "damping", .04, .55, False),
               ("reverb_mix", "mix", .02, .35, False)),
}

FIELD_NAMES = {
    "cutoff_hz": ("estimated cutoff", "估計截止頻率"),
    "resonance": ("estimated resonance", "估計共振"),
    "delay_time": ("estimated echo spacing", "估計回聲間隔"),
    "delay_decay": ("estimated echo decay", "估計回聲衰減時間"),
    "delay_mix": ("estimated echo amount", "估計回聲比例"),
    "reverb_room": ("estimated room size", "估計空間大小"),
    "reverb_damping": ("estimated damping", "估計阻尼"),
    "reverb_mix": ("estimated reverberation amount", "估計混響比例"),
}


@dataclass(frozen=True)
class Calibration:
    group: str
    fraction: float
    issue: str
    direction: int = 0  # +1 means increase the estimate, -1 decrease it.
    region: int | None = None

    def hint(self, language):
        zh = language == "zh-Hant"
        if self.issue == "inactive":
            return "本案沒有這類損傷。" if zh else "This case has no damage of this kind."
        if self.issue == "off":
            return ("先開啟這台修復設備；關閉它會保留原本的失真。" if zh else
                    "Enable this repair device first; switching it off leaves the damage intact.")
        if self.issue == "mode":
            return ("濾波類型估計不符；試試另一種損傷類型。" if zh else
                    "The estimated filter type does not match; try the other damage type.")
        if self.issue == "matched":
            return "校準已進入容許範圍，這部分損傷已移除。" if zh else "Within calibration tolerance; this damage is removed."
        if self.issue == "pitch":
            action = ("提高" if self.direction > 0 else "降低") if zh else ("Raise" if self.direction > 0 else "Lower")
            return (f"第 {self.region} 段仍偏音；試著{action}該段的音高校正。" if zh else
                    f"Region {self.region} is still out of tune; {action.lower()} its pitch correction.")
        name = FIELD_NAMES[self.issue][zh]
        if zh:
            return f"{name}偏{'低' if self.direction > 0 else '高'}；試著{'提高' if self.direction > 0 else '降低'}一點。"
        return f"The {name} is too {'low' if self.direction > 0 else 'high'}; try {'increasing' if self.direction > 0 else 'decreasing'} it."


def calibrate_effects(corruption, repair):
    """Smooth, monotone calibration; every relevant field must be near target."""
    results = []
    for group, fields in FIELDS.items():
        target, estimate = getattr(corruption, group), getattr(repair.estimates, group)
        active = not corruption.bypass and (target.enabled if group == "filter" else target.active)
        if not active:
            results.append(Calibration(group, 1., "inactive"))
        elif not estimate.enabled:
            results.append(Calibration(group, 0., "off"))
        elif group == "filter" and target.mode != estimate.mode:
            results.append(Calibration(group, 0., "mode"))
        else:
            errors = []
            for key, attribute, tolerance, scale, logarithmic in fields:
                wanted, actual = getattr(target, attribute), getattr(estimate, attribute)
                difference = math.log2(wanted / actual) if logarithmic else wanted - actual
                error = max(0., abs(difference) - tolerance) / scale
                errors.append((error, key, 1 if difference > 0 else -1))
            worst, key, direction = max(errors)
            fraction = math.exp(-2 * sum(error ** 2 for error, _, _ in errors))
            results.append(Calibration(group, fraction, key if worst else "matched", direction if worst else 0))
    return tuple(results)


@dataclass(frozen=True)
class RepairRecipe:
    effects: EffectSettings
    filter_repair: float = 0.


def remaining_effects(corruption, repair):
    """Keep damage timing/colour fixed; reduce its amount as calibration improves.

    Filter recovery crossfades the *known dry source* before echo and reverb.
    This avoids pretending that a second high-pass filter undoes a low-pass.
    """
    progress = {item.group: item.fraction for item in calibrate_effects(corruption, repair)}
    filt, echo, room = corruption.filter, corruption.delay, corruption.reverb
    filt = replace(filt, enabled=filt.enabled and progress["filter"] < 1)
    echo = replace(echo, enabled=echo.enabled and progress["delay"] < 1,
                   mix=echo.mix * (1 - progress["delay"]))
    room = replace(room, enabled=room.enabled and progress["reverb"] < 1,
                   mix=room.mix * (1 - progress["reverb"]))
    return RepairRecipe(EffectSettings(filt, echo, room, corruption.bypass), progress["filter"])


@dataclass(frozen=True)
class RepairReport:
    modules: tuple
    total: float


def check_repair(case, settings):
    settings.validate(case)
    residuals = [region.cents for region in settings.residual_regions(case)]
    weights = [region.end_seconds - region.start_seconds for region in case.regions]
    qualities = [math.exp(-2 * (abs(error) / max(abs(region.cents), 100)) ** 2)
                 for error, region in zip(residuals, case.regions)]
    pitch_progress = sum(weight * quality for weight, quality in zip(weights, qualities)) / sum(weights)
    worst = max(range(len(residuals)), key=lambda i: abs(residuals[i]))
    pitch = Calibration("pitch", pitch_progress, "pitch" if residuals[worst] else "matched",
                        -1 if residuals[worst] > 0 else 1, worst + 1)
    modules = (pitch, *calibrate_effects(case.initial_effects, settings.repair))
    active = [item.fraction for item in modules if item.issue != "inactive"]
    return RepairReport(modules, 100 * sum(active) / len(active))
