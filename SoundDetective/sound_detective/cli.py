"""命令行生成音频，验证声音机制；不启动游戏界面。"""
import argparse
import json
from pathlib import Path
import sys

from .audio.models import NOTE_OFF_SECONDS, SoundSettings
from .audio.sc_client import EngineError, SCEngine
from .audio.sequence import REFERENCE_MIDI_PITCH, NoteEvent, NoteSequence


def main() -> int:
    parser = argparse.ArgumentParser(description="Sound Detective - render with SuperCollider")
    parser.add_argument("--settings", type=Path, help="JSON settings; omitted means a pure tone")
    parser.add_argument("--output", type=Path, default=Path("output/sound.wav"))
    parser.add_argument("--sc-dir", type=Path, help="SuperCollider installation directory")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--sequence", type=Path, help="NoteSequence JSON; renders a phrase with shared effects")
    parser.add_argument("--pitch", type=int, help="Single-note MIDI pitch 0-127; default 57 (220 Hz)")
    parser.add_argument("--note-duration", type=float, help="Single-note seconds held before release; default 1.20")
    parser.add_argument("--start-seconds", type=float, help="Single-note leading silence in seconds; default 0")
    parser.add_argument("--velocity", type=int, help="Single-note MIDI velocity 1-127; default full gain (127)")
    args = parser.parse_args()
    if args.sequence is not None and any(value is not None for value in
            (args.pitch, args.note_duration, args.start_seconds, args.velocity)):
        parser.error("--sequence cannot be combined with single-note options")
    try:
        settings = SoundSettings.from_dict(json.loads(args.settings.read_text(encoding="utf-8-sig"))) if args.settings else SoundSettings()
        if args.sequence is not None:
            sequence = NoteSequence.from_dict(json.loads(args.sequence.read_text(encoding="utf-8-sig")))
            result = SCEngine(args.sc_dir).render_sequence(settings, sequence, args.output, overwrite=args.overwrite)
        else:
            note = NoteEvent(
                args.pitch if args.pitch is not None else REFERENCE_MIDI_PITCH,
                args.start_seconds if args.start_seconds is not None else 0.0,
                args.note_duration if args.note_duration is not None else NOTE_OFF_SECONDS,
                args.velocity if args.velocity is not None else 127,
            )
            result = SCEngine(args.sc_dir).render(settings, args.output, overwrite=args.overwrite, note=note)
    except (OSError, ValueError, TypeError, EngineError) as error:
        print(f"Sound Detective: {error}", file=sys.stderr)
        return 1
    print(f"WAV: {result.path}")
    print(f"{result.sample_rate} Hz, stereo, {result.duration:.3f} s, peak {result.peak:.4f}")
    print(f"Render time: {result.elapsed_seconds:.3f} s; tail RMS: {result.tail_rms:.8f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
