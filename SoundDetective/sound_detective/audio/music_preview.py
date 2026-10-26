"""Background, cancellable reconstruction of configured music evidence."""

from collections import OrderedDict
from concurrent.futures import CancelledError, ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading

import numpy as np
import soundfile as sf
from PySide6.QtCore import QObject, Qt, Signal

from .audio_output import prepare_playback
from .models import SAMPLE_RATE, SoundSettings
from .pitch_corruption import detune_regions
from .preview import PreviewAudio
from .sc_client import ROOT, RenderCancelled, SCEngine, check_cancelled
from ..game.music_cases import MusicSettings
from ..game.music_repair import REPAIR_VERSION, remaining_effects
from .music_render import compile_definitions, render_clip, trim_inaudible_margin


class MusicPreviewRenderer(QObject):
    ready = Signal(int, object)
    failed = Signal(int, str)
    _completed = Signal(int, object, object)

    def __init__(self, parent=None, *, cache_parent=None, engine_factory=None):
        super().__init__(parent)
        directory = Path(cache_parent or ROOT / ".runtime")
        directory.mkdir(parents=True, exist_ok=True)
        self._temporary = tempfile.TemporaryDirectory(prefix="music-preview-", dir=directory, ignore_cleanup_errors=True)
        self.directory = Path(self._temporary.name)
        self._factory = engine_factory or (lambda: SCEngine(runtime_dir=self.directory / "engine"))
        self._engine = None
        self._cache = OrderedDict()
        self._pitches = OrderedDict()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="music-preview")
        self._event = None
        self._futures = set()
        self._lock = threading.Lock()
        self._closed = False
        self.revision = 0
        self._completed.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    def cancel(self):
        self.revision += 1
        if self._event is not None:
            self._event.set()

    def prepare(self, case, settings, *, region_index=None, selection=None):
        if self._closed:
            raise RuntimeError("Music renderer is closed")
        if not isinstance(settings, MusicSettings):
            raise TypeError("Expected music reconstruction settings")
        settings.validate(case)
        if region_index is not None and (type(region_index) is not int or not 0 <= region_index < len(case.regions)):
            raise ValueError("Invalid pitch-monitor region")
        if selection is not None:
            if (len(selection) != 2 or not all(isinstance(v, (int, float)) and np.isfinite(v) for v in selection)
                    or not 0 <= selection[0] < selection[1] <= case.seconds or selection[1]-selection[0] < .1):
                raise ValueError('Choose at least 0.1 seconds inside the excerpt')
        self.cancel()
        revision, event = self.revision, threading.Event()
        self._event = event
        future = self._executor.submit(self._audition_work, case, settings, event, region_index, selection)
        with self._lock:
            self._futures.add(future)

        def done(task):
            try:
                try:
                    result, error = task.result(), None
                except (CancelledError, RenderCancelled):
                    return
                except Exception as caught:
                    result, error = None, str(caught)
                if not self._closed:
                    self._completed.emit(revision, result, error)
            finally:
                with self._lock:
                    self._futures.discard(task)
                    cleanup = self._closed and not self._futures
                if cleanup:
                    self._temporary.cleanup()
        future.add_done_callback(done)
        return revision

    def _audition_work(self, case, settings, event, region_index, selection):
        preview = self._work(case, settings, event, region_index)
        if selection is None or region_index is not None:
            return preview
        check_cancelled(event)
        key = hashlib.sha256(f'{preview.listening_path}:{selection}'.encode()).hexdigest()
        path = self.directory / f'{key}-selection.wav'
        if path.is_file():
            return PreviewAudio(path, path, True)
        with sf.SoundFile(preview.listening_path) as source:
            source.seek(round(selection[0]*source.samplerate))
            audio = source.read(round((selection[1]-selection[0])*source.samplerate), always_2d=True)
            rate = source.samplerate
        edge = min(round(.008*rate), len(audio)//2)
        if edge:
            audio[:edge] *= np.linspace(0, 1, edge)[:, None]
            audio[-edge:] *= np.linspace(1, 0, edge)[:, None]
        check_cancelled(event)
        sf.write(path, audio, rate, subtype='PCM_24')
        return PreviewAudio(path, path, preview.cache_hit)

    def _deliver(self, revision, result, error):
        if self._closed or revision != self.revision:
            return
        if error is not None:
            self.failed.emit(revision, error)
        else:
            self.ready.emit(revision, result)

    def _work(self, case, settings, event, region_index=None):
        check_cancelled(event)
        if region_index is not None:
            return self._region_work(case, settings, event, region_index)
        recipe = remaining_effects(case.initial_effects, settings.repair)
        if (all(region.cents == original.cents for region, original in zip(settings.residual_regions(case), case.regions))
                and recipe.effects == case.initial_effects and recipe.filter_repair == 0):
            # The accepted audition plays immediately, even on a cold start.
            return PreviewAudio(case.evidence, case.evidence, True)
        fingerprint = hashlib.sha256(b"".join((ROOT / "supercollider" / name).read_bytes()
            for name in ("synth.scd", "music_example_player.scd"))).hexdigest()
        key = hashlib.sha256(json.dumps({"version": REPAIR_VERSION, "case": case.fingerprint,
            "settings": settings.to_dict(), "sc": fingerprint}, sort_keys=True).encode()).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            raw, listening = self._cache[key]
            return PreviewAudio(raw, listening, True)

        pitch_key = (case.fingerprint, tuple(region.cents for region in settings.residual_regions(case)))
        if pitch_key not in self._pitches:
            # Import the optional decoder/resampler only in this worker.
            from .music_source import load_excerpt
            audio, _ = load_excerpt(case.source, start_seconds=case.start_seconds, seconds=case.seconds)
            mono = audio.mean(axis=1)
            edge = round(.01 * SAMPLE_RATE)
            mono[:edge] *= np.linspace(0, 1, edge)
            mono[-edge:] *= np.linspace(1, 0, edge)
            check_cancelled(event)
            processed = detune_regions(mono, settings.residual_regions(case), cancel_event=event)
            check_cancelled(event)
            self._pitches[pitch_key] = processed
        self._pitches.move_to_end(pitch_key)
        while len(self._pitches) > 4:
            self._pitches.popitem(last=False)
        processed = self._pitches[pitch_key]
        check_cancelled(event)
        if self._engine is None:
            self._engine = self._factory()
        staging = os.environ.get("SOUND_DETECTIVE_TEMP", tempfile.gettempdir())
        if not str(staging).isascii():
            raise ValueError("Set SOUND_DETECTIVE_TEMP to an ASCII-only temporary folder")
        with tempfile.TemporaryDirectory(prefix="sd-music-game-", dir=staging) as temporary:
            stage = Path(temporary)
            definitions = compile_definitions(self._engine, stage, cancel_event=event)
            audio, _ = render_clip(self._engine, stage, definitions, processed,
                SoundSettings(effects=recipe.effects), filter_repair=recipe.filter_repair, cancel_event=event)
        check_cancelled(event)
        audio = trim_inaudible_margin(audio, len(processed))
        edge = round(.02 * SAMPLE_RATE)
        audio[-edge:] *= np.linspace(1, 0, edge)[:, None]
        audio = np.pad(audio, ((0, round(.06 * SAMPLE_RATE)), (0, 0)))
        raw, listening = self.directory / f"{key}-raw.wav", self.directory / f"{key}-listen.wav"
        try:
            sf.write(raw, audio, SAMPLE_RATE, subtype="FLOAT")
            sf.write(listening, prepare_playback(audio, volume=.75, target_rms=.085, peak_limit=.85),
                     SAMPLE_RATE, subtype="PCM_24")
            check_cancelled(event)
        except BaseException:
            raw.unlink(missing_ok=True)
            listening.unlink(missing_ok=True)
            raise
        self._cache[key] = (raw, listening)
        while len(self._cache) > 8:
            _, paths = self._cache.popitem(last=False)
            for path in paths:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
        return PreviewAudio(raw, listening, False)

    def _region_work(self, case, settings, event, index):
        """Dry focus monitor, never an unmodified target/reference preview."""
        from .music_source import load_excerpt
        region = settings.residual_regions(case)[index]
        key = hashlib.sha256(json.dumps({"version": REPAIR_VERSION, "case": case.fingerprint,
            "monitor": index, "cents": region.cents}, sort_keys=True).encode()).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            return PreviewAudio(*self._cache[key], True)
        audio, _ = load_excerpt(case.source, start_seconds=case.start_seconds, seconds=case.seconds)
        mono = detune_regions(audio.mean(axis=1), (region,), cancel_event=event)
        start = max(0, round((region.start_seconds-.12)*SAMPLE_RATE))
        stop = min(len(mono), round((region.end_seconds+.12)*SAMPLE_RATE))
        clip = mono[start:stop].copy()
        edge = min(round(.01*SAMPLE_RATE), len(clip)//2)
        clip[:edge] *= np.linspace(0, 1, edge)
        clip[-edge:] *= np.linspace(1, 0, edge)
        stereo = np.repeat(clip[:, None], 2, axis=1)
        raw, listening = self.directory / f"{key}-raw.wav", self.directory / f"{key}-listen.wav"
        try:
            check_cancelled(event)
            sf.write(raw, stereo, SAMPLE_RATE, subtype="FLOAT")
            sf.write(listening, prepare_playback(stereo, volume=.75, target_rms=.085, peak_limit=.85), SAMPLE_RATE, subtype="PCM_24")
            check_cancelled(event)
        except BaseException:
            raw.unlink(missing_ok=True)
            listening.unlink(missing_ok=True)
            raise
        self._cache[key] = (raw, listening)
        while len(self._cache) > 8:
            _, paths = self._cache.popitem(last=False)
            for path in paths:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
        return PreviewAudio(raw, listening, False)

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
        with self._lock:
            cleanup = not self._futures
        if cleanup:
            self._temporary.cleanup()
