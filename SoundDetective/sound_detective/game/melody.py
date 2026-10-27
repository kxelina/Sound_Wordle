"""W02 rhythm → melody → timbre challenges and separate composition saves.

Scores measure authored reconstruction progress, not perceptual similarity.
The original target phrase is composed for this project; no song is required.
"""

from dataclasses import dataclass, field
import json
import hashlib
from pathlib import Path

from ..audio.matching import MatchConfig
from ..audio.models import SoundSettings
from ..audio.sequence import NoteEvent, NoteSequence
from .hidden_sound import HISTORY_LIMIT, load_hidden_case
from .parameters import PARAMETERS, replace_parameters
from .progress import grade_progress
from .storage import atomic_json_write
from .catalog import MELODY_IDS
from .composition import CompositionDraft

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
    stages: tuple = (0,1,2)
    story: dict | None = None
    clues: dict | None = None
    completion: dict | None = None
    fingerprint: str = ''
    silent_cells: tuple = ()

    def __post_init__(self):
        if self.id not in MELODY_IDS or self.stages not in ((0,),(0,1),(0,1,2)) or not self.pattern.notes:
            raise ValueError('Invalid melody case')
        if 2 not in self.stages and self.initial!=self.reference:
            raise ValueError('Locked timbre must match the reference')
        if any(type(cell) is not int or not 0<=cell<STEPS for cell in self.silent_cells) or len(set(self.silent_cells))!=len(self.silent_cells):
            raise ValueError('Invalid silent cells')
        if any(n.start<=cell<n.start+n.length for cell in self.silent_cells for n in self.pattern.notes):raise ValueError('Reference overlaps a required rest')

    @property
    def sequence(self):
        return self.pattern.sequence()

    def parameters(self, settings):
        return sound_values(settings)

    def settings(self, **changes):
        return replace_parameters(self.initial, changes)


def load_melody_cases(directory=None):
    from ..audio.sc_client import ROOT
    directory=Path(directory or ROOT/'content/melody_cases')
    cases=[MelodyCase()]
    for cid in MELODY_IDS[1:]:
        data=json.loads((directory/(cid+'.json')).read_text('utf-8'))
        fields={'schema_version','id','title','story','pattern','sound','stages','clues','completion','silent_cells'}
        if not isinstance(data,dict) or set(data)!=fields or type(data['schema_version']) is not int or data['schema_version']!=1 or data['id']!=cid:
            raise ValueError('Invalid authored melody case')
        texts=[data['title'],data['story'],data['completion']]
        stages=tuple(data['stages'])
        if not isinstance(data['stages'],list) or any(type(s) is not int for s in data['stages']):raise ValueError('Invalid melody stages')
        if set(data['clues'])!={str(stage) for stage in stages}:raise ValueError('Missing stage clues')
        for clues in data['clues'].values():
            if not isinstance(clues,list) or len(clues)!=4:raise ValueError('Expected initial and three hint tiers')
            texts.extend(clues)
        if any(not isinstance(t,dict) or set(t)!={'en','zh-Hant'} or any(not isinstance(v,str) or not v.strip() or len(v)>1500 for v in t.values()) for t in texts):
            raise ValueError('Melody text requires two languages')
        sound=SoundSettings.from_dict(data['sound'])
        fingerprint=hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        cases.append(MelodyCase(id=cid,title=data['title'],initial=sound,reference=sound,
            pattern=MelodyPattern.from_dict(data['pattern']),stages=stages,story=data['story'],
            clues=data['clues'],completion=data['completion'],fingerprint=fingerprint,silent_cells=tuple(data['silent_cells'])))
    return tuple(cases)


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
    active: tuple = (0,1,2)

    @property
    def total(self):
        value = sum(self.scores[i] for i in self.active) / len(self.active)
        return value if all(self.passed) else min(value, 99.)


def compare_draft(draft, case=None):
    case = case or MelodyCase()
    quality, pairs = align_notes(case.pattern, draft.pattern)
    denominator = max(len(case.pattern.notes), len(draft.pattern.notes))
    rhythm = 100 * quality / denominator
    if any(n.start<=cell<n.start+n.length for cell in case.silent_cells for n in draft.pattern.notes):
        rhythm=min(rhythm,89.)  # A high mean timing score cannot erase a required rest.
    melody = 100 * sum(max(0., 1 - abs(case.pattern.notes[i].pitch - draft.pattern.notes[j].pitch) / 4)
                       for i, j, _ in pairs) / denominator
    timbre = None if draft.sound.patch.is_silent or 2 not in case.stages else grade_progress(case, draft.sound)
    sound = 100. if 2 not in case.stages else timbre.total if timbre else 0.
    return MelodyResult((rhythm, melody, sound),
                        (rhythm >= 90, 1 not in case.stages or melody >= 90,
                         2 not in case.stages or bool(timbre and timbre.passed)), pairs, timbre,case.stages)


@dataclass
class MelodySession:
    challenge: Draft = field(default_factory=Draft)
    free: CompositionDraft = field(default_factory=CompositionDraft)
    mode: str = "challenge"
    unlocked: int = 0
    attempts: int = 0
    hints: list = field(default_factory=lambda: [0, 0, 0])
    records: list = field(default_factory=list)
    solution: dict | None = None
    case: MelodyCase = field(default_factory=MelodyCase)

    def __post_init__(self):
        if self.case.id!='W02' and self.challenge==Draft():self.challenge=Draft(sound=self.case.initial)

    @property
    def current(self):
        return self.free if self.mode == "free" else self.challenge

    @property
    def solved(self):
        return self.solution is not None

    @property
    def focus(self):
        result = compare_draft(self.challenge,self.case)
        return next((i for i in self.case.stages if i<=self.unlocked and not result.passed[i]), self.unlocked)

    @property
    def current_is_submitted(self):
        return bool(self.records) and self.challenge.to_dict() == self.records[-1]["draft"]

    def set_mode(self, mode):
        if mode not in ("challenge", "free") or mode=='free' and self.case.id!='W02':
            raise ValueError("Unknown workshop mode")
        self.mode = mode

    def update(self, draft):
        if self.mode == "free":
            if isinstance(draft,Draft):draft=CompositionDraft.from_legacy(draft)
            if not isinstance(draft,CompositionDraft):raise ValueError('Expected a composition')
            self.free=draft
            return
        if not isinstance(draft, Draft):raise ValueError('Expected a challenge draft')
        if draft.tempo != TEMPO:
            raise ValueError("Challenge tempo is fixed")
        if (self.unlocked == 0 or 1 not in self.case.stages) and any(n.pitch != LOW_PITCH for n in draft.pattern.notes):
            raise ValueError("Pitch unlocks after the rhythm stage")
        if (self.unlocked < 2 or 2 not in self.case.stages) and draft.sound != self.case.initial:
            raise ValueError("Sound controls unlock after the melody stage")
        self.challenge = draft

    def submit(self):
        if self.mode == "free":
            return None  # Composition never consumes an attempt or gets graded.
        if not self.challenge.pattern.notes or self.challenge.sound.patch.is_silent:
            raise ValueError("Add an audible note before submitting")
        result = compare_draft(self.challenge,self.case)
        self.attempts += 1
        while self.unlocked < self.case.stages[-1] and all(result.passed[:self.unlocked + 1]):
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
            self.free = CompositionDraft()
        else:
            self.challenge, self.unlocked, self.attempts = Draft(sound=self.case.initial), 0, 0
            self.hints, self.records = [0, 0, 0], []

    def to_dict(self):
        data={"version": VERSION, "challenge": self.challenge.to_dict(), "free": self.free.to_dict(),
                "mode": self.mode, "unlocked": self.unlocked, "attempts": self.attempts,
                "hints": self.hints, "records": self.records, "solution": self.solution}
        if self.case.id!='W02':data.update(case_id=self.case.id,case_fingerprint=self.case.fingerprint)
        return data

    @classmethod
    def from_dict(cls, data,case=None):
        case=case or MelodyCase()
        fields={"version", "challenge", "free", "mode", "unlocked", "attempts", "hints", "records", "solution"}
        if case.id!='W02':fields|={'case_id','case_fingerprint'}
        if not isinstance(data, dict) or set(data) != fields or data["version"] != VERSION:
            raise ValueError("Unsupported melody save")
        if case.id!='W02' and (data['case_id']!=case.id or data['case_fingerprint']!=case.fingerprint):
            raise ValueError('Melody save belongs to another case revision')
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
        if data['unlocked'] not in case.stages:raise ValueError('Invalid unlocked case stage')
        session = cls(unlocked=data["unlocked"],case=case)
        session.update(Draft.from_dict(data["challenge"]))
        for index, record in enumerate(records, data["attempts"] - len(records) + 1):
            if not isinstance(record, dict) or set(record) != {"number", "draft"} or type(record["number"]) is not int or record["number"] != index:
                raise ValueError("Invalid record")
            validator = cls(unlocked=data["unlocked"],case=case)
            validator.update(Draft.from_dict(record["draft"]))
            if not validator.challenge.pattern.notes or validator.challenge.sound.patch.is_silent:
                raise ValueError("Invalid silent submission")
        solution = data["solution"]
        if solution is not None:
            validator = cls(unlocked=case.stages[-1],case=case)
            validator.update(Draft.from_dict(solution))
            if not all(compare_draft(validator.challenge,case).passed):
                raise ValueError("Invalid solution")
        session.free = CompositionDraft.from_dict(data["free"])
        session.set_mode(data["mode"])
        session.attempts, session.hints, session.records, session.solution = data["attempts"], list(hints), records, solution
        return session


def load_melody_session(path,case=None):
    path = Path(path)
    case=case or MelodyCase()
    if not path.exists():
        return MelodySession(challenge=Draft(sound=case.initial),case=case)
    if path.stat().st_size > 64_000_000:
        raise ValueError("Melody save is too large")
    return MelodySession.from_dict(json.loads(path.read_text(encoding="utf-8")),case)


def save_melody_session(path, session):
    MelodySession.from_dict(session.to_dict(),session.case)
    path=Path(path)
    if path.exists():
        try:old=json.loads(path.read_text('utf-8'))
        except (ValueError,UnicodeError):old=None
        if isinstance(old,dict) and isinstance(old.get('free'),dict) and 'schema_version' not in old['free']:
            import shutil,uuid
            shutil.copy2(path,path.with_name(path.stem+'.before-studio-v2-'+uuid.uuid4().hex[:8]+'.json'))
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


def authored_melody_clue(case,draft,result,stage,tier,language):
    text=case.clues[str(stage)][tier][language]
    if tier<1:return text
    zh=language=='zh-Hant'
    if stage==0:
        delta=len(draft.pattern.notes)-len(case.pattern.notes)
        text+=(' 目前音符太多。' if delta>0 else ' 目前音符不足。' if delta<0 else '') if zh else (' Too many notes.' if delta>0 else ' More notes are needed.' if delta<0 else '')
        if case.id=='W08' and any(n.start<=8<n.start+n.length for n in draft.pattern.notes):
            text+=' 第三拍被一個音覆蓋了。' if zh else ' A note covers the silent third beat.'
        if delta==0:
            for i,j,q in result.pairs:
                target,actual=case.pattern.notes[i],draft.pattern.notes[j]
                if actual.length!=target.length:
                    text+=(f' 第 {j+1} 音需要'+('更長。' if actual.length<target.length else '更短。')) if zh else f' Note {j+1} should be '+('longer.' if actual.length<target.length else 'shorter.')
                    break
    elif stage==1:
        for i,j,q in result.pairs:
            expected,actual=case.pattern.notes[i].pitch,draft.pattern.notes[j].pitch
            if expected!=actual:
                text+=(f' 第 {j+1} 音可再'+('提高。' if actual<expected else '降低。')) if zh else f' Move note {j+1} '+('up.' if actual<expected else 'down.')
                break
    return text
