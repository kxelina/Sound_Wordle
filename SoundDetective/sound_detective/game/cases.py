"""Validated, reachable cases with progressively unlocked audio controls."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from ..audio.matching import MatchConfig
from ..audio.models import SoundSettings, bounded
from ..audio.sequence import NoteSequence
from .parameters import PARAMETERS, replace_parameters
from .catalog import TIMBRE_IDS


@dataclass(frozen=True)
class CaseDefinition:
    id: str
    revision: int
    title: dict[str, str]
    description: dict[str, str]
    reference: SoundSettings
    initial: SoundSettings
    sequence: NoteSequence
    hint_threshold: float
    comparison: MatchConfig
    fingerprint: str
    editable_parameters: tuple[str, ...]
    diagnostic_profile: str = "basic"
    investigation: dict | None = None

    def parameters(self, settings):
        return {key: PARAMETERS[key].get(settings) for key in self.editable_parameters}

    def settings(self, cutoff_hz=None, release=None, **changes):
        """Missing values use initial settings; unknown/locked controls are rejected."""
        if cutoff_hz is not None:
            changes["cutoff_hz"] = cutoff_hz
        if release is not None:
            changes["release"] = release
        if set(changes) - set(self.editable_parameters):
            raise ValueError("Cannot edit a locked control")
        return replace_parameters(self.initial, changes)

    def total(self, spectrum, envelope):
        return {"combined": (spectrum + envelope) / 2, "spectrum": spectrum, "envelope": envelope}[self.comparison.focus]

    def passes(self, total, spectrum, envelope, tail):
        config = self.comparison
        passed = total >= config.pass_score
        if config.focus == "combined":
            passed = passed and min(spectrum, envelope) >= config.component_floor
        if config.focus != "spectrum":
            passed = passed and tail >= config.tail_floor
        return passed


def load_case(path: str | Path) -> CaseDefinition:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    fields = {"schema_version", "id", "revision", "mode", "title", "description", "editable_parameters",
              "reference_settings", "initial_settings", "sequence", "hint_threshold", "comparison"}
    if not isinstance(data, dict) or not fields <= set(data) or set(data) - fields - {"diagnostic_profile","investigation"}:
        raise ValueError("Invalid case fields")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1 or data["id"] not in TIMBRE_IDS or data["mode"] != "timbre_match":
        raise ValueError("Unsupported case schema or mode")
    if type(data["revision"]) is not int or data["revision"] < 1:
        raise ValueError("Invalid case revision")
    for key in ("title", "description"):
        strings = data[key]
        if not isinstance(strings, dict) or set(strings) != {"en", "zh-Hant"} or not all(isinstance(v, str) and v.strip() for v in strings.values()):
            raise ValueError("Case text requires English and Traditional Chinese")
    editable = data["editable_parameters"]
    if not isinstance(editable, list) or not editable or any(not isinstance(key, str) or key not in PARAMETERS for key in editable) or len(set(editable)) != len(editable):
        raise ValueError("Invalid editable controls")
    profile = data.get("diagnostic_profile", "basic")
    if profile not in ("basic", "adsr", "harmonics", "filter", "delay", "reverb", "combined"):
        raise ValueError("Invalid diagnostic profile")
    reference = SoundSettings.from_dict(data["reference_settings"])
    initial = SoundSettings.from_dict(data["initial_settings"])
    # Every locked parameter must agree, so the reference can actually be reached.
    reconstructed = replace_parameters(initial, {key: PARAMETERS[key].get(reference) for key in editable})
    replace_parameters(initial, {key: PARAMETERS[key].get(initial) for key in editable})
    if reconstructed != reference or reference.patch.is_silent or initial.patch.is_silent:
        raise ValueError("Locked parameters must match a non-silent reference")
    if reference.effects.bypass or initial.effects.bypass:
        raise ValueError("Case effects must not be globally bypassed")
    config = MatchConfig(**data["comparison"])
    bounded("hint_threshold", data["hint_threshold"], 0, config.pass_score)
    sequence = NoteSequence.from_dict(data["sequence"])
    if not 1 <= len(sequence.events) <= 8 or sequence.duration_seconds + 1.4 > 30:
        raise ValueError("Cases require a short, non-empty note sequence")
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    investigation=data.get('investigation')
    if investigation is not None:
        if not isinstance(investigation,dict) or set(investigation)!={'question','options','completion'} or not isinstance(investigation['options'],list) or len(investigation['options'])!=3:
            raise ValueError('Invalid investigation question')
        texts=[investigation['question'],investigation['completion']]
        for option in investigation['options']:
            if not isinstance(option,dict) or set(option)!={'label','feedback'}:raise ValueError('Invalid investigation option')
            texts.extend((option['label'],option['feedback']))
        if any(not isinstance(t,dict) or set(t)!={'en','zh-Hant'} or any(not isinstance(v,str) or not v.strip() or len(v)>1000 for v in t.values()) for t in texts):
            raise ValueError('Investigation text requires two languages')
    return CaseDefinition(data["id"], data["revision"], data["title"], data["description"], reference, initial,
                          sequence, data["hint_threshold"], config, fingerprint, tuple(editable), profile,investigation)


def load_campaign(directory=None):
    if directory is None:
        from ..audio.sc_client import ROOT
        directory = ROOT / "content/cases"
    cases = tuple(load_case(Path(directory) / f"{cid}.json") for cid in TIMBRE_IDS)
    if tuple(case.id for case in cases) != TIMBRE_IDS:
        raise ValueError("Campaign is missing registered cases")
    return cases
