"""Regression checks for edit transactions, repair audition and release diagnostics."""
import os
from pathlib import Path
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['SOUND_DETECTIVE_UI_AUDIO'] = '0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'SoundDetective'))
import pytest
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from sound_detective.audio.preview import PreviewAudio
from sound_detective.game.edit_history import EditHistory
from sound_detective.game.cases import load_campaign
from sound_detective.game.parameters import PARAMETERS
from sound_detective.ui.device_panel import ToneDevicePanel
from sound_detective.ui.hidden_sound import HiddenSoundWindow
from sound_detective.ui.melody import MelodyWindow
from sound_detective.game.melody import Draft, GridNote, MelodyPattern


class Renderer(QObject):
    ready = Signal(int, object)
    failed = Signal(int, str)
    matched = Signal(int, object)
    def __init__(self):
        super().__init__()
        self.revision = 0
        self.requests = []
    def prepare(self, *args, **kwargs):
        self.revision += 1
        self.requests.append((self.revision, args, kwargs))
        return self.revision
    def cancel(self):
        self.revision += 1
    def close(self):
        self.cancel()


class Player(QObject):
    state_changed = Signal(str, str)
    error = Signal(str)
    device_changed = Signal(str)
    device_name = 'Test output'
    def __init__(self):
        super().__init__()
        self.items = []
    def set_volume(self, value): pass
    def play(self, items): self.items = list(items)
    def stop(self, **kwargs): self.items = []
    def close(self): self.stop()


@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or QApplication([])


def test_history_branch_coalescing():
    now = [0]
    h = EditHistory({'a': 0, 'b': 0}, limit=3, clock=lambda: now[0])
    h.record({'a': 1, 'b': 0})
    h.record({'a': 2, 'b': 0})
    assert h.undo() == {'a': 0, 'b': 0}
    assert h.redo() == {'a': 2, 'b': 0}
    h.record({'a': 2, 'b': 1})
    h.undo()
    h.record({'a': 3, 'b': 0})
    assert not h.can_redo
    assert h.undo() == {'a': 2, 'b': 0}


@pytest.mark.parametrize('case', load_campaign(), ids=lambda case: case.id)
def test_tone_undo_all_cases(app, tmp_path, case):
    w = ToneDevicePanel(case=case, save_path=tmp_path/f'{case.id}.json', player=Player(), renderer=Renderer())
    try:
        initial = w.session.current
        key = next(k for k in case.editable_parameters if PARAMETERS[k].kind in ('float', 'int'))
        spin, spec = w.controls[key] if hasattr(w, 'controls') else w.editor.controls[key], PARAMETERS[key]
        old = spin.value()
        spin.setValue(old+spec.step if old+spec.step <= spec.high else old-spec.step)
        edited = w.session.current
        assert edited != initial
        w.edit_bar.undo()
        assert w.session.current == initial
        w.edit_bar.redo()
        assert w.session.current == edited
        assert len(w.session.records) == 0
        w._debounce.stop()
        w._language = 'zh-Hant'
        w._translate()
        assert w.edit_bar.undo_button.text().startswith('復原')
    finally: w.close()


def test_hidden_shortcuts_and_progress(app, tmp_path):
    w = HiddenSoundWindow(save_path=tmp_path/'w.json', player=Player(), renderer=Renderer())
    try:
        w.show()
        initial = w.session.current
        w.editor.controls['attack'].setValue(.12)
        w._submit()
        attempts = w.session.attempts
        QTest.keyClick(w.editor.controls['attack'], Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
        assert w.session.current == initial
        assert w.session.attempts == attempts
        w.edit_bar.redo()
        assert w.session.current != initial
    finally: w.close()


def test_free_and_challenge_histories(app, tmp_path):
    w = MelodyWindow(save_path=tmp_path/'w2.json', player=Player(), renderer=Renderer())
    try:
        original = w.session.current
        w._update(Draft(MelodyPattern((GridNote(0, 2, 60),)), original.sound))
        challenge = w.session.current
        w._set_mode('free')
        original_free = w.session.current
        w._update(Draft(MelodyPattern((GridNote(4, 2, 67),)), original_free.sound, 120))
        free = w.session.current
        w.edit_bar.undo()
        assert w.session.current == original_free
        w.edit_bar.redo()
        assert w.session.current == free
        w._set_mode('challenge')
        assert w.session.current == challenge
        w.edit_bar.undo()
        assert w.session.current == original
        assert w.session.free == free
    finally: w.close()


def test_real_selection_audio(app, tmp_path):
    import numpy as np
    import soundfile as sf
    import threading
    from sound_detective.audio.music_preview import MusicPreviewRenderer
    from sound_detective.game.music_cases import MusicSession, load_music_case
    case = load_music_case()
    renderer = MusicPreviewRenderer(cache_parent=tmp_path)
    try:
        preview = renderer._audition_work(case, MusicSession(case).settings, threading.Event(), None, (1, 3))
        audio, rate = sf.read(preview.listening_path, always_2d=True)
        original, original_rate = sf.read(case.evidence, start=rate, frames=2*rate, always_2d=True)
        assert rate == original_rate == 44100
        assert audio.shape == (2*rate, 2)
        assert np.allclose(audio[400:-400], original[400:-400], atol=2e-7)
        assert np.max(abs(audio[0])) < 1e-6
        repeated = renderer._audition_work(case, MusicSession(case).settings, threading.Event(), None, (1, 3))
        assert repeated.cache_hit
        with pytest.raises(ValueError):
            renderer.prepare(case, MusicSession(case).settings, selection=(3, 1))
    finally: renderer.close()


def test_diagnostics_collects_errors_without_aborting(app, tmp_path, monkeypatch):
    from sound_detective.diagnostics import collect_diagnostics, format_report, save_report
    monkeypatch.setenv('SOUND_DETECTIVE_SC_DIR', str(tmp_path/'missing-engine'))
    report = collect_diagnostics(root=tmp_path, probe_audio=False)
    assert not report['ok']
    assert next(c for c in report['checks'] if c['code']=='engine')['status']=='error'
    assert next(c for c in report['checks'] if c['code']=='writable:userdata')['status']=='ok'
    assert 'SOUND_DETECTIVE_SC_DIR' in format_report(report, 'zh-Hant')
    save_report(report, tmp_path/'report.json')
    assert (tmp_path/'report.json').is_file()


def test_scene_lifecycle_and_shortcut(app, tmp_path):
    from sound_detective.ui.studio import StudioWindow
    w = StudioWindow(progress_dir=tmp_path, animation_ms=0)
    try:
        w.volume_slider.setValue(0)
        w.show()
        for cid in ['T01', 'W01', 'W02', 'M01', 'T08']:
            assert w._accept_case(cid)
            w._show_page('desk')
            w._activate_device('synth')
            app.processEvents()
            if cid == 'T01':
                initial=w.controller.session.current
                w.controller.editor.controls['release'].setValue(.13)
                QTest.keyClick(w.controller.editor.controls['release'], Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
                assert w.controller.session.current==initial
                QTest.keyClick(w, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
                assert w.controller.session.current!=initial
        w.open_settings()
        assert w.diagnostics_button.isEnabled()
    finally:
        w.close()
        app.processEvents()
