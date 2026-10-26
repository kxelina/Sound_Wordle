"""SuperCollider rendering helpers used by the music-restoration game."""

import hashlib
import os
from pathlib import Path
import shutil
import socket

import numpy as np
import soundfile as sf

from .models import SAMPLE_RATE, bounded
from .sc_client import (ROOT, EngineError, EngineProcessError, PRE_ROLL,
                        PRE_ROLL_FRAMES, write_score, check_cancelled)


def compile_definitions(engine, stage, *, cancel_event=None):
    check_cancelled(cancel_event)
    names = ("soundDetectiveEffects", "soundDetectiveExamplePlayer")
    sources = ("synth.scd", "music_example_player.scd")
    fingerprint = hashlib.sha256(b"".join((ROOT / "supercollider" / name).read_bytes() for name in sources)
        + str(engine.sclang).encode() + str(engine.sclang.stat().st_mtime_ns).encode()).hexdigest()[:20]
    cache = {name: engine.runtime / f"music-example-{name}-{fingerprint}.scsyndef" for name in names}
    if all(path.is_file() and path.read_bytes().startswith(b"SCgf") for path in cache.values()):
        return {name: path.read_bytes() for name, path in cache.items()}
    for name in sources:
        shutil.copy2(ROOT / "supercollider" / name, stage / name)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    for attempt in range(3):
        try:
            log = engine._run([str(engine.sclang), "-D", "-u", str(port),
                str(stage / "music_example_player.scd"), "compile", str(stage)], "music-compile.log", 90,
                cancel_event=cancel_event)
            break
        except EngineProcessError as error:
            if os.name != "nt" or error.exit_code & 0xffffffff != 0xc0000008 or attempt == 2:
                raise
            shutil.copy2(engine.runtime / "music-compile.log", engine.runtime / f"music-startup-{attempt + 1}.log")
    if "SOUND_DETECTIVE_MUSIC_EXAMPLES_READY" not in log:
        raise EngineError("Music example player did not compile; inspect music-compile.log")
    definitions = {}
    for name, path in cache.items():
        data = (stage / f"{name}.scsyndef").read_bytes()
        if not data.startswith(b"SCgf"):
            raise EngineError("Invalid music example SynthDef")
        path.write_bytes(data)
        definitions[name] = data
    return definitions


def render_clip(engine, stage, definitions, mono, settings, *, playback_rate=1., filter_repair=0., cancel_event=None):
    check_cancelled(cancel_event)
    bounded("playback_rate", playback_rate, .65, 1.35)
    bounded("filter_repair", filter_repair, 0, 1)
    source = stage / "clip.wav"
    sf.write(source, mono, SAMPLE_RATE, subtype="FLOAT")
    clip_seconds = len(mono) / SAMPLE_RATE / playback_rate
    duration = min(29., settings.effects.initial_duration(settings.patch, note_off_seconds=clip_seconds))
    args = settings.synth_arguments(duration)
    controls = dict(zip(args[::2], args[1::2]))
    exclude = {f"h{i}" for i in range(1, 9)} | {"attack", "decay", "sustain", "release"}
    fx_args = [item for key, value in controls.items() if key not in exclude for item in (key, value)]
    fx_args.extend(("filterRepair", float(filter_repair)))
    while True:
        check_cancelled(cancel_event)
        # Effects must last until the current render boundary if it was extended.
        fx_args[fx_args.index("duration") + 1] = duration
        score = stage / "music.osc"
        render = stage / "music.wav"
        render.unlink(missing_ok=True)
        write_score([
            (0., [("/d_recv", [value]) for value in definitions.values()] + [("/b_allocRead", [0, str(source)])]),
            (PRE_ROLL, [("/g_new", [100, 0, 0]),
                ("/s_new", ["soundDetectiveEffects", 900, 1, 0, "in", 16, *fx_args]),
                ("/s_new", ["soundDetectiveExamplePlayer", 1000, 1, 100, "out", 16, "bufnum", 0,
                    "rateFactor", float(playback_rate)])]),
            (PRE_ROLL + duration + .01, [("/c_set", [0, 0])]),
        ], score)
        engine._run([str(engine.scsynth), "-N", str(score), "_", str(render), str(SAMPLE_RATE),
            "WAV", "float", "-o", "2", "-i", "0", "-z", "64", "-m", "65536"], "music-render.log", 90,
            cancel_event=cancel_event)
        audio, rate = sf.read(render, always_2d=True)
        count = round(duration * SAMPLE_RATE)
        if rate != SAMPLE_RATE or audio.shape[1] != 2 or len(audio) < PRE_ROLL_FRAMES + count:
            raise EngineError("Unexpected music-example render format or length")
        audio = audio[PRE_ROLL_FRAMES:PRE_ROLL_FRAMES + count].copy()
        if not np.isfinite(audio).all() or np.max(np.abs(audio)) <= 1e-10:
            raise EngineError("Music-example render is invalid or silent")
        tail_window = max(.5, settings.effects.delay.time_seconds + .05)
        tail = audio[-round(tail_window * rate):-round(.03 * rate)]
        tail_rms = float(np.sqrt(np.mean(tail ** 2)))
        if tail_rms <= max(float(np.max(np.abs(audio))) * .0001, 1e-7):
            return audio, tail_rms
        if duration >= 29.:
            raise EngineError("Music-effect tail is still active at the developer limit")
        duration = min(29., duration + 3.)


def trim_inaudible_margin(audio, source_frames):
    """Remove only the long trailing reserve, preserving a -80 dB tail +150 ms."""
    peak = float(np.max(np.abs(audio)))
    active = np.flatnonzero(np.max(np.abs(audio), axis=1) > peak * .0001)
    end = max(source_frames, int(active[-1]) + 1) + round(.15 * SAMPLE_RATE)
    return audio[:min(end, len(audio))].copy()
