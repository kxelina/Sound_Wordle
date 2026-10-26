"""Standalone entry for W02 and the free melody workshop."""

import sys
from PySide6.QtWidgets import QApplication

from .audio.sc_client import ROOT
from .game.desktop import DesktopStore
from .ui.melody import MelodyWindow
from .ui.studio import STYLE


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    preferences = DesktopStore(ROOT / "userdata/desktop-preferences.json").load()
    window = MelodyWindow(language=preferences.language, volume=preferences.volume / 100)
    window.setStyleSheet(STYLE + "\nQMainWindow, QWidget#wordle_body { background: #1e231f; }")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
