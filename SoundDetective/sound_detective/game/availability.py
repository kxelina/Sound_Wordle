"""Optional recorded-music content must never prevent synthesized play."""

from dataclasses import dataclass
from pathlib import Path

from ..audio.sc_client import ROOT


@dataclass(frozen=True)
class MusicAvailability:
    available: bool
    reason: str
    case_id: str = "M01"

    def to_dict(self):
        return {"available": self.available, "case_id": self.case_id, "reason": self.reason}


def music_availability(*, root=ROOT):
    from .music_cases import load_music_case
    from .recorded_pitch import load_recorded_pitch_map
    try:
        case = load_music_case(root=Path(root), verify=True)
        load_recorded_pitch_map(case)
        return MusicAvailability(True, "ready", case.id)
    except (OSError, ValueError, TypeError, KeyError) as error:
        return MusicAvailability(False, str(error))
