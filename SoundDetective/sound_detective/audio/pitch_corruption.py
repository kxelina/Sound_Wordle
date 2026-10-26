"""Selective pitch-shift auditions; not a polyphonic transcription engine.

Regions stay on the original forward timeline. A mixed recording shifts all
voices in the chosen region. Clean note events/stems are needed to address an
individual voice in a future music game.
"""

from dataclasses import dataclass

import numpy as np

from .models import SAMPLE_RATE, bounded
from .sc_client import check_cancelled


@dataclass(frozen=True)
class PitchRegion:
    start_seconds: float
    end_seconds: float
    cents: float

    def __post_init__(self):
        bounded("start_seconds", self.start_seconds, 0, 3600)
        bounded("end_seconds", self.end_seconds, 0, 3600)
        bounded("cents", self.cents, -1200, 1200)
        if self.end_seconds <= self.start_seconds:
            raise ValueError("Pitch region must end after it starts")


def detune_regions(audio, regions, *, amount=1., cancel_event=None):
    """Shift selected spans in cents without changing their duration or order.

    100 cents = one semitone. amount=0 re-renders the original source exactly;
    it does not attempt to invert a previously corrupted export.
    """
    check_cancelled(cancel_event)
    source = np.asarray(audio, dtype=np.float64)
    if source.ndim != 1 or not source.size or not np.isfinite(source).all():
        raise ValueError("Expected nonempty finite mono audio")
    bounded("amount", amount, 0, 1)
    regions = tuple(regions)
    duration = len(source) / SAMPLE_RATE
    previous_end = 0
    for region in regions:
        if not isinstance(region, PitchRegion):
            raise ValueError("Expected PitchRegion instances")
        if region.start_seconds < previous_end or region.end_seconds > duration:
            raise ValueError("Regions must be ordered, non-overlapping and inside the source")
        previous_end = region.end_seconds
    result = source.copy()
    if not amount or not any(region.cents for region in regions):
        return result

    import librosa  # Optional developer dependency; zero-effect path needs none.

    context = round(.08 * SAMPLE_RATE)
    fade_frames = round(.008 * SAMPLE_RATE)
    for region in regions:
        check_cancelled(cancel_event)
        if not region.cents:
            continue
        start = round(region.start_seconds * SAMPLE_RATE)
        end = round(region.end_seconds * SAMPLE_RATE)
        if end <= start:
            raise ValueError("Pitch region is shorter than one sample")
        lo, hi = max(0, start-context), min(len(source), end+context)
        segment = source[lo:hi]
        # Fixed FFT size, including for short selected notes near a clip edge.
        padded = np.pad(segment, (0, max(0, 2048-len(segment))))
        shifted = librosa.effects.pitch_shift(padded, sr=SAMPLE_RATE,
            n_steps=region.cents * amount / 100, n_fft=2048, hop_length=256,
            res_type="soxr_hq", scale=False)[start-lo:end-lo]
        blend = np.ones(end-start)
        edge = min(fade_frames, len(blend) // 2)
        if edge:
            ramp = .5 - .5 * np.cos(np.linspace(0, np.pi, edge))
            blend[:edge], blend[-edge:] = ramp, ramp[::-1]
        result[start:end] = source[start:end] * (1-blend) + shifted * blend
    if not np.isfinite(result).all():
        raise ValueError("Pitch shift produced invalid audio")
    check_cancelled(cancel_event)
    return result
