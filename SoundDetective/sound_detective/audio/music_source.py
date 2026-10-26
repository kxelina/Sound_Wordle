"""Decode the selected local song excerpt for restoration playback."""

import librosa
import numpy as np
import soundfile as sf

from .models import SAMPLE_RATE, bounded


def load_excerpt(source, *, start_seconds=0., seconds=12.):
    """Decode only the requested local-file region; keep the source untouched."""
    bounded("start_seconds", start_seconds, 0, 3600)
    bounded("seconds", seconds, .1, 20)
    with sf.SoundFile(source) as stream:
        native_rate = stream.samplerate
        start_frame = round(start_seconds * native_rate)
        count = round(seconds * native_rate)
        if stream.channels not in (1, 2):
            raise ValueError("Music auditions support mono or stereo sources")
        if start_frame + count > len(stream):
            raise ValueError("Requested excerpt extends beyond the source audio")
        metadata = {"sample_rate": native_rate, "channels": stream.channels,
            "duration_seconds": len(stream) / native_rate, "format": stream.format,
            "subtype": stream.subtype, "start_frame": start_frame, "excerpt_frames": count}
        stream.seek(start_frame)
        audio = stream.read(count, always_2d=True, dtype="float64")
    if len(audio) != count or not np.isfinite(audio).all():
        raise ValueError("Decoded excerpt is incomplete or contains invalid samples")
    if native_rate != SAMPLE_RATE:
        audio = librosa.resample(audio, orig_sr=native_rate, target_sr=SAMPLE_RATE, axis=0)
    return audio, metadata
