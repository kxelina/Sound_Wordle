"""Validated display annotations for recorded pitch regions, separate from saves.

The pitch map describes a predominant-pitch estimate in mixed audio, not an
isolated voice or a complete polyphonic transcription. Game corrections stay
in cents and keep the recording's original timing.
"""

from dataclasses import dataclass
import json
import math

from ..audio.models import bounded


@dataclass(frozen=True)
class RecordedNote:
    start_seconds: float
    end_seconds: float
    midi: int
    confidence: float
    region_index: int | None = None

    def __post_init__(self):
        bounded("note start", self.start_seconds, 0, 3600)
        bounded("note end", self.end_seconds, 0, 3600)
        if self.end_seconds <= self.start_seconds or type(self.midi) is not int or not 0 <= self.midi <= 127:
            raise ValueError("Invalid recorded pitch note")
        bounded("pitch confidence", self.confidence, 0, 1)
        if self.region_index is not None and (type(self.region_index) is not int or self.region_index < 0):
            raise ValueError("Invalid pitch-region index")


@dataclass(frozen=True)
class RecordedPitchMap:
    notes: tuple
    seconds: float

    def __post_init__(self):
        object.__setattr__(self, "notes", tuple(self.notes))
        bounded("pitch map duration", self.seconds, .1, 20)
        if not self.notes or len(self.notes) > 512:
            raise ValueError("A pitch map needs 1–512 notes")
        previous, regions = 0., set()
        for note in self.notes:
            if not isinstance(note, RecordedNote) or note.start_seconds < previous-1e-8 or note.end_seconds > self.seconds+1e-8:
                raise ValueError("Recorded pitch annotations must be ordered and non-overlapping")
            previous = note.end_seconds
            if note.region_index is not None:
                if note.region_index in regions:
                    raise ValueError("Duplicate editable pitch region")
                regions.add(note.region_index)
        if regions != set(range(len(regions))):
            raise ValueError("Pitch-map region indices must be contiguous")

    @property
    def editable_notes(self):
        return tuple(sorted((n for n in self.notes if n.region_index is not None), key=lambda n: n.region_index))

    def current_pitch(self, region_index, initial_cents, corrections):
        return self.editable_notes[region_index].midi + (initial_cents[region_index]+corrections[region_index])/100

    def correction_for_pitch(self, region_index, pitch, initial_cents):
        bounded("display pitch", pitch, 0, 127)
        return max(-600, min(600, round((pitch-self.editable_notes[region_index].midi)*100-initial_cents[region_index])))


def load_recorded_pitch_map(case):
    path = case.evidence.with_name(f"{case.id}-pitch-map.json")
    if path.stat().st_size > 256_000:
        raise ValueError("Pitch map exceeds the size limit")
    data = json.loads(path.read_text(encoding="utf-8"))
    fields = {"schema_version", "case_id", "case_fingerprint", "source_sha256", "analysis", "seconds", "notes"}
    if (not isinstance(data, dict) or set(data) != fields or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["case_id"] != case.id or data["case_fingerprint"] != case.fingerprint
            or data["source_sha256"] != case.source_sha256 or data["seconds"] != case.seconds
            or not isinstance(data["analysis"], str) or not data["analysis"]
            or not isinstance(data["notes"], list)):
        raise ValueError("Pitch map does not match this recording/case")
    try:
        mapping = RecordedPitchMap(tuple(RecordedNote(**note) for note in data["notes"]), data["seconds"])
    except TypeError as error:
        raise ValueError("Invalid pitch-map note fields") from error
    if len(mapping.editable_notes) != len(case.regions):
        raise ValueError("Pitch map is missing editable regions")
    for note, region in zip(mapping.editable_notes, case.regions):
        if not (math.isclose(note.start_seconds, region.start_seconds, abs_tol=1e-7)
                and math.isclose(note.end_seconds, region.end_seconds, abs_tol=1e-7)):
            raise ValueError("Pitch-map timing disagrees with the repair regions")
    return mapping
