"""Cancellable serial SC work, session cache and stale-result filtering."""

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, CancelledError
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
import threading

import soundfile as sf
from PySide6.QtCore import QObject, Qt, Signal

from .audio_output import prepare_playback
from .models import SoundSettings,bounded
from .matching import MatchConfig, compare_files
from .clue_features import DiagnosticContext
from .sc_client import ROOT, RenderCancelled, SCEngine, check_cancelled
from .sequence import NoteSequence


@dataclass(frozen=True)
class PreviewAudio:
    raw_path: Path
    listening_path: Path
    cache_hit: bool


class PreviewRenderer(QObject):
    ready = Signal(int, object)
    matched = Signal(int, object)
    failed = Signal(int, str)
    _completed = Signal(int, object, object)

    def __init__(self, parent=None, *, cache_parent=None, engine_factory=None, cache_limit=16):
        super().__init__(parent)
        parent_path = Path(cache_parent) if cache_parent is not None else ROOT / ".runtime"
        parent_path.mkdir(parents=True, exist_ok=True)
        self._temporary = tempfile.TemporaryDirectory(prefix="preview-", dir=parent_path, ignore_cleanup_errors=True)
        self.directory = Path(self._temporary.name)
        self._engine_factory = engine_factory or (lambda: SCEngine(runtime_dir=self.directory / "engine"))
        self._engine = None
        self._cache = OrderedDict()
        self._cache_limit = cache_limit
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sound-preview")
        self._event = None
        self._future = None
        self._futures = set()
        self._futures_lock = threading.Lock()
        self.revision = 0
        self._closed = False
        self._completed.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    def cancel(self):
        self.revision += 1
        if self._event is not None:
            self._event.set()
        if self._future is not None:
            self._future.cancel()

    def prepare(self, requests, *, match=False, comparison_config=None, diagnostic_context=None,playback_rms=.1):
        if self._closed:
            raise RuntimeError("PreviewRenderer is closed")
        bounded('playback_rms',playback_rms,.001,.25)
        requests = dict(requests)
        if not requests:
            raise ValueError("No preview requests")
        if match and set(requests) != {"a", "b"}:
            raise ValueError("Comparison requires target 'a' and current 'b'")
        if comparison_config is not None and (not match or not isinstance(comparison_config, MatchConfig)):
            raise ValueError("comparison_config requires a comparison and MatchConfig")
        if diagnostic_context is not None and (not match or not isinstance(diagnostic_context, DiagnosticContext)):
            raise ValueError("diagnostic_context requires a comparison and DiagnosticContext")
        for settings, sequence in requests.values():
            if not isinstance(settings, SoundSettings) or not isinstance(sequence, NoteSequence):
                raise TypeError("Each preview requires SoundSettings and NoteSequence")
        return self._enqueue(requests, match, comparison_config, diagnostic_context,playback_rms)

    def _enqueue(self, requests, match=False, comparison_config=None, diagnostic_context=None,playback_rms=.1):
        """Shared cancellation and delivery lifecycle for different source types."""
        if self._closed:
            raise RuntimeError("PreviewRenderer is closed")
        self.cancel()
        revision = self.revision
        event = threading.Event()
        self._event = event
        future = self._executor.submit(self._work, requests, event, match, comparison_config, diagnostic_context,playback_rms)
        self._future = future
        with self._futures_lock:
            self._futures.add(future)

        def complete(done):
            try:
                try:
                    result, error = done.result(), None
                except (CancelledError, RenderCancelled):
                    return
                except Exception as caught:
                    result, error = None, str(caught)
                if not self._closed:
                    self._completed.emit(revision, result, error)
            finally:
                with self._futures_lock:
                    self._futures.discard(done)
                    cleanup = self._closed and not self._futures
                if cleanup:
                    self._temporary.cleanup()
        future.add_done_callback(complete)
        return revision

    def _deliver(self, revision, result, error):
        if not self._closed and revision == self.revision:
            if error is None:
                previews, comparison = result
                self.ready.emit(revision, previews)
                # A ready handler may itself stop/replace the request.
                if comparison is not None and not self._closed and revision == self.revision:
                    self.matched.emit(revision, comparison)
            else:
                self.failed.emit(revision, error)

    def _work(self, requests, event, match=False, comparison_config=None, diagnostic_context=None,playback_rms=.1):
        check_cancelled(event)
        if self._engine is None:
            self._engine = self._engine_factory()
        fingerprint = hashlib.sha256(b"".join(
            (ROOT / "supercollider" / name).read_bytes() for name in ("synth.scd", "engine.scd")
        )).hexdigest()
        result = {}
        for label, (settings, sequence) in requests.items():
            check_cancelled(event)
            payload = {"version": "preview-rms-v1", "settings": settings.to_dict(),
                       "sequence": sequence.to_dict(), "sc_source": fingerprint,"playback_rms":playback_rms}
            key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
            raw = self.directory / f"{key}-raw.wav"
            listening = self.directory / f"{key}-listening.wav"
            hit = key in self._cache and raw.is_file() and listening.is_file()
            if not hit:
                try:
                    self._engine.render_sequence(settings, sequence, raw, cancel_event=event, overwrite=True)
                    check_cancelled(event)
                    data, rate = sf.read(raw, always_2d=True)
                    # One normalized copy at full gain; user volume is applied by the device.
                    prepared = prepare_playback(data, volume=1.,target_rms=playback_rms)
                    sf.write(listening, prepared, rate, subtype="PCM_24")
                    check_cancelled(event)
                except BaseException:
                    raw.unlink(missing_ok=True)
                    listening.unlink(missing_ok=True)
                    raise
                self._cache[key] = (raw, listening)
            self._cache.move_to_end(key)
            result[label] = PreviewAudio(raw, listening, hit)
        while len(self._cache) > max(self._cache_limit, len(requests)):
            _, obsolete = self._cache.popitem(last=False)
            for path in obsolete:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass  # An open device handle may delay deletion until session cleanup.
        check_cancelled(event)
        options = {"config": comparison_config}
        if diagnostic_context is not None:
            options["context"] = diagnostic_context
        comparison = compare_files(result["a"].raw_path, result["b"].raw_path, **options) if match else None
        check_cancelled(event)
        return result, comparison

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
        with self._futures_lock:
            cleanup = not self._futures
        if cleanup:
            self._temporary.cleanup()
