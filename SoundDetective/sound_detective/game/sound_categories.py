"""Data-driven hidden source cases and transparent construction-progress scores.

Attribute bands intentionally accept several patches. These scores guide
construction; they are not measured perceptual similarity percentages.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path

from ..audio.sc_client import ROOT
from ..audio.sound_sources import CONTROLS, SourcePatch
from .storage import atomic_json_write

CATEGORIES = {"all": ("All sounds", "全部聲音"), "nature": ("Nature", "自然聲音"),
              "instrument": ("Instruments", "樂器聲音"), "noise": ("Noise / electronics", "噪聲與電子"),
              "classic": ("Signals / melody", "信號與旋律")}
SCORING_VERSION = "source-bands-v1"


@dataclass(frozen=True)
class SourceCase:
    id: str
    category: str
    title: dict
    story: dict
    initial: SourcePatch
    target: SourcePatch
    bands: dict

    def __post_init__(self):
        if self.category not in ("nature", "instrument", "noise") or self.id not in ("W03", "W04", "W05", "W06"):
            raise ValueError("Invalid sound category case")
        if self.initial.recipe != self.target.recipe or self.initial.seed != self.target.seed:
            raise ValueError("Initial and target sources must share recipe and seed")
        for text in (self.title, self.story):
            if set(text) != {"en", "zh-Hant"} or any(not isinstance(v, str) or not v for v in text.values()):
                raise ValueError("Category case needs bilingual text")
        if set(self.bands) != {s.key for s in CONTROLS[self.target.recipe]}:
            raise ValueError("Missing sound attribute bands")
        values = dict(self.target.values)
        for spec in CONTROLS[self.target.recipe]:
            band = self.bands[spec.key]
            if not isinstance(band, list) or len(band) != 2:
                raise ValueError("Invalid sound attribute band")
            if not spec.low <= band[0] <= values[spec.key] <= band[1] <= spec.high:
                raise ValueError("Target must be inside the valid attribute band")


def load_source_cases(directory=None):
    directory = Path(directory or ROOT/"content/sound_cases")
    result = []
    for path in sorted(directory.glob("W*.json")):
        data = json.loads(path.read_text("utf-8"))
        recipe, seed = data.pop("recipe"), data.pop("seed")
        data["initial"] = SourcePatch.make(recipe, data["initial"], seed)
        data["target"] = SourcePatch.make(recipe, data["target"], seed)
        result.append(SourceCase(**data))
    if len({case.id for case in result}) != len(result):
        raise ValueError("Duplicate source case IDs")
    return tuple(result)


@dataclass(frozen=True)
class SourceMatch:
    total: float
    scores: dict
    directions: dict

    @property
    def passed(self):
        return self.total >= 90 and min(self.scores.values()) >= 85


def assess_source(case, patch):
    if patch.recipe != case.target.recipe or patch.seed != case.target.seed:
        raise ValueError("Patch belongs to another source case")
    scores, directions = {}, {}
    for spec in CONTROLS[patch.recipe]:
        value = dict(patch.values)[spec.key]
        low, high = case.bands[spec.key]
        direction = -1 if value < low else 1 if value > high else 0
        distance = max(spec.position(low)-spec.position(value), spec.position(value)-spec.position(high), 0)
        # Goal bands receive 100. Distance is measured on the control's audible
        # scale (log for noise bandwidth), with no penalty for valid alternatives.
        scores[spec.key] = max(0., 100*(1-distance)**2)
        directions[spec.key] = direction
    return SourceMatch(sum(scores.values())/len(scores), scores, directions)


def source_clue(case, patch, tier, language="en"):
    zh = language == "zh-Hant"
    result = assess_source(case, patch)
    key = min(result.scores, key=result.scores.get)
    if result.directions[key] == 0:
        return "各項聲音特徵已進入目標範圍，提交記錄這個版本。" if zh else "The sound attributes are inside the goal bands. Submit to record this version."
    spec = next(s for s in CONTROLS[patch.recipe] if s.key == key)
    text = spec.directions[result.directions[key] > 0][zh]
    if tier >= 2:
        text += (f" 試著{'提高' if result.directions[key] < 0 else '降低'}「{spec.labels[zh]}」。" if zh else
                 f" Try {'raising' if result.directions[key] < 0 else 'lowering'} {spec.labels[zh]}.")
    if tier >= 3:
        low, high = case.bands[key]
        text += (f" 可接受範圍：{low:g}–{high:g}{spec.unit}。" if zh else f" Accepted band: {low:g}–{high:g}{spec.unit}.")
    return text


@dataclass
class SourceSession:
    case: SourceCase
    current: SourcePatch | None = None
    attempts: int = 0
    hints: int = 0
    solved: bool = False
    best: float = 0
    last: SourcePatch | None = None
    records: list = field(default_factory=list)

    def __post_init__(self):
        if self.current is None:
            self.current = self.case.initial

    def update(self, patch):
        assess_source(self.case, patch)
        self.current = patch

    def submit(self):
        result = assess_source(self.case, self.current)
        self.attempts += 1
        self.last = self.current
        self.best = max(self.best, result.total)
        self.solved = self.solved or result.passed
        self.records.append({"number": self.attempts, "patch": self.current.to_dict(), "score": result.total})
        self.records = self.records[-30:]
        return result

    def to_dict(self):
        return {"schema_version": 1, "case": self.case.id, "scoring_version": SCORING_VERSION,
                "current": self.current.to_dict(), "attempts": self.attempts, "hints": self.hints,
                "solved": self.solved, "best": self.best,
                "last": self.last.to_dict() if self.last else None, "records": self.records}

    @classmethod
    def from_dict(cls, data, case):
        if not isinstance(data, dict) or set(data) != {"schema_version", "case", "scoring_version", "current", "attempts", "hints", "solved", "best", "last", "records"}:
            raise ValueError("Invalid category progress")
        if data["schema_version"] != 1 or data["case"] != case.id or data["scoring_version"] != SCORING_VERSION:
            raise ValueError("Incompatible category progress")
        if type(data["attempts"]) is not int or not 0 <= data["attempts"] <= 10**9 or type(data["hints"]) is not int or not 0 <= data["hints"] <= 3 or type(data["solved"]) is not bool:
            raise ValueError("Invalid category counters")
        from ..audio.models import bounded
        bounded("best", data["best"], 0, 100)
        patch = SourcePatch.from_dict(data["current"])
        assess_source(case, patch)
        last = SourcePatch.from_dict(data["last"]) if data["last"] else None
        if last:
            assess_source(case, last)
        records = data["records"]
        if not isinstance(records, list) or len(records) > 30 or len(records) != min(data["attempts"], 30):
            raise ValueError("Invalid category history")
        for index, record in enumerate(records):
            if not isinstance(record, dict) or set(record) != {"number", "patch", "score"} or type(record["number"]) is not int or record["number"] != data["attempts"]-len(records)+index+1:
                raise ValueError("Invalid category submission")
            result = assess_source(case, SourcePatch.from_dict(record["patch"]))
            bounded("score", record["score"], 0, 100)
            if abs(result.total-record["score"]) > 1e-6:
                raise ValueError("Invalid category score")
        if bool(data["attempts"]) != bool(last) or records and SourcePatch.from_dict(records[-1]["patch"]) != last:
            raise ValueError("Inconsistent category last submission")
        if records and data["best"]+1e-6 < max(r["score"] for r in records):
            raise ValueError("Inconsistent category best score")
        if not data["attempts"] and (data["solved"] or data["best"] != 0) or data["solved"] and data["best"] < 90:
            raise ValueError("Inconsistent category completion")
        if last and assess_source(case,last).passed and not data["solved"]:
            raise ValueError("Missing category completion")
        return cls(case, patch, data["attempts"], data["hints"], data["solved"], data["best"], last, records)


def load_source_session(path, case):
    path = Path(path)
    if not path.exists():
        return SourceSession(case)
    if path.stat().st_size > 250000:
        raise ValueError("Category progress is too large")
    return SourceSession.from_dict(json.loads(path.read_text("utf-8")), case)


def save_source_session(path, session):
    data = session.to_dict()
    SourceSession.from_dict(data, session.case)
    atomic_json_write(path, data)
