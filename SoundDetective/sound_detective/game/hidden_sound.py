"""One guided hidden-sound prototype; broad sound requirements, not exact answers.

The prototype evaluates nominal envelope times, harmonic power proportions and
echo settings. These are transparent synthesis-domain criteria, not a measured
perceptual similarity percentage or an audio classifier.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path

from ..audio.models import SoundSettings, SynthPatch, EffectSettings, DelaySettings
from ..audio.sequence import NoteEvent, NoteSequence
from .parameters import PARAMETERS, replace_parameters
from .storage import atomic_json_write


STAGES = (("attack", "release"), ("h2", "h3", "h4"),
          ("delay_enabled", "delay_time", "delay_decay", "delay_mix"))
HISTORY_LIMIT = 30
VERSION = "hidden-sound-prototype-v1"


@dataclass(frozen=True)
class HiddenCase:
    id: str = "W01"
    title: dict = field(default_factory=lambda: {"en": "The Corridor Signal", "zh-Hant": "走廊裡的電子信號"})
    initial: SoundSettings = field(default_factory=lambda: SoundSettings(
        SynthPatch(attack=.25, decay=.10, sustain=.65, release=.80),
        EffectSettings(delay=DelaySettings(False, .12, 1.50, .45))))
    reference: SoundSettings = field(default_factory=lambda: SoundSettings(
        SynthPatch((1, .50, .25, .12, 0, 0, 0, 0), .02, .10, .65, .12),
        EffectSettings(delay=DelaySettings(True, .24, .50, .20))))
    sequence: NoteSequence = field(default_factory=lambda: NoteSequence((NoteEvent(69, .07, .18, 100),)))
    editable_parameters: tuple = sum(STAGES, ())


def load_hidden_case():
    return HiddenCase()


def parameters(settings):
    return {key: PARAMETERS[key].get(settings) for key in sum(STAGES, ())}


def settings_from_parameters(data):
    if not isinstance(data, dict) or set(data) != set(sum(STAGES, ())):
        raise ValueError("Unexpected hidden-sound controls")
    return replace_parameters(load_hidden_case().initial, data)


@dataclass(frozen=True)
class Requirement:
    code: str
    value: float
    low: float
    high: float
    fade: float

    @property
    def passed(self):
        return self.low - 1e-9 <= self.value <= self.high + 1e-9

    @property
    def score(self):
        distance = max(self.low - self.value, self.value - self.high, 0)
        return max(0., 100 * (1 - distance / self.fade))

    @property
    def direction(self):
        return "close" if self.passed else "low" if self.value < self.low else "high"


@dataclass(frozen=True)
class Assessment:
    groups: tuple

    @property
    def passed(self):
        return tuple(all(item.passed for item in group) for group in self.groups)

    @property
    def scores(self):
        # An absent echo is diagnosed before its inactive knobs.
        return tuple(0. if i == 2 and not group[0].passed else
                     sum(item.score for item in group) / len(group)
                     for i, group in enumerate(self.groups))

    @property
    def total(self):
        value = sum(self.scores) / 3
        return value if all(self.passed) else min(value, 99.)

    def problem(self, stage):
        group = self.groups[stage]
        if stage == 2 and not group[0].passed:
            return group[0]
        remaining = [item for item in group if not item.passed]
        return min(remaining, key=lambda item: item.score) if remaining else None


def assess(settings):
    patch, echo = settings.patch, settings.effects.delay
    power = sum(value * value for value in patch.harmonics)
    upper = sum(value * value for value in patch.harmonics[1:]) / max(power, 1e-12)
    return Assessment((
        (Requirement("attack", patch.attack, .01, .06, .15),
         Requirement("release", patch.release, .02, .22, .45)),
        (Requirement("brightness", upper, .12, .40, .12),),
        (Requirement("echo", float(echo.active and not settings.effects.bypass), 1, 1, 1),
         Requirement("delay_time", echo.time_seconds, .18, .32, .15),
         Requirement("delay_decay", echo.decay_seconds, .20, .80, 1.),
         Requirement("delay_mix", echo.mix, .10, .30, .20)),
    ))


@dataclass
class HiddenSession:
    current: SoundSettings = field(default_factory=lambda: load_hidden_case().initial)
    unlocked: int = 0
    attempts: int = 0
    hints: list = field(default_factory=lambda: [0, 0, 0])
    records: list = field(default_factory=list)
    solution: dict | None = None

    @property
    def solved(self):
        return self.solution is not None

    @property
    def current_is_submitted(self):
        return bool(self.records) and parameters(self.current) == self.records[-1]["parameters"]

    @property
    def focus(self):
        passed = assess(self.current).passed
        return next((i for i in range(self.unlocked + 1) if not passed[i]), self.unlocked)

    def update(self, changes):
        settings = settings_from_parameters(changes)
        allowed = sum(STAGES[:self.unlocked + 1], ())
        if any(changes[key] != PARAMETERS[key].get(self.current) for key in changes if key not in allowed):
            raise ValueError("Finish earlier stages before changing these controls")
        self.current = settings

    def submit(self):
        result = assess(self.current)
        self.attempts += 1
        while self.unlocked < 2 and all(result.passed[:self.unlocked + 1]):
            self.unlocked += 1
        if all(result.passed) and self.solution is None:
            self.solution = parameters(self.current)
        self.records.append({"number": self.attempts, "parameters": parameters(self.current)})
        self.records = self.records[-HISTORY_LIMIT:]
        return result

    def request_hint(self):
        stage = self.focus
        self.hints[stage] = min(3, self.hints[stage] + 1)
        return self.hints[stage]

    def restore(self, index):
        self.current = settings_from_parameters(self.records[index]["parameters"])

    def to_dict(self):
        return {"version": VERSION, "current": parameters(self.current), "unlocked": self.unlocked,
                "attempts": self.attempts, "hints": self.hints, "records": self.records, "solution": self.solution}

    @classmethod
    def from_dict(cls, data):
        keys = {"version", "current", "unlocked", "attempts", "hints", "records", "solution"}
        if not isinstance(data, dict) or set(data) != keys or data["version"] != VERSION:
            raise ValueError("Unsupported hidden-sound save")
        if type(data["unlocked"]) is not int or not 0 <= data["unlocked"] <= 2:
            raise ValueError("Invalid stage")
        if type(data["attempts"]) is not int or data["attempts"] < 0:
            raise ValueError("Invalid attempt count")
        if not isinstance(data["hints"], list) or len(data["hints"]) != 3 or any(type(v) is not int or not 0 <= v <= 3 for v in data["hints"]):
            raise ValueError("Invalid hints")
        records = data["records"]
        if not isinstance(records, list) or len(records) != min(data["attempts"], HISTORY_LIMIT):
            raise ValueError("Invalid history")
        for index, record in enumerate(records, data["attempts"] - len(records) + 1):
            if not isinstance(record, dict) or set(record) != {"number", "parameters"} or type(record["number"]) is not int or record["number"] != index:
                raise ValueError("Invalid history record")
            settings_from_parameters(record["parameters"])
        solution = data["solution"]
        if solution is not None and not all(assess(settings_from_parameters(solution)).passed):
            raise ValueError("Invalid solution")
        current = settings_from_parameters(data["current"])
        locked = sum(STAGES[data["unlocked"] + 1:], ())
        if any(PARAMETERS[key].get(current) != PARAMETERS[key].get(load_hidden_case().initial) for key in locked):
            raise ValueError("Locked controls were modified")
        return cls(current, data["unlocked"], data["attempts"], list(data["hints"]), records, solution)


def load_hidden_session(path):
    path = Path(path)
    if not path.exists():
        return HiddenSession()
    if path.stat().st_size > 1_000_000:
        raise ValueError("Hidden-sound save is too large")
    return HiddenSession.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_hidden_session(path, session):
    atomic_json_write(path, session.to_dict())


def lesson(stage):
    """Generic A3 teaching examples, distinct from the A4 hidden reference."""
    base = SoundSettings(SynthPatch(attack=.02, decay=.10, sustain=.65, release=.12))
    if stage == 0:
        pair = (replace_parameters(base, {"release": .06}), replace_parameters(base, {"release": .85}))
    elif stage == 1:
        pair = (base, replace_parameters(base, {"h2": .75, "h3": .50, "h4": .30}))
    else:
        pair = (base, replace_parameters(base, {"delay_enabled": True, "delay_time": .25, "delay_decay": .6, "delay_mix": .25}))
    return pair, NoteSequence((NoteEvent(57, .07, .18, 100),))
