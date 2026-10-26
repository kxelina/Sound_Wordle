"""One Qt audio player with sequential A/B, fade-stop and latest-request wins.

Run on the Qt application thread. Inputs are already prepared listening WAVs;
output gain never alters synthesizer settings or the raw render used for scoring.
"""

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, QVariantAnimation, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

from .models import bounded
from .ui_sounds import remaining_click_ms


@dataclass(frozen=True)
class PlaybackItem:
    path: Path
    label: str
    loop: bool = False
    gain: float = 1.


class AudioPlayer(QObject):
    state_changed = Signal(str, str)
    error = Signal(str)
    device_changed = Signal(str)

    def __init__(self, parent=None, *, fade_ms=25, gap_ms=180,
                 media_player=None, audio_output=None, devices=None):
        super().__init__(parent)
        self._media = media_player if media_player is not None else QMediaPlayer(self)
        self._output = audio_output if audio_output is not None else QAudioOutput(self)
        self._devices = devices if devices is not None else QMediaDevices(self)
        self._media.setAudioOutput(self._output)
        self._media.mediaStatusChanged.connect(self._media_status)
        self._media.playbackStateChanged.connect(self._playback_state)
        self._media.errorOccurred.connect(self._media_error)
        self._devices.audioOutputsChanged.connect(self._device_change)
        self._volume = .35
        self._gain = 1.
        self._item_gain = 1.
        self._queue = []
        self._pending = None
        self._label = ""
        self.state = "stopped"
        self._closed = False
        self._gap = QTimer(self)
        self._gap.setSingleShot(True)
        self._gap.setInterval(gap_ms)
        self._gap.timeout.connect(self._advance)
        self._ui_wait = QTimer(self)
        self._ui_wait.setSingleShot(True)
        self._ui_wait.timeout.connect(self._advance)
        self._fade = QVariantAnimation(self)
        self._fade.setDuration(fade_ms)
        self._fade.valueChanged.connect(self._set_gain)
        self._fade.finished.connect(self._finish_stop)
        self._device_change(initial=True)

    @property
    def device_name(self):
        device = self._devices.defaultAudioOutput()
        return "" if device.isNull() else device.description()

    def _set_state(self, state, label=""):
        self.state = state
        self.state_changed.emit(state, label)

    def set_volume(self, volume):
        bounded("volume", volume, 0, 1)
        self._volume = float(volume)
        self._output.setVolume(self._volume * self._gain * self._item_gain)

    def _set_gain(self, gain):
        self._gain = float(gain)
        self._output.setVolume(self._volume * self._gain * self._item_gain)

    def play(self, items):
        if self._closed:
            raise RuntimeError("AudioPlayer is closed")
        items = list(items)
        if not items or any(not isinstance(item, PlaybackItem) for item in items):
            raise ValueError("Expected one or more PlaybackItem objects")
        for item in items:
            if type(item.loop) is not bool:
                raise ValueError("Playback loop must be true or false")
            bounded("playback gain", item.gain, 0, 1)
            if not Path(item.path).is_file():
                raise FileNotFoundError(f"Audio file not found: {item.path}")
        if any(item.loop for item in items) and len(items) != 1:
            raise ValueError("Loop playback requires exactly one item")
        if not self.device_name:
            self._fail("No audio output device is available")
            return
        self._pending = items
        self._queue.clear()
        self._gap.stop()
        self._ui_wait.stop()
        if self.state == "stopping":
            return  # Replace the pending preview without restarting the fade.
        if self._media.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._set_state("stopping", self._label)
            self._fade.setStartValue(self._gain)
            self._fade.setEndValue(0.)
            self._fade.start()
        else:
            self._finish_stop()

    def stop(self, *, immediate=False):
        self._pending = None
        self._queue.clear()
        self._gap.stop()
        self._ui_wait.stop()
        if self._closed:
            return
        if immediate:
            self._fade.stop()
            self._finish_stop()
        elif self.state != "stopping":
            if self._media.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self._set_state("stopping", self._label)
                self._fade.setStartValue(self._gain)
                self._fade.setEndValue(0.)
                self._fade.start()
            else:
                self._finish_stop()

    def _finish_stop(self):
        pending, self._pending = self._pending, None
        self._label = ""
        self._media.stop()
        self._media.setSource(QUrl())
        self._media.setLoops(1)
        self._item_gain = 1.
        self._set_gain(1.)
        self._set_state("stopped")
        if pending and not self._closed:
            self._queue = pending
            self._advance()

    def _advance(self):
        if self._closed or self.state == "stopping":
            return
        if not self._queue:
            self._label = ""
            self._set_state("stopped")
            return
        wait = remaining_click_ms()
        if wait > 0:
            self._ui_wait.start(wait + 8)
            return
        item = self._queue.pop(0)
        self._label = item.label
        self._item_gain = item.gain
        self._set_gain(1.)
        self._media.setLoops(-1 if item.loop else 1)
        self._set_state("loading", self._label)
        self._media.setSource(QUrl.fromLocalFile(str(Path(item.path).resolve())))
        self._media.play()

    def _media_status(self, status):
        if self._closed or self.state == "stopping" or not self._label:
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._label = ""
            if self._queue:
                self._set_state("gap", self._queue[0].label)
                self._gap.start()
            else:
                self._set_state("stopped")

    def _playback_state(self, state):
        if not self._closed and self.state != "stopping" and self._label:
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self._set_state("playing", self._label)

    def _media_error(self, error, message):
        if error != QMediaPlayer.Error.NoError and not self._closed:
            self._fail(message or "Audio playback failed")

    def _fail(self, message):
        self.stop(immediate=True)
        self._set_state("error")
        self.error.emit(message)

    def _device_change(self, initial=False):
        if self._closed:
            return
        if not initial:
            self.stop(immediate=True)
        device = self._devices.defaultAudioOutput()
        self._output.setDevice(device)
        self.device_changed.emit(self.device_name)
        if not initial and device.isNull():
            self._fail("Audio output device disconnected")

    def close(self):
        if not self._closed:
            self.stop(immediate=True)
            self._closed = True
