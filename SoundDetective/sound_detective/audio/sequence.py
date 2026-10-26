"""Validated musical events, independent of the renderer, UI, and audio devices."""

from collections.abc import Mapping
from dataclasses import dataclass
import math
from numbers import Integral, Real


SEQUENCE_SCHEMA_VERSION = 1
REFERENCE_MIDI_PITCH = 57  # A3, 220 Hz; preserves the original render default.


def _midi_integer(name: str, value: int, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")
    return int(value)


def _seconds(name: str, value: float, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a number in seconds")
    try:
        seconds = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(seconds) or seconds < 0 or (positive and seconds == 0):
        constraint = "greater than zero" if positive else "non-negative"
        raise ValueError(f"{name} must be finite and {constraint}")
    return seconds


@dataclass(frozen=True)
class NoteEvent:
    """One note: MIDI pitch 0–127, absolute seconds, and MIDI velocity 1–127.

    Duration ends at key release, before the patch's release envelope/effect tail.
    Velocity zero is not a sounding note; omit that event instead.
    """

    pitch: int
    start_seconds: float
    duration_seconds: float
    velocity: int = 100

    def __post_init__(self):
        object.__setattr__(self, "pitch", _midi_integer("pitch", self.pitch, 0, 127))
        object.__setattr__(self, "velocity", _midi_integer("velocity", self.velocity, 1, 127))
        object.__setattr__(self, "start_seconds", _seconds("start_seconds", self.start_seconds))
        object.__setattr__(self, "duration_seconds", _seconds("duration_seconds", self.duration_seconds, positive=True))
        if not math.isfinite(self.end_seconds):
            raise ValueError("note end_seconds must be finite")
        if self.end_seconds <= self.start_seconds:
            raise ValueError("duration_seconds must produce an end after start_seconds")

    @property
    def end_seconds(self) -> float:
        """Absolute key-release time; excludes ADSR release and effects."""
        return self.start_seconds + self.duration_seconds

    @property
    def frequency_hz(self) -> float:
        """Twelve-tone equal temperament, with MIDI 69 (A4) at 440 Hz."""
        return 440.0 * 2.0 ** ((self.pitch - 69) / 12.0)

    @property
    def velocity_gain(self) -> float:
        """Linear amplitude multiplier for the future renderer, not loudness."""
        return self.velocity / 127.0

    def to_dict(self) -> dict:
        return {
            "pitch": self.pitch,
            "start_seconds": self.start_seconds,
            "duration_seconds": self.duration_seconds,
            "velocity": self.velocity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NoteEvent":
        fields = {"pitch", "start_seconds", "duration_seconds", "velocity"}
        if not isinstance(data, dict) or set(data) - fields:
            raise ValueError("NoteEvent must contain only pitch, start_seconds, duration_seconds, and velocity")
        try:
            return cls(**data)
        except TypeError as error:
            raise ValueError(f"Invalid NoteEvent: {error}") from error


@dataclass(frozen=True)
class NoteSequence:
    """Immutable events on a shared timeline; rests and overlaps are retained.

    Events are sorted by onset, preserving input order for simultaneous notes.
    Empty sequences are valid editing data; they contain no playable audio.
    This model does not impose a renderer's pitch, polyphony, or length limits.
    """

    events: tuple[NoteEvent, ...] = ()

    def __post_init__(self):
        if isinstance(self.events, (str, bytes, bytearray, Mapping)):
            raise ValueError("events must be an iterable of NoteEvent objects")
        try:
            events = tuple(self.events)
        except TypeError as error:
            raise ValueError("events must be an iterable of NoteEvent objects") from error
        if any(not isinstance(event, NoteEvent) for event in events):
            raise ValueError("events must contain only NoteEvent objects")
        object.__setattr__(self, "events", tuple(sorted(events, key=lambda event: event.start_seconds)))

    @property
    def duration_seconds(self) -> float:
        """Last key release, including leading rests but excluding sound tails."""
        return max((event.end_seconds for event in self.events), default=0.0)

    def to_dict(self) -> dict:
        return {
            "schema_version": SEQUENCE_SCHEMA_VERSION,
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "NoteSequence":
        if not isinstance(data, dict) or set(data) != {"schema_version", "events"}:
            raise ValueError("NoteSequence requires exactly schema_version and events")
        version = data["schema_version"]
        if type(version) is not int or version != SEQUENCE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported sequence schema_version; expected {SEQUENCE_SCHEMA_VERSION}")
        if not isinstance(data["events"], list):
            raise ValueError("events must be a JSON array")
        events = []
        for index, item in enumerate(data["events"]):
            try:
                events.append(NoteEvent.from_dict(item))
            except ValueError as error:
                raise ValueError(f"Invalid events[{index}]: {error}") from error
        return cls(events=tuple(events))
