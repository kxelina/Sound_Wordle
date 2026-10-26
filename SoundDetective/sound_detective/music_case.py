"""Launch the configured music investigation: python -m sound_detective.music_case."""

import sys


def main():
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        from .ui.music_case import MusicCaseWindow
    except ImportError as error:
        print(f"Install requirements-music-case.txt: {error}", file=sys.stderr)
        return 1
    app = QApplication(sys.argv)
    app.setApplicationName("Sound Detective")
    try:
        window = MusicCaseWindow()
    except (OSError, ValueError, TypeError, KeyError) as error:
        QMessageBox.critical(None, "Sound Detective — Music case", str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
