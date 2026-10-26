"""Serial, cancellable, cached category-source rendering on the SC backend."""

from dataclasses import dataclass
import hashlib
import json

import soundfile as sf

from .audio_output import prepare_playback
from .preview import PreviewAudio, PreviewRenderer
from .sc_client import ROOT, check_cancelled
from .sound_sources import SourcePatch, SOURCE_VERSION, measure_source


@dataclass(frozen=True)
class SourcePreviewAudio(PreviewAudio):
    measurements: dict


class SourcePreviewRenderer(PreviewRenderer):
    def prepare(self, requests):
        requests = dict(requests)
        if not requests or any(not isinstance(v, SourcePatch) for v in requests.values()):
            raise ValueError("Each category preview requires a SourcePatch")
        return self._enqueue(requests)

    def _work(self, requests, event, *unused):
        check_cancelled(event)
        if self._engine is None:
            self._engine = self._engine_factory()
        fingerprint = hashlib.sha256((ROOT/"supercollider/synth.scd").read_bytes()).hexdigest()
        result = {}
        for label, patch in requests.items():
            check_cancelled(event)
            key = hashlib.sha256(json.dumps({"patch": patch.to_dict(), "version": SOURCE_VERSION,
                "synth": fingerprint}, sort_keys=True).encode()).hexdigest()
            raw, listening = self.directory/f"{key}-raw.wav", self.directory/f"{key}-listening.wav"
            hit = key in self._cache and raw.is_file() and listening.is_file()
            try:
                if not hit:
                    self._engine.render_source(patch, raw, overwrite=True, cancel_event=event)
                    check_cancelled(event)
                audio, rate = sf.read(raw, always_2d=True)
                measurements = measure_source(audio, rate)
                if not hit:
                    sf.write(listening, prepare_playback(audio, volume=1.), rate, subtype="PCM_24")
                check_cancelled(event)
            except BaseException:
                if not hit:
                    raw.unlink(missing_ok=True)
                    listening.unlink(missing_ok=True)
                raise
            self._cache[key] = (raw, listening)
            self._cache.move_to_end(key)
            result[label] = SourcePreviewAudio(raw, listening, hit, measurements)
        while len(self._cache) > max(self._cache_limit, len(requests)):
            _, paths = self._cache.popitem(last=False)
            for path in paths:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
        return result, None
