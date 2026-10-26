"""Console-free desktop entry and isolated checks used by SoundDetective.exe."""

import argparse
import json
import os
from pathlib import Path
import sys
import traceback


def check_environment():
    import librosa
    import numpy
    import scipy
    import soundfile
    import pythonosc
    from PySide6 import __version__ as qt_version
    from PySide6 import QtMultimedia  # Include the actual native playback module.
    from .audio.sc_client import ROOT, find_executable
    from .game.cases import load_campaign
    from .game.availability import music_availability
    from .ui.studio_scenes import SCENES

    for filename in {name for scene in SCENES.values() for name in (scene.room_art, scene.desk_art)}:
        if not (ROOT/"assets/ui"/filename).is_file():
            raise FileNotFoundError(f"Required scene artwork is missing: {filename}")
    if not (ROOT/"assets/audio/ui-click.wav").is_file():
        raise FileNotFoundError("The UI click sound is missing")
    cases = load_campaign()
    from .game.melody import load_melody_cases
    melodies=load_melody_cases()
    from .game.sound_categories import load_source_cases
    source_cases = load_source_cases()
    music = music_availability()
    return {"project": str(ROOT), "python": sys.version.split()[0], "python_executable": sys.executable,
            "pyside": qt_version, "timbre_cases": len(cases), "music_case": music.case_id if music.available else None,
            "optional_music": music.to_dict(), "category_cases": len(source_cases),"melody_cases":len(melodies),
            "supercollider": {name: str(find_executable(name)) for name in ("sclang.exe", "scsynth.exe")}}


def smoke_test(music):
    # Only the explicit developer check uses offscreen widgets, muted audio and
    # temporary progress. The normal EXE delegates unchanged to play.main().
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["SOUND_DETECTIVE_UI_AUDIO"] = "0"
    from tempfile import TemporaryDirectory
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from .audio.sc_client import ROOT
    from .ui.studio import StudioWindow

    app = QApplication([sys.argv[0]])
    app.setQuitOnLastWindowClosed(True)
    directory = ROOT/".runtime/launcher"
    directory.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="exe-check-", dir=directory) as temporary:
        window = StudioWindow(progress_dir=Path(temporary), animation_ms=0)
        window.volume_slider.setValue(0)
        if music and not window.open_music_studio():
            window.close()
            raise RuntimeError("The music studio could not be opened")
        window.show()
        app.processEvents()
        state = {"page": window.page, "scene": window.scene_key, "visible": window.isVisible(),
                 "language": window.language, "isolated_progress": True}
        assert state["page"] == ("room" if music else "menu")
        QTimer.singleShot(500, window.close)
        code = app.exec()
        if not window._closed:
            window.close()
        if code:
            raise RuntimeError(f"Startup check event loop exited with {code}")
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--music-studio", action="store_true")
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument("--check", action="store_true", help="Check dependencies, engine and game assets")
    checks.add_argument("--smoke-test", action="store_true", help="Check actual GUI startup without user saves or speaker output")
    checks.add_argument('--diagnose', action='store_true', help='Write an actionable JSON diagnostic report')
    checks.add_argument('--diagnostics', action='store_true', help='Open startup diagnostics')
    args = parser.parse_args(argv)
    try:
        from .diagnostics import collect_diagnostics, save_report
        if args.diagnose or args.diagnostics:
            if args.diagnostics:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance() or QApplication([sys.argv[0]])
            report = collect_diagnostics(probe_audio=args.diagnostics)
            directory = Path(__file__).resolve().parents[1]/'.runtime'
            directory.mkdir(parents=True, exist_ok=True)
            save_report(report, directory/'diagnostics-latest.json')
            if args.diagnostics:
                from PySide6.QtWidgets import QApplication
                from .ui.diagnostics import DiagnosticsDialog
                app = QApplication.instance() or QApplication([sys.argv[0]])
                DiagnosticsDialog(report=report).exec()
            else:
                print(json.dumps(report, ensure_ascii=False), flush=True)
            return 0 if report['ok'] else 1
        if args.check or args.smoke_test:
            report = check_environment()
            if args.smoke_test:
                report["ui"] = smoke_test(args.music_studio)
            print(json.dumps(report, ensure_ascii=False), flush=True)
            print("SOUND_DETECTIVE_LAUNCH_CHECK_OK", flush=True)
            return 0
        report = collect_diagnostics(probe_audio=False)
        if not report['ok']:
            from PySide6.QtWidgets import QApplication
            from .ui.diagnostics import DiagnosticsDialog
            app = QApplication.instance() or QApplication([sys.argv[0]])
            DiagnosticsDialog(report=report).exec()
            return 1
        from .play import main as play
        return play(["--music-studio"] if args.music_studio else [])
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
