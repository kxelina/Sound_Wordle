"""One-bar composition and the W02 rhythm → melody → timbre challenge.

Scores measure authored reconstruction progress, not perceptual similarity.
The original target phrase is composed for this project; no song is required.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path

from ..audio.matching import MatchConfig
from ..audio.models import SoundSettings
from ..audio.sequence import NoteEvent, NoteSequence
from .hidden_sound import HISTORY_LIMIT, load_hidden_case
from .parameters import PARAMETERS, replace_parameters
from .progress import grade_progress
from .storage import atomic_json_write

STEPS, LOW_PITCH, HIGH_PITCH, TEMPO = 16, 60, 72, 100
VERSION = "melody-workshop-v1"


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in {low}..{high}")
    return value


@dataclass(frozen=True, order=True)
class GridNote:
    start: int
    length: int
    pitch: int = LOW_PITCH

    def __post_init__(self):
        integer(self.start, 0, STEPS - 1, "start")
        integer(self.length, 1, STEPS, "length")
        integer(self.pitch, LOW_PITCH, HIGH_PITCH, "pitch")
        if self.start + self.length > STEPS:
            raise ValueError("A note must stay inside the bar")

    def to_dict(self):
        return {"start": self.start, "length": self.length, "pitch": self.pitch}


@dataclass(frozen=True)
class MelodyPattern:
    notes: tuple = ()

    def __post_init__(self):
        if not isinstance(self.notes, (list, tuple)) or any(not isinstance(n, GridNote) for n in self.notes):
            raise ValueError("notes must be GridNote objects")
        notes = tuple(sorted(self.notes))
        if len(notes) > STEPS or any(a.start + a.length > b.start for a, b in zip(notes, notes[1:])):
            raise ValueError("This one-voice editor does not allow overlapping notes")
        object.__setattr__(self, "notes", notes)

    def to_dict(self):
        return [note.to_dict() for note in self.notes]

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, list) or len(data) > STEPS:
            raise ValueError("Invalid melody")
        notes = []
        for note in data:
            if not isinstance(note, dict) or set(note) != {"start", "length", "pitch"}:
                raise ValueError("Invalid grid note")
            notes.append(GridNote(**note))
        return cls(tuple(notes))

    def sequence(self, tempo=TEMPO):
        integer(tempo, 60, 160, "tempo")
        tick = 60 / tempo / 4  # Sixteenth-note grid, 4/4, one bar.
        return NoteSequence(tuple(NoteEvent(n.pitch, .07 + n.start * tick, n.length * tick, 100)
                                  for n in self.notes))


def sound_values(settings):
    return {key: spec.get(settings) for key, spec in PARAMETERS.items()}


def sound_from_values(values):
    if not isinstance(values, dict) or set(values) != set(PARAMETERS):
        raise ValueError("Invalid sound controls")
    return replace_parameters(load_hidden_case().initial, values)


@dataclass(frozen=True)
class MelodyCase:
    id: str = "W02"
    title: dict = field(default_factory=lambda: {"en": "The Four-Note Message", "zh-Hant": "四個音的留言"})
    initial: SoundSettings = field(default_factory=lambda: load_hidden_case().initial)
    reference: SoundSettings = field(default_factory=lambda: load_hidden_case().reference)
    pattern: MelodyPattern = field(default_factory=lambda: MelodyPattern((
        GridNote(0, 2, 60), GridNote(4, 2, 64), GridNote(8, 2, 67), GridNote(12, 4, 64))))
    editable_parameters: tuple = tuple(PARAMETERS)
    comparison: MatchConfig = field(default_factory=lambda: MatchConfig(pass_score=90, component_floor=85))

    @property
    def sequence(self):
        return self.pattern.sequence()

    def parameters(self, settings):
        return sound_values(settings)

    def settings(self, **changes):
        return replace_parameters(self.initial, changes)


@dataclass(frozen=True)
class Draft:
    pattern: MelodyPattern = field(default_factory=MelodyPattern)
    sound: SoundSettings = field(default_factory=lambda: MelodyCase().initial)
    tempo: int = TEMPO

    def __post_init__(self):
        if not isinstance(self.pattern, MelodyPattern) or not isinstance(self.sound, SoundSettings):
            raise ValueError("Invalid draft")
        integer(self.tempo, 60, 160, "tempo")
        # Also enforces registry precision and prevents bypass from escaping scoring.
        if sound_from_values(sound_values(self.sound)) != self.sound:
            raise ValueError("Unsupported sound settings")

    @property
    def sequence(self):
        return self.pattern.sequence(self.tempo)

    def to_dict(self):
        return {"notes": self.pattern.to_dict(), "sound": sound_values(self.sound), "tempo": self.tempo}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {"notes", "sound", "tempo"}:
            raise ValueError("Invalid draft fields")
        return cls(MelodyPattern.from_dict(data["notes"]), sound_from_values(data["sound"]), data["tempo"])


def align_notes(target, player):
    """Ordered, maximum-quality alignment using only onset and duration.

    Missing/extra notes contribute zero; pitch cannot conceal a timing error.
    Four grid steps of combined displacement/length error lose one note's credit.
    """
    a, b = target.notes, player.notes
    dp = [[(0., ()) for _ in range(len(b) + 1)] for _ in range(len(a) + 1)]
    for i, expected in enumerate(a, 1):
        for j, actual in enumerate(b, 1):
            q = max(0., 1 - (abs(expected.start - actual.start) + abs(expected.length - actual.length)) / 4)
            score, pairs = dp[i-1][j-1]
            dp[i][j] = max(((score + q, pairs + ((i-1, j-1, q),)), dp[i-1][j], dp[i][j-1]), key=lambda x: x[0])
    return dp[-1][-1]


@dataclass(frozen=True)
class MelodyResult:
    scores: tuple
    passed: tuple
    pairs: tuple
    timbre: object = None

    @property
    def total(self):
        value = sum(self.scores) / 3
        return value if all(self.passed) else min(value, 99.)


def compare_draft(draft, case=None):
    case = case or MelodyCase()
    quality, pairs = align_notes(case.pattern, draft.pattern)
    denominator = max(len(case.pattern.notes), len(draft.pattern.notes))
    rhythm = 100 * quality / denominator
    melody = 100 * sum(max(0., 1 - abs(case.pattern.notes[i].pitch - draft.pattern.notes[j].pitch) / 4)
                       for i, j, _ in pairs) / denominator
    timbre = None if draft.sound.patch.is_silent else grade_progress(case, draft.sound)
    sound = timbre.total if timbre else 0.
    return MelodyResult((rhythm, melody, sound),
                        (rhythm >= 90, melody >= 90, bool(timbre and timbre.passed)), pairs, timbre)


@dataclass
class MelodySession:
    challenge: Draft = field(default_factory=Draft)
    free: Draft = field(default_factory=Draft)
    mode: str = "challenge"
    unlocked: int = 0
    attempts: int = 0
    hints: list = field(default_factory=lambda: [0, 0, 0])
    records: list = field(default_factory=list)
    solution: dict | None = None

    @property
    def current(self):
        return self.free if self.mode == "free" else self.challenge

    @property
    def solved(self):
        return self.solution is not None

    @property
    def focus(self):
        result = compare_draft(self.challenge)
        return next((i for i in range(self.unlocked + 1) if not result.passed[i]), self.unlocked)

    @property
    def current_is_submitted(self):
        return bool(self.records) and self.challenge.to_dict() == self.records[-1]["draft"]

    def set_mode(self, mode):
        if mode not in ("challenge", "free"):
            raise ValueError("Unknown workshop mode")
        self.mode = mode

    def update(self, draft):
        if not isinstance(draft, Draft):
            raise ValueError("Expected a draft")
        if self.mode == "free":
            self.free = draft
            return
        if draft.tempo != TEMPO:
            raise ValueError("Challenge tempo is fixed")
        if self.unlocked == 0 and any(n.pitch != LOW_PITCH for n in draft.pattern.notes):
            raise ValueError("Pitch unlocks after the rhythm stage")
        if self.unlocked < 2 and draft.sound != MelodyCase().initial:
            raise ValueError("Sound controls unlock after the melody stage")
        self.challenge = draft

    def submit(self):
        if self.mode == "free":
            return None  # Composition never consumes an attempt or gets graded.
        if not self.challenge.pattern.notes or self.challenge.sound.patch.is_silent:
            raise ValueError("Add an audible note before submitting")
        result = compare_draft(self.challenge)
        self.attempts += 1
        while self.unlocked < 2 and all(result.passed[:self.unlocked + 1]):
            self.unlocked += 1
        if all(result.passed) and self.solution is None:
            self.solution = self.challenge.to_dict()
        self.records.append({"number": self.attempts, "draft": self.challenge.to_dict()})
        self.records = self.records[-HISTORY_LIMIT:]
        return result

    def request_hint(self):
        if self.mode == "free":
            return 0
        stage = self.focus
        self.hints[stage] = min(3, self.hints[stage] + 1)
        return self.hints[stage]

    def restore(self, index):
        self.set_mode("challenge")
        draft = Draft.from_dict(self.records[index]["draft"])
        self.update(draft)

    def reset(self):
        if self.mode == "free":
            self.free = Draft()
        else:
            self.challenge, self.unlocked, self.attempts = Draft(), 0, 0
            self.hints, self.records = [0, 0, 0], []

    def to_dict(self):
        return {"version": VERSION, "challenge": self.challenge.to_dict(), "free": self.free.to_dict(),
                "mode": self.mode, "unlocked": self.unlocked, "attempts": self.attempts,
                "hints": self.hints, "records": self.records, "solution": self.solution}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or set(data) != {"version", "challenge", "free", "mode", "unlocked", "attempts", "hints", "records", "solution"} or data["version"] != VERSION:
            raise ValueError("Unsupported melody save")
        integer(data["unlocked"], 0, 2, "stage")
        if type(data["attempts"]) is not int or data["attempts"] < 0:
            raise ValueError("Invalid attempt count")
        hints, records = data["hints"], data["records"]
        if not isinstance(hints, list) or len(hints) != 3:
            raise ValueError("Invalid hints")
        for value in hints:
            integer(value, 0, 3, "hint")
        if not isinstance(records, list) or len(records) != min(data["attempts"], HISTORY_LIMIT):
            raise ValueError("Invalid history")
        session = cls(unlocked=data["unlocked"])
        session.update(Draft.from_dict(data["challenge"]))
        for index, record in enumerate(records, data["attempts"] - len(records) + 1):
            if not isinstance(record, dict) or set(record) != {"number", "draft"} or type(record["number"]) is not int or record["number"] != index:
                raise ValueError("Invalid record")
            validator = cls(unlocked=data["unlocked"])
            validator.update(Draft.from_dict(record["draft"]))
            if not validator.challenge.pattern.notes or validator.challenge.sound.patch.is_silent:
                raise ValueError("Invalid silent submission")
        solution = data["solution"]
        if solution is not None:
            validator = cls(unlocked=2)
            validator.update(Draft.from_dict(solution))
            if not all(compare_draft(validator.challenge).passed):
                raise ValueError("Invalid solution")
        session.free = Draft.from_dict(data["free"])
        session.set_mode(data["mode"])
        session.attempts, session.hints, session.records, session.solution = data["attempts"], list(hints), records, solution
        return session


def load_melody_session(path):
    path = Path(path)
    if not path.exists():
        return MelodySession()
    if path.stat().st_size > 2_000_000:
        raise ValueError("Melody save is too large")
    return MelodySession.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_melody_session(path, session):
    atomic_json_write(path, session.to_dict())


def teaching_pair(stage):
    """Generic examples differ in key, shape and sound from the hidden phrase."""
    base = SoundSettings()
    if stage == 0:
        patterns = ((NoteEvent(57, .07, .15), NoteEvent(57, .67, .15)),
                    (NoteEvent(57, .07, .30), NoteEvent(57, .37, .60)))
    elif stage == 1:
        patterns = (tuple(NoteEvent(p, .07 + i * .4, .2) for i, p in enumerate((57, 59, 62))),
                    tuple(NoteEvent(p, .07 + i * .4, .2) for i, p in enumerate((62, 59, 57))))
    else:
        from .hidden_sound import lesson
        sounds, seq = lesson(1)
        return ((sounds[0], seq), (sounds[1], seq))
    return tuple((base, NoteSequence(notes)) for notes in patterns)
