"""Direct note gestures, cancellation, stage locks and undo integration."""
import os
from pathlib import Path
import sys

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['SOUND_DETECTIVE_UI_AUDIO'] = '0'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'SoundDetective'))
import pytest
from PySide6.QtCore import Qt, QPointF
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from sound_detective.game.melody import Draft, GridNote, MelodyPattern
from sound_detective.ui.piano_roll import PianoRollEditor, pitch_name
from sound_detective.ui.melody import MelodyWindow
from test_features import Player, Renderer


@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def editor(app):
    e = PianoRollEditor()
    e.resize(800, 430)
    e.set_pattern(MelodyPattern((GridNote(4, 3, 64),)))
    e.show()
    app.processEvents()
    yield e
    e.close()


def drag(roll, edge, dx=0, dy=0, *, release=True):
    rect = roll.note_rect(roll.pattern.notes[roll.selection if roll.selection >= 0 else 0])
    origin = rect.center()
    if edge == 'left': origin.setX(rect.left()+2)
    elif edge == 'right': origin.setX(rect.right()-2)
    destination = origin + QPointF(dx*roll.cell_width, -dy*roll.ROW)
    QTest.mousePress(roll, Qt.MouseButton.LeftButton, pos=origin.toPoint())
    QTest.mouseMove(roll, destination.toPoint())
    if release:
        QTest.mouseRelease(roll, Qt.MouseButton.LeftButton, pos=destination.toPoint())
    return destination


@pytest.mark.parametrize('semitones', [-3, 2, 20, -20])
def test_drag_up_down_changes_pitch_only(editor, semitones):
    changes = []
    editor.changed.connect(changes.append)
    old = editor.roll.pattern
    destination = drag(editor.roll, 'move', dy=semitones, release=False)
    expected = max(60, min(72, 64+semitones))
    assert editor.roll.pattern == old
    assert pitch_name(expected) in editor.readout.text()
    QTest.mouseRelease(editor.roll, Qt.MouseButton.LeftButton, pos=destination.toPoint())
    assert editor.roll.pattern.notes == (GridNote(4, 3, expected),)
    assert len(changes) == 1


@pytest.mark.parametrize('edge,dx,expected', [
    ('right', 2, GridNote(4, 5, 64)), ('right', -2, GridNote(4, 1, 64)),
    ('left', -2, GridNote(2, 5, 64)), ('left', 2, GridNote(6, 1, 64)),
    ('left', -30, GridNote(0, 7, 64)), ('right', 30, GridNote(4, 12, 64)),
])
def test_both_edges_resize(editor, edge, dx, expected):
    drag(editor.roll, edge, dx=dx)
    assert editor.roll.pattern.notes == (expected,)


@pytest.mark.parametrize('edge,dx,expected', [('left', -30, GridNote(2, 5, 64)), ('right', 30, GridNote(4, 5, 64))])
def test_edges_stop_at_neighbours(editor, edge, dx, expected):
    editor.set_pattern(MelodyPattern((GridNote(0, 2, 60), GridNote(4, 3, 64), GridNote(9, 2, 67))))
    editor.roll.selection = 1
    drag(editor.roll, edge, dx=dx)
    assert editor.roll.pattern.notes[1] == expected


def test_overlap_rejected_with_no_committed_change(editor):
    original = MelodyPattern((GridNote(4, 3, 64), GridNote(9, 2, 67)))
    editor.set_pattern(original)
    editor.roll.selection = 0
    destination = drag(editor.roll, 'move', dx=4, release=False)
    assert editor.message.text()
    QTest.mouseRelease(editor.roll, Qt.MouseButton.LeftButton, pos=destination.toPoint())
    assert editor.roll.pattern == original
    assert editor.message.text()


@pytest.mark.parametrize('cancel', ['escape', 'hide', 'focus'])
def test_cancel_does_not_change_note(editor, cancel):
    old = editor.roll.pattern
    destination = drag(editor.roll, 'move', dy=3, release=False)
    if cancel == 'escape': QTest.keyClick(editor.roll, Qt.Key.Key_Escape)
    elif cancel == 'hide': editor.roll.hide()
    else: editor.pitch.setFocus(); QApplication.processEvents()
    assert editor.roll._drag is None
    QTest.mouseRelease(editor.roll, Qt.MouseButton.LeftButton, pos=destination.toPoint())
    assert editor.roll.pattern == old


def test_window_stage_lock_drag_history_and_playback(app, tmp_path):
    r, p = Renderer(), Player()
    w = MelodyWindow(save_path=tmp_path/'gesture-progress.json', renderer=r, player=p)
    w.show()
    try:
        rhythm = MelodyPattern(tuple(GridNote(n.start, n.length, 60) for n in w.case.pattern.notes))
        w._pattern_changed(rhythm)
        app.processEvents()
        w.piano.roll.selection = 1
        drag(w.piano.roll, 'move', dy=4)
        assert w.session.current.pattern == rhythm
        assert not w.piano.pitch.isEnabled()
        w._submit()
        assert w.session.unlocked == 1
        app.processEvents()
        w.piano.roll.selection = 1
        p.items = ['old preview']
        destination = drag(w.piano.roll, 'move', dy=4, release=False)
        assert not p.items
        QTest.mouseRelease(w.piano.roll, Qt.MouseButton.LeftButton, pos=destination.toPoint())
        assert w.session.current.pattern.notes[1].pitch == 64
        edited = w.session.current
        w.edit_bar.undo()
        assert w.session.current.pattern == rhythm
        assert w.session.attempts == 1 and w.session.unlocked == 1
        w.edit_bar.redo()
        assert w.session.current == edited
        w._prepare('current')
        assert r.requests[-1][1][0]['current'][1] == edited.sequence
        w._set_mode('free')
        draft = w.session.current
        w._update(Draft(MelodyPattern((GridNote(4, 3, 64),)), draft.sound, 120))
        app.processEvents()
        drag(w.piano.roll, 'right', dx=2)
        assert w.session.current.pattern.notes == (GridNote(4, 5, 64),)
        w.edit_bar.undo()
        assert w.session.current.pattern.notes == (GridNote(4, 3, 64),)
        w._set_mode('challenge')
        assert w.session.current == edited
    finally: w.close()


def test_embedded_scene_keeps_low_notes_visible_and_draggable(app, tmp_path):
    from sound_detective.ui.studio import StudioWindow
    w = StudioWindow(progress_dir=tmp_path, animation_ms=0)
    w.resize(1280, 720)
    w.volume_slider.setValue(0)
    w.show()
    try:
        assert w.open_free_composition()
        w._show_page('desk')
        w._activate_device('synth')
        c = w.controller
        c._update(Draft(MelodyPattern((GridNote(4, 3, 60),)), c.session.current.sound))
        c.piano.roll.selection = 0
        c.piano.roll.selected.emit()
        app.processEvents()
        c.piano._reveal_selection()
        app.processEvents()
        roll = c.piano.roll
        rect = roll.note_rect(c.session.current.pattern.notes[0])
        for viewport in (c.piano.viewport.viewport(), c.piano_scroll.viewport()):
            assert viewport.rect().contains(roll.mapTo(viewport, rect.center().toPoint()))
        def point(p):
            return w.view.mapFromScene(w.device_proxy.mapToScene(QPointF(roll.mapTo(w.device_proxy.widget(), p.toPoint()))))
        a = point(rect.center())
        b = point(rect.center()+QPointF(0, -2*roll.ROW))
        QTest.mousePress(w.view.viewport(), Qt.MouseButton.LeftButton, pos=a)
        QTest.mouseMove(w.view.viewport(), pos=b)
        QTest.mouseRelease(w.view.viewport(), Qt.MouseButton.LeftButton, pos=b)
        assert c.session.current.pattern.notes == (GridNote(4, 3, 62),)
        assert c.piano.ruler.isVisible()
        assert c.piano.pitch.value() == 62
        c.edit_bar.undo()
        assert c.session.current.pattern.notes == (GridNote(4, 3, 60),)
    finally:
        w.close()
        app.processEvents()
