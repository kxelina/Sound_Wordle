"""One preloaded UI click voice, separate from scored/preview audio.

The bus lives for the QApplication, including while cases are switched. It
never modifies a patch or WAV used for scoring. Rendered playback waits for
the small UI cue, rather than mixing it into the start of the target.
"""

import math
import os
from pathlib import Path
import time
import wave

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QMediaDevices, QSoundEffect
from PySide6.QtWidgets import QApplication

from .models import bounded
from .sc_client import ROOT

CUE_PATH = ROOT / "assets/audio/ui-click.wav"
UI_GAIN = .65


class UiSoundBus(QObject):
    def __init__(self, parent=None, *, path=CUE_PATH, effect=None, devices=None, enabled=None, clock=time.monotonic):
        super().__init__(parent)
        self.enabled = os.environ.get("SOUND_DETECTIVE_UI_AUDIO", "1") != "0" if enabled is None else enabled
        self._clock = clock
        self._until = 0.
        self._last_role, self._last_at = None, -math.inf
        self.duration_seconds = 0.
        self._effect = self._devices = None
        if not self.enabled:
            return
        try:
            with wave.open(str(path), "rb") as cue:
                self.duration_seconds = cue.getnframes() / cue.getframerate()
            self._effect = effect if effect is not None else QSoundEffect(self)
            self._devices = devices if devices is not None else QMediaDevices(self)
            self._devices.audioOutputsChanged.connect(self._device_changed)
            self._effect.setLoopCount(1)
            self._effect.setVolume(0)
            self._device_changed()
            self._effect.setSource(QUrl.fromLocalFile(str(Path(path).resolve())))
        except (OSError, ValueError, RuntimeError, wave.Error):
            self.enabled = False  # A missing UI cue must not prevent gameplay.

    def _device_changed(self):
        self.stop()
        if self._effect is not None:
            self._effect.setAudioDevice(self._devices.defaultAudioOutput())

    @property
    def ready(self):
        return bool(self.enabled and self._effect is not None and
                    self._effect.status() == QSoundEffect.Status.Ready and
                    not self._devices.defaultAudioOutput().isNull())

    def play_click(self, role, volume=.35):
        bounded("UI volume", volume, 0, 1)
        if not self.ready or volume == 0:
            return False
        now = self._clock()
        # The cassette forwards its click to the current-play button. Both
        # share a role, so this produces one cue, without delaying the action.
        if role == self._last_role and now - self._last_at < .035:
            return False
        self._last_role, self._last_at = role, now
        self._effect.stop()
        self.set_volume(volume)
        self._effect.play()
        self._until = now + self.duration_seconds
        return True

    def remaining_ms(self):
        if not self.enabled or self._effect is None or not self._effect.isPlaying():
            return 0
        now = self._clock()
        if now > self._until + .25:
            self.stop()  # A broken output backend must not block previews.
            return 0
        return max(10, math.ceil((self._until - now) * 1000))

    def set_volume(self, volume):
        bounded("UI volume", volume, 0, 1)
        if self._effect is not None:
            self._effect.setVolume(float(volume) * UI_GAIN)
        if volume == 0:
            self.stop()

    def stop(self):
        self._until = 0.
        if self._effect is not None:
            self._effect.stop()


def ui_sounds(*, create=True):
    app = QApplication.instance()
    if app is None:
        return None
    bus = getattr(app, "_sound_detective_ui_sounds", None)
    if bus is None and create:
        bus = UiSoundBus(app)
        app._sound_detective_ui_sounds = bus
        app.aboutToQuit.connect(bus.stop)
    return bus


def remaining_click_ms():
    bus = ui_sounds(create=False)
    return bus.remaining_ms() if bus is not None else 0


def widget_volume(widget):
    while widget is not None:
        volume = widget.property("uiAudioVolume")
        if volume is not None:
            return float(volume)
        widget = widget.parentWidget()
    return .35


def play_widget_click(widget, role=None):
    bus = ui_sounds()
    if bus is not None:
        return bus.play_click(role or widget.property("hoverHelpKey") or "click", widget_volume(widget))
    return False


def bind_button_click(widget):
    """Bind once; parameter/language refreshes must not add duplicate sounds."""
    from PySide6.QtWidgets import QAbstractButton
    if not isinstance(widget, QAbstractButton) or widget.property("uiClickBound"):
        return
    widget.setProperty("uiClickBound", True)
    if widget.property("uiClickForwarded"):
        return  # The cassette activates the already-bound play button.
    widget.pressed.connect(lambda: play_widget_click(widget))
    ui_sounds()  # Preload while the window is built, not on the first click.


def bind_volume(owner):
    slider = getattr(owner, "volume", None)
    if slider is None or slider.property("uiVolumeBound"):
        return
    body = owner.centralWidget() or owner
    body.setProperty("uiAudioVolume", slider.value() / 100)
    def changed(value):
        body.setProperty("uiAudioVolume", value / 100)
        bus = ui_sounds(create=False)
        if bus is not None:
            bus.set_volume(value / 100)
    slider.valueChanged.connect(changed)
    slider.setProperty("uiVolumeBound", True)


def bind_tab_clicks(tabs):
    if tabs is not None and not tabs.property("uiClickBound"):
        tabs.setProperty("uiClickBound", True)
        tabs.tabBarClicked.connect(lambda index: play_widget_click(tabs, "tab") if index >= 0 else None)
        ui_sounds()
