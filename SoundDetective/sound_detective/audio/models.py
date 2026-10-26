"""声音参数；不依赖界面，也不包含关卡或评分逻辑。"""

from dataclasses import asdict, dataclass, field
import math
from numbers import Real

SAMPLE_RATE = 44_100
FUNDAMENTAL_HZ = 220.0
HARMONIC_COUNT = 8
NOTE_OFF_SECONDS = 1.20
DURATION_SECONDS = 2.60


def bounded(name: str, value: float, low: float, high: float) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be finite and between {low} and {high}")


def enabled_flag(value: bool) -> None:
    if type(value) is not bool:
        raise ValueError("enabled must be true or false")


@dataclass(frozen=True)
class SynthPatch:
    """相对谐波幅度与线性 ADSR；时间单位为秒。"""
    harmonics: tuple[float, ...] = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    attack: float = 0.03
    decay: float = 0.18
    sustain: float = 0.65
    release: float = 0.25

    def __post_init__(self):
        object.__setattr__(self, "harmonics", tuple(self.harmonics))
        if len(self.harmonics) != HARMONIC_COUNT:
            raise ValueError("Exactly eight harmonics are required")
        for index, value in enumerate(self.harmonics, 1):
            bounded(f"H{index}", value, 0, 1)
        bounded("attack", self.attack, 0.01, 0.40)
        bounded("decay", self.decay, 0.02, 0.60)
        bounded("sustain", self.sustain, 0, 1)
        bounded("release", self.release, 0.02, 1.20)

    @property
    def is_silent(self) -> bool:
        return not any(self.harmonics)


@dataclass(frozen=True)
class FilterSettings:
    enabled: bool = False
    mode: str = "lowpass"
    cutoff_hz: float = 1200.0
    resonance: float = 0.0

    def __post_init__(self):
        enabled_flag(self.enabled)
        if self.mode not in ("lowpass", "highpass"):
            raise ValueError("filter.mode must be lowpass or highpass")
        bounded("cutoff_hz", self.cutoff_hz, 120, 4000)
        bounded("resonance", self.resonance, 0, 1)

    @property
    def rq(self) -> float:
        # UI 共振从 0 到 1，Q 从 1/sqrt(2) 到 4；SC 使用其倒数。
        return math.sqrt(2) * (0.25 / math.sqrt(2)) ** self.resonance


@dataclass(frozen=True)
class DelaySettings:
    enabled: bool = False
    time_seconds: float = 0.25
    decay_seconds: float = 0.8
    mix: float = 0.25

    def __post_init__(self):
        enabled_flag(self.enabled)
        bounded("delay.time_seconds", self.time_seconds, 0.08, 0.60)
        bounded("delay.decay_seconds", self.decay_seconds, 0.20, 3.0)
        bounded("delay.mix", self.mix, 0, 0.50)

    @property
    def active(self) -> bool:
        return self.enabled and self.mix > 0


@dataclass(frozen=True)
class ReverbSettings:
    enabled: bool = False
    room: float = 0.5
    damping: float = 0.5
    mix: float = 0.20

    def __post_init__(self):
        enabled_flag(self.enabled)
        bounded("reverb.room", self.room, 0, 0.85)
        bounded("reverb.damping", self.damping, 0, 1)
        bounded("reverb.mix", self.mix, 0, 0.50)

    @property
    def active(self) -> bool:
        return self.enabled and self.mix > 0


@dataclass(frozen=True)
class EffectSettings:
    filter: FilterSettings = field(default_factory=FilterSettings)
    delay: DelaySettings = field(default_factory=DelaySettings)
    reverb: ReverbSettings = field(default_factory=ReverbSettings)
    bypass: bool = False

    def __post_init__(self):
        for name, expected in (("filter", FilterSettings), ("delay", DelaySettings), ("reverb", ReverbSettings)):
            if not isinstance(getattr(self, name), expected):
                raise ValueError(f"{name} must be {expected.__name__}")
        if type(self.bypass) is not bool:
            raise ValueError("bypass must be true or false")

    def initial_duration(self, patch: SynthPatch, *, note_off_seconds: float = NOTE_OFF_SECONDS) -> float:
        """先估算长度；渲染器随后测量尾音，必要时延长。"""
        bounded("note_off_seconds", note_off_seconds, 0, math.inf)
        # Keep a dry silent margin ahead of the renderer's final fade/tail probe.
        dry_duration = max(DURATION_SECONDS, note_off_seconds + patch.release + 0.20)
        if self.bypass:
            return dry_duration
        tail = 0.0
        if self.delay.active:
            tail += self.delay.time_seconds + self.delay.decay_seconds + 0.25
        if self.reverb.active:
            tail += 2.0 + 8.0 * self.reverb.room
        return max(dry_duration, note_off_seconds + patch.release + tail)


@dataclass(frozen=True)
class SoundSettings:
    patch: SynthPatch = field(default_factory=SynthPatch)
    effects: EffectSettings = field(default_factory=EffectSettings)

    def __post_init__(self):
        if not isinstance(self.patch, SynthPatch) or not isinstance(self.effects, EffectSettings):
            raise ValueError("SoundSettings requires a SynthPatch and EffectSettings")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SoundSettings":
        if not isinstance(data, dict) or set(data) - {"patch", "effects"}:
            raise ValueError("Settings must contain only patch and effects")
        try:
            effects = dict(data.get("effects", {}))
            effects["filter"] = FilterSettings(**effects.get("filter", {}))
            effects["delay"] = DelaySettings(**effects.get("delay", {}))
            effects["reverb"] = ReverbSettings(**effects.get("reverb", {}))
            return cls(SynthPatch(**data.get("patch", {})), EffectSettings(**effects))
        except (TypeError, KeyError) as error:
            raise ValueError(f"Invalid sound settings: {error}") from error

    def synth_arguments(self, duration: float) -> list:
        """扁平 OSC 控制参数，与 synth.scd 的控件名保持一致。"""
        patch, fx = self.patch, self.effects
        args = []
        for index, value in enumerate(patch.harmonics, 1):
            args.extend((f"h{index}", float(value)))
        mode = (1 if fx.filter.mode == "lowpass" else 2) if fx.filter.enabled and not fx.bypass else 0
        args.extend((
            "attack", float(patch.attack), "decay", float(patch.decay),
            "sustain", float(patch.sustain), "release", float(patch.release),
            "filterMode", mode, "cutoff", float(fx.filter.cutoff_hz), "rq", fx.filter.rq,
            "delayOn", int(fx.delay.active and not fx.bypass),
            "delayTime", float(fx.delay.time_seconds), "delayDecay", float(fx.delay.decay_seconds),
            "delayMix", float(fx.delay.mix), "reverbOn", int(fx.reverb.active and not fx.bypass),
            "room", float(fx.reverb.room), "damping", float(fx.reverb.damping),
            "reverbMix", float(fx.reverb.mix), "duration", float(duration),
        ))
        return args
