"""Python -> OSC score -> SuperCollider NRT -> WAV.

The SC SynthDef is the only synthesizer. This blocking API can later run in a
background worker. Real-time OSC transport and device playback are future work.
"""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time

import numpy as np
import soundfile as sf
from pythonosc.osc_message_builder import OscMessageBuilder
from .models import DURATION_SECONDS, NOTE_OFF_SECONDS, SAMPLE_RATE, SoundSettings
from .sequence import REFERENCE_MIDI_PITCH, NoteEvent, NoteSequence

ROOT = Path(__file__).resolve().parents[2]
PRE_ROLL_FRAMES = 4416  # Multiple of the 64-sample server control block.
PRE_ROLL = PRE_ROLL_FRAMES / SAMPLE_RATE
MAX_DURATION = 30.0
MAX_SEQUENCE_EVENTS = 4096
MAX_VOICES = 16  # Includes notes that are still in their ADSR Release stage.
SYNTH_NAMES = ("soundDetective", "soundDetectiveVoice", "soundDetectiveEffects",
               "sdRainBed", "sdDrop", "sdChirp", "sdPluck", "sdRadio")


class EngineError(RuntimeError):
    """SC startup, compilation or rendering failed."""


class EngineProcessError(EngineError):
    """Preserve the exit status for narrowly scoped startup recovery."""

    def __init__(self, message, exit_code):
        super().__init__(message)
        self.exit_code = exit_code


class RenderCancelled(EngineError):
    """A caller cancelled the render; no final export should be published."""


def check_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise RenderCancelled("Audio generation cancelled")


def process_executable(path: str) -> str:
    """Keep bundled SC's Windows class-library lookup within short path limits.

    Do not resolve the returned alias: doing so expands it before CreateProcess.
    Volumes without short names retain the original path. File discovery and
    diagnostic reports continue to use the actual installation location.
    """
    if os.name != 'nt':
        return path
    import ctypes
    from ctypes import wintypes
    short_path = ctypes.WinDLL('kernel32', use_last_error=True).GetShortPathNameW
    short_path.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD)
    short_path.restype = wintypes.DWORD
    size = short_path(path, None, 0)
    if not size:
        return path
    buffer = ctypes.create_unicode_buffer(size)
    count = short_path(path, buffer, size)
    return buffer.value if 0 < count < size and len(buffer.value) < len(path) else path


@dataclass(frozen=True)
class RenderResult:
    path: Path
    duration: float
    sample_rate: int
    peak: float
    tail_rms: float
    peak_gain: float
    elapsed_seconds: float
    request_id: int | None = None


def find_executable(name: str, sc_directory: Path | None = None) -> Path:
    candidates = []
    configured = sc_directory or os.environ.get("SOUND_DETECTIVE_SC_DIR")
    if configured:
        path = Path(configured) / name
        if not path.is_file():
            raise FileNotFoundError(f"SuperCollider executable not found: {path}")
        return path.resolve()
    bundled = ROOT / 'engine' / 'SuperCollider' / name
    if bundled.is_file():
        return bundled.resolve()
    found = shutil.which(name)
    if found:
        return Path(found).resolve()
    for base in (Path(os.environ.get("ProgramFiles", "C:/Program Files")),
                 Path(os.environ.get("LOCALAPPDATA", "C:/Users/Default/AppData/Local")) / "Programs"):
        candidates.extend(sorted(base.glob(f"SuperCollider*/{name}"), reverse=True))
    if candidates:
        return candidates[0].resolve()
    raise FileNotFoundError("Install SuperCollider or set SOUND_DETECTIVE_SC_DIR to its installation folder")


def write_score(events: list, path: Path) -> None:
    """SC NRT files contain length-prefixed OSC bundles with relative times."""
    with path.open("wb") as file:
        for timestamp, messages in sorted(events, key=lambda event: event[0]):
            bundle = b"#bundle\0" + struct.pack(">Q", round(timestamp * (1 << 32)))
            for address, arguments in messages:
                builder = OscMessageBuilder(address=address)
                for argument in arguments:
                    builder.add_arg(argument)
                payload = builder.build().dgram
                bundle += struct.pack(">i", len(payload)) + payload
            file.write(struct.pack(">i", len(bundle)) + bundle)


class SCEngine:
    def __init__(self, sc_directory: Path | None = None, runtime_dir: Path | None = None):
        self.sclang = find_executable("sclang.exe", sc_directory)
        self.scsynth = find_executable("scsynth.exe", sc_directory)
        self.runtime = Path(runtime_dir) if runtime_dir else ROOT / ".runtime"
        self.runtime.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _run(self, command: list[str], log_name: str, timeout: float,
             cancel_event: threading.Event | None = None) -> str:
        check_cancelled(cancel_event)
        environment = os.environ.copy()
        # A headless PySide test must not select Qt's offscreen platform for
        # the separately installed Windows sclang runtime and its GUI classes.
        if os.name == "nt" and environment.get("QT_QPA_PLATFORM") == "offscreen":
            environment.pop("QT_QPA_PLATFORM")
        log_path = self.runtime / log_name
        # A file-backed log avoids anonymous pipe-reader threads. Keep a valid
        # stdin for GUI/pythonw launches, where inherited standard handles vary.
        with log_path.open("wb") as output:
            try:
                launch = [process_executable(str(command[0])), *command[1:]]
                process = subprocess.Popen(launch, cwd=Path(launch[0]).parent,
                                           stdin=subprocess.DEVNULL,
                                           stdout=output, stderr=subprocess.STDOUT,
                                           env=environment,
                                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except OSError as error:
                raise EngineError(f"Cannot start SuperCollider: {error}") from error
            deadline = time.monotonic() + timeout
            try:
                while True:
                    check_cancelled(cancel_event)
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise EngineError(f"SC timed out after {timeout:g}s during {log_name}")
                    try:
                        process.wait(timeout=min(.1, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        continue
            except BaseException:
                if process.poll() is None:
                    process.kill()
                process.wait()
                raise
        log = log_path.read_text(encoding="utf-8", errors="replace")
        check_cancelled(cancel_event)
        if process.returncode:
            raise EngineProcessError(f"SC failed (exit {process.returncode}, 0x{process.returncode & 0xffffffff:08x}); "
                                     f"see {self.runtime / log_name}\n{log[-1600:]}", process.returncode)
        return log

    def _compile(self, stage: Path, cancel_event: threading.Event | None = None) -> dict[str, bytes]:
        check_cancelled(cancel_event)
        sources = [ROOT / "supercollider" / name for name in ("synth.scd", "engine.scd")]
        fingerprint = hashlib.sha256(b"".join(p.read_bytes() for p in sources)
                                     + str(self.sclang).encode()
                                     + str(self.sclang.stat().st_mtime_ns).encode()).hexdigest()[:20]
        caches = {name: self.runtime / f"{name}-{fingerprint}.scsyndef" for name in SYNTH_NAMES}
        if all(path.is_file() and path.read_bytes().startswith(b"SCgf") for path in caches.values()):
            return {name: path.read_bytes() for name, path in caches.items()}
        for source in sources:
            shutil.copy2(source, stage / source.name)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        command = [str(self.sclang), "-D", "-u", str(port), str(stage / "engine.scd"), "compile", str(stage)]
        # Windows SC 3.14.1 can intermittently exit with STATUS_INVALID_HANDLE
        # during cold class-library startup. Only that process failure is safe
        # to retry here; cancellation, timeout, SC code errors and NRT failures
        # must propagate. Never accept definitions until the ready marker exists.
        for attempt in range(3):
            try:
                log = self._run(command, "compile.log", 90, cancel_event)
                break
            except EngineProcessError as error:
                if os.name != "nt" or (error.exit_code & 0xffffffff) != 0xc0000008 or attempt == 2:
                    raise
                shutil.copy2(self.runtime / "compile.log", self.runtime / f"compile-startup-{attempt + 1}.log")
                check_cancelled(cancel_event)
                if cancel_event is not None:
                    cancel_event.wait(.1)
                else:
                    time.sleep(.1)
                check_cancelled(cancel_event)
        definitions = {}
        for name, cache in caches.items():
            compiled = stage / f"{name}.scsyndef"
            if "SOUND_DETECTIVE_DEFS_READY" not in log or not compiled.is_file():
                raise EngineError(f"SC did not compile {name}. See {self.runtime / 'compile.log'}\n{log[-1600:]}")
            data = compiled.read_bytes()
            if not data.startswith(b"SCgf"):
                raise EngineError(f"SC wrote an invalid SynthDef: {name}")
            with tempfile.NamedTemporaryFile(dir=self.runtime, suffix=".tmp", delete=False) as tmp:
                tmp.write(data)
                temporary = Path(tmp.name)
            temporary.replace(cache)
            definitions[name] = data
        return definitions

    def render(self, settings: SoundSettings, output_path: Path, *,
               request_id: int | None = None, overwrite: bool = False,
               note: NoteEvent | None = None, cancel_event: threading.Event | None = None) -> RenderResult:
        """Render one note with its leading rest, release, and complete effects.

        Omitting note preserves the original 220 Hz / 1.20 s / full-gain tone.
        Use render_sequence for a phrase with a shared effects chain.
        """
        if note is None:
            note = NoteEvent(REFERENCE_MIDI_PITCH, 0.0, NOTE_OFF_SECONDS, 127)
        if not isinstance(note, NoteEvent):
            raise TypeError("note must be NoteEvent")
        return self._render(settings, NoteSequence((note,)), output_path,
                            request_id=request_id, overwrite=overwrite, shared_effects=False, cancel_event=cancel_event)

    def render_sequence(self, settings: SoundSettings, sequence: NoteSequence, output_path: Path, *,
                        request_id: int | None = None, overwrite: bool = False,
                        cancel_event: threading.Event | None = None) -> RenderResult:
        """Render all notes on one timeline through one shared filter/delay/reverb.

        Times are absolute seconds; rests, overlaps and note velocities are kept.
        The same patch is used for all notes. This is a blocking offline render.
        """
        return self._render(settings, sequence, output_path,
                            request_id=request_id, overwrite=overwrite, shared_effects=True, cancel_event=cancel_event)

    def render_source(self, patch, output_path, *, overwrite=False, cancel_event=None):
        """Render a procedural source through SC using the usual safe staging."""
        from .sound_sources import SourcePatch, SOURCE_DURATION, source_events
        if not isinstance(patch, SourcePatch):
            raise TypeError("Expected SourcePatch")
        check_cancelled(cancel_event)
        destination = Path(output_path).resolve()
        if destination.suffix.lower() != ".wav":
            raise ValueError("Output file must have a .wav extension")
        if destination.exists() and not overwrite:
            raise FileExistsError(str(destination))
        temp_base = os.environ.get("SOUND_DETECTIVE_TEMP")
        if temp_base:
            Path(temp_base).mkdir(parents=True, exist_ok=True)
        with self._lock, tempfile.TemporaryDirectory(prefix="sd-source-", dir=temp_base) as temporary:
            stage = Path(temporary)
            if not str(stage).isascii():
                raise EngineError("Set SOUND_DETECTIVE_TEMP to a writable ASCII-only temporary folder")
            definitions = self._compile(stage, cancel_event)
            nodes = source_events(patch)
            events = [(0., [("/d_recv", [definitions[name]]) for name in sorted({n[1] for n in nodes})])]
            for index, (at, name, controls) in enumerate(nodes):
                arguments = [item for key, value in controls.items() for item in (key, value)]
                events.append((PRE_ROLL+at, [("/s_new", [name, 1000+index, 0, 0, *arguments])]))
            events.append((PRE_ROLL+SOURCE_DURATION+.01, [("/c_set", [0, 0])]))
            score, render = stage/"source.osc", stage/"source.wav"
            write_score(events, score)
            self._run([str(self.scsynth), "-N", str(score), "_", str(render), str(SAMPLE_RATE),
                       "WAV", "float", "-o", "2", "-i", "0", "-z", "64", "-m", "65536"],
                      "source-render.log", 60, cancel_event)
            if not render.is_file():
                raise EngineError("SC did not create the procedural audio")
            audio, rate = sf.read(render, always_2d=True)
            end = PRE_ROLL_FRAMES + round(SOURCE_DURATION*SAMPLE_RATE)
            if rate != SAMPLE_RATE or audio.shape[1] != 2 or len(audio) < end:
                raise EngineError("Unexpected procedural audio format")
            audio = audio[PRE_ROLL_FRAMES:end].copy()
            if not np.isfinite(audio).all() or np.max(np.abs(audio)) < 1e-10:
                raise EngineError("Procedural source returned invalid or silent audio")
            audio *= min(1., .9 / float(np.max(np.abs(audio))))
            check_cancelled(cancel_event)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".wav", delete=False) as file:
                export = Path(file.name)
            try:
                sf.write(export, audio, SAMPLE_RATE, subtype="PCM_24")
                check_cancelled(cancel_event)
                if not overwrite and destination.exists():
                    raise FileExistsError(str(destination))
                export.replace(destination)
            finally:
                export.unlink(missing_ok=True)
        return destination

    def _render(self, settings: SoundSettings, sequence: NoteSequence, output_path: Path, *,
                request_id: int | None, overwrite: bool, shared_effects: bool,
                cancel_event: threading.Event | None) -> RenderResult:
        check_cancelled(cancel_event)
        if not isinstance(settings, SoundSettings):
            raise TypeError("settings must be SoundSettings")
        if not isinstance(sequence, NoteSequence):
            raise TypeError("sequence must be NoteSequence")
        if not sequence.events:
            raise ValueError("Sequence has no notes to render")
        if len(sequence.events) > MAX_SEQUENCE_EVENTS:
            raise ValueError(f"Sequence exceeds the {MAX_SEQUENCE_EVENTS}-event render limit")
        if settings.patch.is_silent:
            raise ValueError("Current sound is silent: raise at least one harmonic")
        changes = []
        for index, note in enumerate(sequence.events):
            if note.duration_seconds < 1 / SAMPLE_RATE:
                raise ValueError(f"Note {index} duration must be at least one output sample")
            if not any(amplitude > 0 and harmonic * note.frequency_hz < SAMPLE_RATE / 2
                       for harmonic, amplitude in enumerate(settings.patch.harmonics, 1)):
                raise ValueError(f"Current sound is silent at note {index}: all active harmonics reach or exceed Nyquist")
            changes.extend(((round(note.start_seconds * SAMPLE_RATE), 1),
                            (round((note.end_seconds + settings.patch.release) * SAMPLE_RATE), -1)))
        active = 0
        for _, delta in sorted(changes):  # At a boundary, release finishes before a new note starts.
            active += delta
            if active > MAX_VOICES:
                raise ValueError(f"Sequence exceeds {MAX_VOICES} simultaneous voices including Release")
        minimum_duration = max(DURATION_SECONDS, sequence.duration_seconds + settings.patch.release + 0.20)
        if minimum_duration > MAX_DURATION:
            raise ValueError("Note timing and release must leave a silent margin within the 30-second render limit")
        destination = Path(output_path).resolve()
        if destination.suffix.lower() != ".wav":
            raise ValueError("Output file must have a .wav extension")
        if destination.exists() and not overwrite:
            raise FileExistsError(f"Output already exists: {destination}")
        started = time.perf_counter()
        # SC receives ASCII staging paths; Python handles the user's Unicode path.
        temp_base = os.environ.get("SOUND_DETECTIVE_TEMP")
        if temp_base:
            Path(temp_base).mkdir(parents=True, exist_ok=True)
        with self._lock, tempfile.TemporaryDirectory(prefix="sound-detective-", dir=temp_base) as temporary:
            stage = Path(temporary)
            if not str(stage).isascii():
                raise EngineError("Set SOUND_DETECTIVE_TEMP to a writable ASCII-only temporary folder")
            definitions = self._compile(stage, cancel_event)
            duration = min(MAX_DURATION, settings.effects.initial_duration(
                settings.patch, note_off_seconds=sequence.duration_seconds))
            while True:
                check_cancelled(cancel_event)
                audio, tail_rms = self._render_once(settings, definitions, stage, duration, sequence, shared_effects, cancel_event)
                peak = float(np.max(np.abs(audio)))
                # Measure before the 20 ms ending fade, so a fade cannot conceal a tail.
                if tail_rms <= max(peak * 0.0001, 1e-7):
                    break
                if duration >= MAX_DURATION:
                    raise EngineError("Effect tail exceeds the silence threshold at the 30-second render limit")
                duration = min(MAX_DURATION, duration + max(3.0, duration * 0.5))
            if peak < 1e-10:
                raise EngineError("SC returned silence for a non-silent patch")
            peak_gain = min(1.0, 0.9 / peak)
            audio *= peak_gain  # Constant gain, never hard clipping.
            check_cancelled(cancel_event)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".wav", delete=False) as tmp:
                export = Path(tmp.name)
            try:
                sf.write(export, audio, SAMPLE_RATE, subtype="PCM_24")
                check_cancelled(cancel_event)
                if not overwrite and destination.exists():
                    raise FileExistsError(f"Output already exists: {destination}")
                export.replace(destination)
            finally:
                export.unlink(missing_ok=True)
        return RenderResult(destination, len(audio)/SAMPLE_RATE, SAMPLE_RATE,
                            float(np.max(np.abs(audio))), tail_rms*peak_gain, peak_gain,
                            time.perf_counter()-started, request_id)

    def _render_once(self, settings: SoundSettings, definitions: dict[str, bytes], stage: Path,
                     duration: float, sequence: NoteSequence, shared_effects: bool,
                     cancel_event: threading.Event | None = None) -> tuple[np.ndarray, float]:
        score = stage / "score.osc"
        render = stage / "render.wav"
        render.unlink(missing_ok=True)
        if shared_effects:
            all_args = settings.synth_arguments(duration)
            controls = dict(zip(all_args[::2], all_args[1::2]))
            voice_controls = {f"h{i}" for i in range(1, 9)} | {"attack", "decay", "sustain", "release"}
            voice_args = [item for name, value in controls.items() if name in voice_controls for item in (name, value)]
            fx_args = [item for name, value in controls.items() if name not in voice_controls for item in (name, value)]
            events = [
                (0.0, [("/d_recv", [definitions[name]]) for name in SYNTH_NAMES[1:3]]),
                (PRE_ROLL, [("/g_new", [100, 0, 0]),
                            ("/s_new", ["soundDetectiveEffects", 900, 1, 0, "in", 16, *fx_args])]),
            ]
            for index, note in enumerate(sequence.events):
                events.append((PRE_ROLL + note.start_seconds, [("/s_new", [
                    "soundDetectiveVoice", 1000 + index, 1, 100, "out", 16, *voice_args,
                    "freq", note.frequency_hz, "noteOff", note.duration_seconds, "velocity", note.velocity_gain])]))
        else:
            note = sequence.events[0]
            events = [
                (0.0, [("/d_recv", [definitions["soundDetective"]])]),
                (PRE_ROLL + note.start_seconds, [("/s_new", ["soundDetective", 1000, 0, 0,
                    *settings.synth_arguments(duration - note.start_seconds),
                    "freq", note.frequency_hz, "noteOff", note.duration_seconds,
                    "velocity", note.velocity_gain])]),
            ]
        events.append((PRE_ROLL + duration + 0.01, [("/c_set", [0, 0])]))
        write_score(events, score)
        self._run([str(self.scsynth), "-N", str(score), "_", str(render), str(SAMPLE_RATE),
                   "WAV", "float", "-o", "2", "-i", "0", "-z", "64", "-m", "65536"],
                  "render.log", max(60, duration*4), cancel_event)
        if not render.is_file():
            raise EngineError("SC did not create a WAV; inspect .runtime/render.log")
        audio, rate = sf.read(render, always_2d=True, dtype="float64")
        count = round(duration*SAMPLE_RATE)
        if rate != SAMPLE_RATE or audio.shape[1] != 2 or len(audio) < PRE_ROLL_FRAMES + count:
            raise EngineError("SC returned an unexpected audio format or duration")
        audio = audio[PRE_ROLL_FRAMES:PRE_ROLL_FRAMES+count].copy()
        if not np.isfinite(audio).all():
            raise EngineError("SC returned non-finite audio samples")
        # Cover at least one echo interval; otherwise a gap between echoes could
        # incorrectly look like a finished tail. Dry sounds can end at 2.40 s.
        window = 0.12
        if not settings.effects.bypass:
            if settings.effects.delay.active:
                window = max(window, settings.effects.delay.time_seconds + 0.05)
            if settings.effects.reverb.active:
                window = max(window, 0.5)
        tail = audio[-round(window*SAMPLE_RATE):-round(0.03*SAMPLE_RATE)]
        return audio, float(np.sqrt(np.mean(tail**2)))


def request_render(parameters: dict | SoundSettings, output_path: Path,
                   request_id: int = 0, *, overwrite: bool = False,
                   note: NoteEvent | None = None, cancel_event: threading.Event | None = None) -> RenderResult:
    """同步完成后才返回；request_id 用于调用方识别对应的参数版本。"""
    settings = parameters if isinstance(parameters, SoundSettings) else SoundSettings.from_dict(parameters)
    return SCEngine().render(settings, output_path, request_id=request_id, overwrite=overwrite,
                             note=note, cancel_event=cancel_event)
