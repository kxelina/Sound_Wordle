"""Data-driven music restoration: one effect at a time, then pitch."""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import unicodedata

import soundfile as sf

from ..audio.models import EffectSettings, SoundSettings, bounded
from ..audio.pitch_corruption import PitchRegion
from ..audio.sc_client import ROOT
from .music_repair import PITCH_TOLERANCE_CENTS, RepairSettings, check_repair


def normalize_answer(text):
    if not isinstance(text, str) or len(text) > 128:
        raise ValueError("Enter a song title of at most 128 characters")
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def _localized(data):
    if (not isinstance(data, dict) or set(data) != {"en", "zh-Hant"}
            or not all(isinstance(v, str) and v.strip() for v in data.values())):
        raise ValueError("Music case text needs English and Traditional Chinese")
    return data


def _asset(root, relative):
    if not isinstance(relative, str) or not relative:
        raise ValueError("Invalid music asset path")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Music assets must stay in the project")
    return result


@dataclass(frozen=True)
class MusicCaseDefinition:
    id: str
    title: dict
    clues: tuple
    answers: tuple
    source: Path
    evidence: Path
    source_sha256: str
    evidence_sha256: str
    start_seconds: float
    seconds: float
    regions: tuple
    initial_effects: EffectSettings
    reveal_gain: float
    fingerprint: str

    def verify_assets(self):
        for path, expected in ((self.source, self.source_sha256), (self.evidence, self.evidence_sha256)):
            if not path.is_file():
                raise FileNotFoundError(f"Required music-case asset is missing: {path}")
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Music-case asset changed: {path.name}")
        source, evidence = sf.info(self.source), sf.info(self.evidence)
        if source.duration < self.start_seconds + self.seconds or source.channels not in (1, 2):
            raise ValueError("Full song cannot supply the configured excerpt")
        if evidence.samplerate != 44100 or evidence.channels != 2 or evidence.duration < self.seconds:
            raise ValueError("Invalid prerecorded evidence")


def load_music_case(path=None, *, root=ROOT, verify=True):
    root = Path(root).resolve()
    path = Path(path) if path is not None else root / "content/music_cases/M01.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fields = {"schema_version", "id", "title", "clues", "accepted_answers", "source_audio",
        "evidence_audio", "source_sha256", "evidence_sha256", "excerpt", "regions", "initial_effects", "reveal_gain"}
    if not isinstance(data, dict) or set(data) != fields or type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported music-case configuration")
    if not isinstance(data["id"], str) or not data["id"].startswith("M") or not data["id"][1:].isdigit():
        raise ValueError("Invalid music-case ID")
    title = _localized(data["title"])
    if not isinstance(data["clues"], list) or not data["clues"]:
        raise ValueError("At least one starting clue is required")
    clues = tuple(_localized(clue) for clue in data["clues"])
    aliases = data["accepted_answers"]
    if not isinstance(aliases, list) or not aliases or any(not normalize_answer(s) for s in aliases):
        raise ValueError("Invalid accepted song titles")
    excerpt = data["excerpt"]
    if not isinstance(excerpt, dict) or set(excerpt) != {"start_seconds", "seconds"}:
        raise ValueError("Invalid excerpt")
    bounded("start_seconds", excerpt["start_seconds"], 0, 3600)
    bounded("seconds", excerpt["seconds"], 1, 20)
    if not isinstance(data["regions"], list) or not 1 <= len(data["regions"]) <= 64:
        raise ValueError("Music case requires 1–64 fixed pitch regions")
    regions = tuple(PitchRegion(**item) for item in data["regions"])
    previous = 0
    for region in regions:
        if region.start_seconds < previous or region.end_seconds > excerpt["seconds"] or abs(region.cents) > 600:
            raise ValueError("Music-case pitch regions overlap or exceed excerpt limits")
        previous = region.end_seconds
    for key in ("source_sha256", "evidence_sha256"):
        value = data[key]
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("Invalid asset digest")
    effects = SoundSettings.from_dict({"effects": data["initial_effects"]}).effects
    bounded("reveal_gain", data["reveal_gain"], .01, 1)
    case = MusicCaseDefinition(data["id"], title, clues, tuple(aliases),
        _asset(root, data["source_audio"]), _asset(root, data["evidence_audio"]),
        data["source_sha256"], data["evidence_sha256"], excerpt["start_seconds"], excerpt["seconds"],
        regions, effects, data["reveal_gain"], hashlib.sha256(path.read_bytes()).hexdigest())
    if verify:
        case.verify_assets()
    return case


@dataclass(frozen=True)
class MusicSettings:
    corrections: tuple
    repair: RepairSettings = field(default_factory=RepairSettings)

    def __post_init__(self):
        object.__setattr__(self, "corrections", tuple(self.corrections))

    def validate(self, case):
        if len(self.corrections) != len(case.regions) or not isinstance(self.repair, RepairSettings):
            raise ValueError("Invalid reconstruction controls")
        for value in self.corrections:
            bounded("pitch correction", value, -600, 600)
            if abs(value - round(value)) > 1e-8:
                raise ValueError("Pitch correction uses whole cents")
        return self

    def residual_regions(self, case):
        self.validate(case)
        return tuple(PitchRegion(r.start_seconds, r.end_seconds,
                                 0 if abs(r.cents + value) <= PITCH_TOLERANCE_CENTS else r.cents + value)
                     for r, value in zip(case.regions, self.corrections))

    def to_dict(self):
        return {"corrections": list(self.corrections), "repair": self.repair.to_dict()}

    @classmethod
    def from_dict(cls, data, case):
        if not isinstance(data, dict) or set(data) != {"corrections", "repair"} or not isinstance(data["corrections"], list):
            raise ValueError("Invalid music controls")
        return cls(tuple(data["corrections"]), RepairSettings.from_dict(data["repair"])).validate(case)


STAGED_VERSION = "staged-music-v2"
STAGE_ORDER = ("filter", "delay", "reverb", "pitch")
LEGACY_STAGE_ORDER = ("pitch", "filter", "delay", "reverb")
STAGE_PASS_SCORE = 90.
PITCH_STAGE_TOLERANCE_CENTS = 25


@dataclass(frozen=True)
class StageResult:
    stage: str
    score: float
    passed: bool
    attempt: int
    next_stage: str
    newly_solved: bool


class MusicSession:
    def __init__(self, case):
        self.case = case
        self._settings = MusicSettings((0,) * len(case.regions))
        self.migrated = False
        self.attempts = 0
        self.stage_index = 0
        self.stage_scores = {}
        self.last = None
        self.first_clear = None
        self.legacy_progress = None

    @property
    def stages(self):
        return self._stages(STAGE_ORDER)

    def _stages(self, order):
        fx = self.case.initial_effects
        return tuple(name for name in order if name == "pitch" or (
            not fx.bypass and (getattr(fx, name).enabled if name == "filter" else getattr(fx, name).active)))

    @property
    def stage(self):
        return "complete" if self.solved else self.stages[self.stage_index]

    @property
    def solved(self):
        return self.stage_index == len(self.stages)

    @property
    def completed(self):
        return self.stages[:self.stage_index]

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, settings):
        settings.validate(self.case)
        if self.solved:
            raise ValueError("Restart before editing a completed restoration")
        if self.stage != "pitch" and settings.corrections != self._settings.corrections:
            raise ValueError("Pitch is editable only during the pitch stage")
        for name in ("filter", "delay", "reverb"):
            if name != self.stage and getattr(settings.repair.estimates, name) != getattr(self._settings.repair.estimates, name):
                raise ValueError("Only the current repair device is editable")
        self._settings = settings

    def render_settings(self):
        """Completed stages stay repaired; future devices cannot repair early."""
        from dataclasses import replace
        estimates = RepairSettings().estimates
        for name in ("filter", "delay", "reverb"):
            if name in self.completed:
                value = getattr(self.case.initial_effects, name)
            elif name == self.stage:
                value = getattr(self.settings.repair.estimates, name)
            else:
                value = getattr(estimates, name)
            estimates = replace(estimates, **{name: value})
        corrections = (tuple(-r.cents for r in self.case.regions) if "pitch" in self.completed else self.settings.corrections)
        return MusicSettings(corrections, RepairSettings(estimates))

    def report(self):
        return check_repair(self.case, self.render_settings())

    def submit(self):
        if self.solved:
            return self.last
        stage = self.stage
        module = next(item for item in self.report().modules if item.group == stage)
        score = 100 * module.fraction
        passed = score >= STAGE_PASS_SCORE
        if stage == "pitch":
            # Do not let a duration-weighted average hide one badly wrong note.
            passed = passed and all(abs(r.cents + c) <= PITCH_STAGE_TOLERANCE_CENTS
                                    for r, c in zip(self.case.regions, self.settings.corrections))
        self.attempts += 1
        if passed:
            self.stage_scores[stage] = score
            self.stage_index += 1
        if self.solved and self.first_clear is None:
            self.first_clear = {"attempt": self.attempts, "version": STAGED_VERSION}
        self.last = StageResult(stage, score, passed, self.attempts, self.stage, self.solved)
        return self.last

    def restart(self):
        first, legacy = self.first_clear, self.legacy_progress
        self.__init__(self.case)
        self.first_clear, self.legacy_progress = first, legacy

    def to_dict(self):
        return {"schema_version": 4, "case_id": self.case.id, "case_fingerprint": self.case.fingerprint,
            "settings": self.settings.to_dict(), "attempts": self.attempts,
            "stage_index": self.stage_index, "stage_scores": dict(self.stage_scores),
            "first_clear": self.first_clear, "legacy_progress": self.legacy_progress}

    @classmethod
    def from_dict(cls, data, case):
        old_fields = {"schema_version", "case_id", "case_fingerprint", "settings", "attempts", "solved", "first_clear"}
        fields = old_fields - {"solved"} | {"stage_index", "stage_scores", "legacy_progress"}
        if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
                or data["schema_version"] not in (1, 2, 3, 4)
                or set(data) != (fields if data["schema_version"] >= 3 else old_fields)
                or data["case_id"] != case.id or data["case_fingerprint"] != case.fingerprint):
            raise ValueError("Incompatible music progress")
        if type(data["attempts"]) is not int or not 0 <= data["attempts"] <= 100000:
            raise ValueError("Invalid music progress")
        result = cls(case)
        if data["schema_version"] < 3:
            legacy = {key: data[key] for key in ("schema_version", "attempts", "solved", "first_clear")}
            cls._validate_legacy(legacy)
        else:
            legacy = data["legacy_progress"]
            if legacy is not None:
                cls._validate_legacy(legacy)
        if data["schema_version"] == 1:
            old = data["settings"]
            if not isinstance(old, dict) or set(old) != {"corrections", "effects"} or not isinstance(old["corrections"], list):
                raise ValueError("Invalid legacy music controls")
            # Old forward-FX knobs cannot be treated as inverse-device estimates:
            # they initially contained the hidden answer. Keep pitch and clears,
            # start the new repair devices independently, and back up in the UI.
            SoundSettings.from_dict({"effects": old["effects"]})
            result._settings = MusicSettings(tuple(old["corrections"])).validate(case)
        else:
            result._settings = MusicSettings.from_dict(data["settings"], case)
        result.legacy_progress = legacy
        if data["schema_version"] < 3:
            result._settings = MusicSettings(result.settings.corrections)
            result.migrated = True
            return result
        # Validate old staged saves in their original order before reordering.
        # An old numeric index must never complete a different device implicitly.
        stages = result._stages(LEGACY_STAGE_ORDER) if data["schema_version"] == 3 else result.stages
        index = data["stage_index"]
        if type(index) is not int or not 0 <= index <= len(stages):
            raise ValueError("Invalid music stage")
        completed = stages[:index]
        stage = stages[index] if index < len(stages) else "complete"
        scores = data["stage_scores"]
        if not isinstance(scores, dict) or set(scores) != set(completed) or data["attempts"] < index:
            raise ValueError("Music stages require preceding successful submissions")
        for score in scores.values():
            bounded("stage score", score, STAGE_PASS_SCORE, 100)
        result.stage_scores, result.attempts = dict(scores), data["attempts"]
        first = data["first_clear"]
        if first is not None:
            versions = ("staged-music-v1",) if data["schema_version"] == 3 else ("staged-music-v1", STAGED_VERSION)
            if not isinstance(first, dict) or set(first) != {"attempt", "version"} or first["version"] not in versions:
                raise ValueError("Invalid restoration first clear")
            if type(first["attempt"]) is not int or not len(stages) <= first["attempt"] <= 100000:
                raise ValueError("Invalid restoration first-clear count")
        if stage == "complete" and first is None:
            raise ValueError("Completed restoration requires a first-clear record")
        result.first_clear = first
        raw_report = check_repair(case, result.settings)
        for module in raw_report.modules:
            if module.group in completed and 100 * module.fraction < STAGE_PASS_SCORE:
                raise ValueError("Completed stage controls do not meet the threshold")
        if "pitch" in completed and any(abs(r.cents+c) > PITCH_STAGE_TOLERANCE_CENTS
                                                for r, c in zip(case.regions, result.settings.corrections)):
            raise ValueError("Completed pitch stage still has an out-of-tune region")
        defaults = RepairSettings().estimates
        for name in ("filter", "delay", "reverb"):
            if name not in completed and name != stage and getattr(result.settings.repair.estimates, name) != getattr(defaults, name):
                raise ValueError("Future music controls must remain at their initial values")
        if data["schema_version"] == 3:
            # Keep passed FX in the new prefix. Pitch corrections remain a draft
            # until the final submission; an already completed case stays clear.
            result.stage_index = next((i for i, name in enumerate(result.stages) if name not in completed), len(result.stages))
            result.stage_scores = {name: scores[name] for name in result.completed}
            result.migrated = True
        else:
            result.stage_index = index
        return result

    @staticmethod
    def _validate_legacy(data):
        if not isinstance(data, dict) or set(data) != {"schema_version", "attempts", "solved", "first_clear"}:
            raise ValueError("Invalid legacy music record")
        if type(data["schema_version"]) is not int or data["schema_version"] not in (1, 2):
            raise ValueError("Invalid legacy schema")
        if type(data["attempts"]) is not int or not 0 <= data["attempts"] <= 100000 or type(data["solved"]) is not bool:
            raise ValueError("Invalid legacy attempts")
        first = data["first_clear"]
        if first is not None and (type(first) is not int or not 1 <= first <= 100000):
            raise ValueError("Invalid legacy first clear")
        if data["solved"] and (first is None or data["attempts"] < 1):
            raise ValueError("Legacy completion requires a valid record")
