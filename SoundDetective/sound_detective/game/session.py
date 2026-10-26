"""Submission transactions and score-gated clues; never gate on a past best."""

from dataclasses import asdict, dataclass, field,replace
import time

from ..audio.matching import ALGORITHM_VERSION, CLUES, MatchResult
from ..audio.models import bounded
from .cases import CaseDefinition
from .diagnostics import submission_diagnostics
from .progress import PROGRESS_CLUES, PROGRESS_VERSION, grade_progress, progress_passes


MAX_ATTEMPTS = 1000


@dataclass(frozen=True)
class AttemptRecord:
    run: int
    number: int
    parameters: dict
    total: float
    spectrum: float
    envelope: float
    tail: float
    diagnostics: tuple[str, ...]
    elapsed_seconds: float
    version: str = ALGORITHM_VERSION
    modules: dict[str, float] = field(default_factory=dict)

    def passed(self, case):
        if self.version == PROGRESS_VERSION:
            return progress_passes(case, self.total, self.modules)
        return case.passes(self.total, self.spectrum, self.envelope, self.tail)

    @property
    def cutoff_hz(self):
        return self.parameters.get("cutoff_hz")

    @property
    def release(self):
        return self.parameters.get("release")


class SessionState:
    def __init__(self, case: CaseDefinition, *, clock=time.monotonic):
        self.case = case
        self._clock = clock
        self._started_at = clock()
        self._elapsed_base = 0.
        self.current = case.initial
        self.records: list[AttemptRecord] = []
        self.run = 1
        self.language = "en"
        self.volume = .35
        self._token = 0
        self._pending = None
        self._submitted=0
        self._saved_first_pass=None

    @property
    def attempts(self):
        return tuple(record for record in self.records if record.run == self.run)

    @property
    def last(self):
        return self.attempts[-1] if self.attempts else None

    @property
    def first_pass(self):
        return self._saved_first_pass or next((record for record in self.records if record.passed(self.case)), None)

    @property
    def attempt_count(self):
        return self._submitted if self.case.id=='T09' else len(self.attempts)

    @property
    def solved(self):
        return self.last is not None and self.last.passed(self.case)

    @property
    def practice(self):
        return self.first_pass is not None and self.first_pass.run < self.run

    @property
    def elapsed_seconds(self):
        return self._elapsed_base + (max(0., self._clock() - self._started_at) if self._started_at is not None else 0.)

    @property
    def current_is_submitted(self):
        return self.last is not None and self.last.parameters == self.case.parameters(self.current)

    @property
    def visible_diagnostics(self):
        # No raw MatchResult is exposed to the view through this property.
        if self._pending is not None or not self.current_is_submitted or self.last.total < self.case.hint_threshold:
            return ()
        if self.last.version == PROGRESS_VERSION:
            return self.last.diagnostics
        # Old saves retain their original diagnostic history. Reinterpret the
        # current snapshot with today's module checks without rewriting it or
        # consuming an extra attempt. No audio regeneration is needed here.
        return submission_diagnostics(self.case, self.current, self.last)

    def update(self, **changes):
        if self.solved or self._pending is not None:
            raise RuntimeError("Restart a solved case, or stop the pending comparison before editing")
        self.current = self.case.settings(**(self.case.parameters(self.current) | changes))

    def begin_submission(self):
        if self.solved or self._pending is not None:
            raise RuntimeError("A submission is already pending or the case is solved")
        if self.case.id!='T09' and len(self.records) >= MAX_ATTEMPTS:
            raise ValueError("Submission history is full; export/archive this save before continuing")
        self._token += 1
        self._pending = (self._token, self.current)
        return self._token

    def cancel_submission(self):
        self._pending = None

    def complete_submission(self, token, result: MatchResult):
        if self._pending is None or token != self._pending[0]:
            return None
        if not isinstance(result, MatchResult) or result.version != ALGORITHM_VERSION or result.config != self.case.comparison:
            raise ValueError("Comparison version/configuration does not match this case")
        for key in ("total", "spectrum", "envelope", "tail"):
            bounded(key, getattr(result, key), 0, 100)
        if abs(result.total - self.case.total(result.spectrum, result.envelope)) > 1e-5:
            raise ValueError("Inconsistent focused score")
        if not result.diagnostics or any(code not in CLUES for code in result.diagnostics):
            raise ValueError("Invalid diagnosis codes")
        settings = self._pending[1]
        progress = grade_progress(self.case, settings)
        record = AttemptRecord(self.run, self.attempt_count + 1, self.case.parameters(settings),
            progress.total, result.spectrum, result.envelope, result.tail,
            progress.diagnostics, self.elapsed_seconds, PROGRESS_VERSION, progress.modules)
        self.records.append(record)
        if self.case.id=='T09':
            self._submitted+=1
            if record.passed(self.case) and self._saved_first_pass is None:self._saved_first_pass=record
            self.records=self.records[-30:]
        self._pending = None
        if record.passed(self.case):
            self._elapsed_base = record.elapsed_seconds
            self._started_at = None
        return record

    def restart(self):
        self.cancel_submission()
        self.run += 1
        self._submitted=0
        self.current = self.case.initial
        self._elapsed_base = 0.
        self._started_at = self._clock()

    def to_dict(self):
        data={"schema_version": 3, "case_id": self.case.id, "case_fingerprint": self.case.fingerprint,
            "scoring_version": PROGRESS_VERSION, "run": self.run, "language": self.language, "volume": self.volume,
            "current": self.case.parameters(self.current),
            "elapsed_seconds": self.elapsed_seconds, "records": [asdict(record) for record in self.records]}
        if self.case.id=='T09':data.update(schema_version=4,submitted=self._submitted,first_pass=asdict(self.first_pass) if self.first_pass else None)
        return data

    @classmethod
    def _from_rolling(cls,case,data,clock):
        base_fields={'schema_version','case_id','case_fingerprint','scoring_version','run','language','volume','current','elapsed_seconds','records'}
        if set(data)!=base_fields|{'submitted','first_pass'} or type(data['submitted']) is not int or data['submitted']<0:
            raise ValueError('Invalid rolling submission count')
        records=data['records']
        if not isinstance(records,list) or len(records)>30:raise ValueError('Invalid rolling history')
        normalized=[];numbers=[];last_run=None;last_number=None
        for item in records:
            if not isinstance(item,dict) or type(item.get('number')) is not int or item['number']<1 or type(item.get('run')) is not int:
                raise ValueError('Invalid rolling record')
            if item['run']==last_run and item['number']!=last_number+1:raise ValueError('Nonconsecutive history')
            if last_run is not None and item['run']!=last_run and item['number']!=1:raise ValueError('Invalid run start')
            count=normalized[-1]['number']+1 if item['run']==last_run else 1
            normalized.append(dict(item,number=count));numbers.append(item['number'])
            last_run,last_number=item['run'],item['number']
        base={key:data[key] for key in base_fields};base.update(schema_version=3,records=normalized)
        session=cls.from_dict(case,base,clock=clock)
        session.records=[replace(record,number=number) for record,number in zip(session.records,numbers)]
        current=[r for r in session.records if r.run==session.run]
        if data['submitted']!=(current[-1].number if current else 0):raise ValueError('Inconsistent rolling count')
        session._submitted=data['submitted'];session._saved_first_pass=None
        first=data['first_pass']
        if first is not None:
            if not isinstance(first,dict) or type(first.get('number')) is not int or first['number']<1 or type(first.get('run')) is not int or first['run']>session.run:
                raise ValueError('Invalid first-pass snapshot')
            sample=dict(base,run=first['run'],current=first.get('parameters'),elapsed_seconds=first.get('elapsed_seconds'),records=[dict(first,number=1)])
            checked=cls.from_dict(case,sample,clock=clock).records[0]
            checked=replace(checked,number=first['number'])
            if not checked.passed(case):raise ValueError('First-pass snapshot did not pass')
            if any(r.run==checked.run and r.number==checked.number and r!=checked for r in session.records):
                raise ValueError('First-pass snapshot differs from retained history')
            if any(r.passed(case) and (r.run,r.number)<(checked.run,checked.number) for r in session.records):
                raise ValueError('First-pass snapshot is not the first pass')
            if checked.run==session.run and (not session.last or not session.last.passed(case) or checked.number!=session.last.number):
                raise ValueError('Inconsistent first-pass run')
            session._saved_first_pass=checked
        if any(r.passed(case) for r in session.records) and session._saved_first_pass is None:raise ValueError('Missing first-pass snapshot')
        return session

    @classmethod
    def from_dict(cls, case, data, *, clock=time.monotonic):
        if case.id=='T09' and isinstance(data,dict) and type(data.get('schema_version')) is int and data['schema_version']==4:
            return cls._from_rolling(case,data,clock)
        fields = {"schema_version", "case_id", "case_fingerprint", "scoring_version", "run", "language", "volume", "current", "elapsed_seconds", "records"}
        if not isinstance(data, dict) or set(data) != fields:
            raise ValueError("Invalid save fields")
        if type(data["schema_version"]) is not int or data["schema_version"] not in (1, 2, 3) or data["case_id"] != case.id or data["case_fingerprint"] != case.fingerprint:
            raise ValueError("Save belongs to another case/scoring revision")
        expected_version = PROGRESS_VERSION if data["schema_version"] == 3 else ALGORITHM_VERSION
        if data["scoring_version"] != expected_version:
            raise ValueError("Save belongs to another scoring revision")
        legacy = data["schema_version"] == 1
        if legacy and case.id != "T01":
            raise ValueError("Legacy saves support only T01")
        if type(data["run"]) is not int or not 1 <= data["run"] <= 100000:
            raise ValueError("Invalid run number")
        if data["language"] not in ("en", "zh-Hant"):
            raise ValueError("Invalid saved language")
        bounded("volume", data["volume"], 0, 1)
        bounded("elapsed_seconds", data["elapsed_seconds"], 0, 1e9)
        if not isinstance(data["current"], dict) or set(data["current"]) != set(case.editable_parameters):
            raise ValueError("Invalid saved controls")
        session = cls(case, clock=clock)
        session.run, session.language, session.volume = data["run"], data["language"], data["volume"]
        session.current = case.settings(**data["current"])
        if not isinstance(data["records"], list) or len(data["records"]) > MAX_ATTEMPTS:
            raise ValueError("Invalid submission history")
        last_run, count, last_time, closed_run = 0, 0, 0., False
        for item in data["records"]:
            if legacy and isinstance(item, dict):
                if set(item) != ((set(AttemptRecord.__dataclass_fields__) - {"parameters", "modules"}) | {"cutoff_hz", "release"}):
                    raise ValueError("Invalid legacy submission")
                item = dict(item)
                item["parameters"] = {key: item.pop(key) for key in ("cutoff_hz", "release")}
            if data["schema_version"] < 3 and isinstance(item, dict):
                if "modules" in item:
                    raise ValueError("Legacy record contains new scoring fields")
                item = dict(item, modules={})
            if not isinstance(item, dict) or set(item) != set(AttemptRecord.__dataclass_fields__):
                raise ValueError("Invalid submission record")
            if type(item["run"]) is not int or not last_run <= item["run"] <= session.run or item["run"] < 1:
                raise ValueError("Invalid submission run order")
            if item["run"] != last_run:
                count, last_time, closed_run = 0, 0., False
            if type(item["number"]) is not int or item["number"] != count + 1 or closed_run:
                raise ValueError("Invalid submission order")
            if not isinstance(item["parameters"], dict) or set(item["parameters"]) != set(case.editable_parameters):
                raise ValueError("Invalid submitted controls")
            case.settings(**item["parameters"])
            for name in ("total", "spectrum", "envelope", "tail"):
                bounded(name, item[name], 0, 100)
            bounded("attempt time", item["elapsed_seconds"], last_time, 1e9)
            if item["version"] == ALGORITHM_VERSION:
                if item["modules"] != {} or abs(item["total"] - case.total(item["spectrum"], item["envelope"])) > 1e-5:
                    raise ValueError("Invalid historical audio score")
                valid_codes = CLUES
            elif item["version"] == PROGRESS_VERSION and data["schema_version"] == 3:
                expected = grade_progress(case, case.settings(**item["parameters"]))
                if not isinstance(item["modules"], dict) or set(item["modules"]) != set(expected.modules):
                    raise ValueError("Invalid reconstruction modules")
                for key, value in item["modules"].items():
                    bounded(key, value, 0, 100)
                    if abs(value - expected.modules[key]) > 1e-5:
                        raise ValueError("Inconsistent reconstruction module")
                if abs(item["total"] - expected.total) > 1e-5:
                    raise ValueError("Inconsistent reconstruction total")
                valid_codes = PROGRESS_CLUES
            else:
                raise ValueError("Invalid saved scoring version")
            if not isinstance(item["diagnostics"], (list, tuple)) or not item["diagnostics"] or any(not isinstance(code, str) or code not in valid_codes for code in item["diagnostics"]):
                raise ValueError("Invalid saved diagnosis")
            if item["version"] == PROGRESS_VERSION and tuple(item["diagnostics"]) != expected.diagnostics:
                raise ValueError("Diagnosis does not match the submitted reconstruction")
            record = AttemptRecord(**dict(item, diagnostics=tuple(item["diagnostics"])))
            session.records.append(record)
            last_run, count, last_time, closed_run = record.run, record.number, record.elapsed_seconds, record.passed(case)
        if session.last and data["elapsed_seconds"] < session.last.elapsed_seconds:
            raise ValueError("Saved time precedes last submission")
        if session.solved and not session.current_is_submitted:
            raise ValueError("Solved save must retain the submitted answer")
        session._elapsed_base = data["elapsed_seconds"]
        session._started_at = None if session.solved else clock()
        if case.id=='T09':
            session._submitted=session.last.number if session.last else 0
            session._saved_first_pass=session.first_pass
        return session
