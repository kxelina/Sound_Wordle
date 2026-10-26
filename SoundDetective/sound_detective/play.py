"""Launch the detective studio: python -m sound_detective.play."""

import sys
import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--music-studio", action="store_true", help="Resume M01 in the music restoration room")
    args = parser.parse_args(argv)
    try:
        from PySide6.QtWidgets import QApplication
        from .ui.studio import StudioWindow
    except ImportError as error:
        print(f"Install requirements.txt or reinstall the packaged game: {error}", file=sys.stderr)
        return 1
    app = QApplication([sys.argv[0]])
    app.setApplicationName("Sound Detective")
    try:
        window = StudioWindow()
        if args.music_studio and not window.open_music_studio():
            window.close()
            raise ValueError("Cannot open the music restoration case; check the local audio assets")
    except (OSError, ValueError, TypeError) as error:
        print(f"Cannot load Sound Detective: {error}", file=sys.stderr)
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
