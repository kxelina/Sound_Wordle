"""Standalone shortcut for the W01 hidden-sound prototype."""

import sys
from PySide6.QtWidgets import QApplication

from .ui.hidden_sound import HiddenSoundWindow
from .ui.studio import STYLE
from .audio.sc_client import ROOT
from .game.desktop import DesktopStore


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    preferences = DesktopStore(ROOT / "userdata/desktop-preferences.json").load()
    window = HiddenSoundWindow(language=preferences.language, volume=preferences.volume / 100)
    window.setStyleSheet(STYLE + "\nQMainWindow, QWidget#wordle_body { background: #1e231f; }")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
