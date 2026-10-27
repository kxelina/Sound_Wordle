"""Category construction, safe progress, actual SC audio and scene regressions."""

import copy
import os
from pathlib import Path
import sys
import threading
import time

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['SOUND_DETECTIVE_UI_AUDIO'] = '0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SoundDetective'))

import numpy as np
import pytest
import soundfile as sf
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QScrollArea

from sound_detective.audio.models import SoundSettings
from sound_detective.audio.sc_client import SCEngine, RenderCancelled
from sound_detective.audio.sound_sources import CONTROLS, SourcePatch, measure_source, source_events
from sound_detective.audio.source_preview import SourcePreviewRenderer
from sound_detective.game.sound_categories import (SourceSession, assess_source, load_source_cases,
    load_source_session, save_source_session, source_clue)
from sound_detective.ui.sound_categories import SourceCaseWindow
from test_features import Renderer, Player

CASES = load_source_cases()


@pytest.fixture(scope='session')
def app():
    app = QApplication.instance() or QApplication([])
    for name in ('segoeui.ttf','msyh.ttc'):
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
    app.setFont(QFont('Microsoft YaHei UI',10))
    return app


@pytest.mark.parametrize('case',[c for c in CASES if c.scoring=='control_bands'],ids=lambda c:c.id)
def test_reference_alternatives_and_progress_directions(case):
    assert assess_source(case,case.target).total == 100
    assert not assess_source(case,case.initial).passed
    previous = assess_source(case,case.initial).total
    values = dict(case.initial.values)
    for spec in CONTROLS[case.target.recipe]:
        values[spec.key] = dict(case.target.values)[spec.key]
        score = assess_source(case,SourcePatch.make(case.target.recipe,values,case.target.seed)).total
        assert score > previous
        previous = score
    alternatives = {key:band[0]+(band[1]-band[0])*.2 for key,band in case.bands.items()}
    patch = SourcePatch.make(case.target.recipe,alternatives,case.target.seed)
    assert patch != case.target and assess_source(case,patch).passed
    for language in ('en','zh-Hant'):
        for tier in (0,1,2,3):
            assert source_clue(case,case.initial,tier,language)
        assert 'Accepted band' in source_clue(case,case.initial,3,'en')
    assert SourcePatch.from_dict(patch.to_dict()) == patch


@pytest.mark.parametrize('case',[c for c in CASES if c.scoring=='control_bands'],ids=lambda c:c.id)
def test_single_attribute_hint_and_quiet_near_match(case):
    for spec in CONTROLS[case.target.recipe]:
        for value,direction in ((spec.low,-1),(spec.high,1)):
            values = dict(case.target.values)
            values[spec.key] = value
            p = SourcePatch.make(case.target.recipe,values,case.target.seed)
            r = assess_source(case,p)
            assert min(r.scores,key=r.scores.get) == spec.key
            assert r.directions[spec.key] == direction
            assert spec.directions[direction>0][0] in source_clue(case,p,1)
    assert 'inside the goal bands' in source_clue(case,case.target,3)


@pytest.mark.parametrize('case',CASES,ids=lambda c:c.id)
def test_progress_roundtrip_and_unlimited_history(case,tmp_path):
    session = SourceSession(case)
    for _ in range(35): session.submit()
    session.hints = 3
    session.update(case.target)
    assert session.submit().passed
    session.update(case.initial)
    path = tmp_path/'中文 progress'/f'{case.id}.json'
    save_source_session(path,session)
    loaded = load_source_session(path,case)
    assert loaded.to_dict() == session.to_dict()
    assert loaded.attempts == 36 and loaded.solved and len(loaded.records) == 30
    for field,value in (('attempts',-1),('best',float('nan')),('case','W99'),('hints',4),('solved',1)):
        bad = copy.deepcopy(session.to_dict());bad[field] = value
        with pytest.raises((ValueError,TypeError)):
            SourceSession.from_dict(bad,case)


@pytest.mark.parametrize('case',CASES,ids=lambda c:c.id)
def test_source_validation_and_schedules(case):
    for spec in CONTROLS[case.target.recipe]:
        values = dict(case.target.values)
        values[spec.key] = float('nan')
        with pytest.raises(ValueError):SourcePatch.make(case.target.recipe,values)
        values[spec.key] = spec.high+1
        with pytest.raises(ValueError):SourcePatch.make(case.target.recipe,values)
        for position in (0,.25,.5,.75,1):
            value = spec.value_at(position)
            assert spec.low <= value <= spec.high
    events = source_events(case.target)
    assert events == source_events(case.target)
    assert events and all(0 <= event[0] < 3.6 for event in events)


@pytest.mark.parametrize('case',CASES,ids=lambda c:c.id)
def test_workshop_hidden_target_edits_hints_and_recovery(app,case,tmp_path):
    renderer,player = Renderer(),Player()
    path = tmp_path/(case.id+'.json')
    w = SourceCaseWindow(case=case,save_path=path,renderer=renderer,player=player)
    w.show();app.processEvents()
    try:
        assert not w.play_reference.isEnabled()
        w._prepare('target');w._prepare('ab');assert not renderer.requests
        w._submit();assert w.session.attempts == 1
        w._hint();assert w.session.hints == 1
        spec = CONTROLS[case.target.recipe][0]
        w.editor.controls[spec.key].setValue(dict(case.target.values)[spec.key])
        edited = w.session.current
        w.edit_bar.undo();assert w.session.current == case.initial
        assert w.session.attempts == 1 and w.session.hints == 1
        w.edit_bar.redo();assert w.session.current == edited
        w._restore_edit(case.target,record=True)
        w._submit();assert w.session.solved and w.play_reference.isEnabled()
        w._prepare('ab')
        assert renderer.requests[-1][1][0] == {'target':case.target,'current':case.target}
        old = w._revision
        w._restore_edit(case.initial,record=True)
        assert w.session.solved and w.session.attempts == 2
        w._ready(old,{}) # Old render cannot start audio after editing.
        assert not player.items
        w.language.setCurrentIndex(1)
        assert w.submit_button.toolTip() and '合成' in w.submit_button.text()
        assert all(c.toolTip() for c in w.editor.controls.values())
    finally:w.close()
    assert load_source_session(path,case).solved
    path.write_text('{broken','utf-8')
    v = SourceCaseWindow(case=case,save_path=path,renderer=Renderer(),player=Player())
    try:
        assert v._warning == 'backup' and list(tmp_path.glob('*.invalid-*.json'))
        assert not v.session.solved
    finally:v.close()


def test_chirp_curve_direct_pitch_and_duration(app,tmp_path):
    case = next(c for c in CASES if c.id == 'W04')
    w = SourceCaseWindow(case=case,save_path=tmp_path/'bird.json',renderer=Renderer(),player=Player(),embedded=False)
    w.show();app.processEvents()
    try:
        curve = w.editor.curve
        p = curve.points()[1].toPoint()
        destination = p+QPointF(-100,-12).toPoint()
        old = dict(w.session.current.values)
        QTest.mousePress(curve,Qt.MouseButton.LeftButton,pos=p)
        QTest.mouseMove(curve,pos=destination)
        QTest.mouseRelease(curve,Qt.MouseButton.LeftButton,pos=destination)
        new = dict(w.session.current.values)
        assert new['sweep'] > old['sweep']
        assert new['length'] < old['length']
        assert not w.session.attempts
        w.edit_bar.undo();assert w.session.current == case.initial
    finally:w.close()


@pytest.mark.parametrize('case',CASES,ids=lambda c:c.id)
@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_long_feedback_never_hides_transport(app,case,language,tmp_path):
    from sound_detective.ui.studio import StudioWindow
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0)
    w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        assert w._accept_case(case.id)
        w._show_page('desk');w._activate_device('synth')
        c=w.controller
        c.difficulty.setCurrentIndex(c.difficulty.findData('advanced'))
        w.preferences.language=language;w._translate()
        c._restore_edit(case.target,record=True);c._submit()
        c._restore_edit(case.initial,record=True)
        for _ in range(3):c._hint()
        c.status.setText('An intentionally long device error or export path. '*50)
        app.processEvents()
        root=w.device_proxy.widget()
        for button in (c.deck.display,c.deck.reference_display,c.stop_button,c.hint_button,c.submit_button):
            assert root.rect().contains(button.mapTo(root,button.rect().topLeft()))
            assert root.rect().contains(button.mapTo(root,button.rect().bottomRight()))
            if button is not c.submit_button:
                assert c.notebook.rect().contains(button.mapTo(c.notebook,button.rect().topLeft()))
                assert c.notebook.rect().contains(button.mapTo(c.notebook,button.rect().bottomRight()))
        assert len(c.status.toolTip())>1000
        assert c.status.height()<=42
    finally:w.close();app.processEvents()


def test_case_board_filters_scene_and_preferences(app,tmp_path):
    from sound_detective.ui.studio import StudioWindow
    from sound_detective.game.desktop import DesktopPreferences
    w = StudioWindow(progress_dir=tmp_path,animation_ms=0)
    w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        w.board.open(None,'en');w.board.set_mode('wordle')
        assert set(w.board.cards) == {'W01','W02','W03','W04','W05','W06','W07','W08','W09'}
        for category,ids in {'nature':{'W03','W04'},'instrument':{'W05'},'noise':{'W06','W09'},'classic':{'W01','W02','W07','W08'}}.items():
            w.board.set_category(category)
            assert set(w.board.cards) == ids
        for case in CASES:
            assert w._accept_case(case.id)
            w._show_page('desk');w._activate_device('synth');app.processEvents()
            c = w.controller
            c.difficulty.setCurrentIndex(c.difficulty.findData('advanced'))
            assert c.case == case and w.scene_key == 'office'
            assert w.device_proxy.size().height() <= 624
            for field in c.editor.controls.values():
                # Full five-control panel should be visible without scrolling.
                center = field.mapTo(w.device_proxy.widget(),field.rect().center())
                assert w.device_proxy.widget().rect().contains(center)
                viewport = c.editor.findChild(QScrollArea).viewport()
                assert viewport.rect().contains(field.mapTo(viewport,field.rect().topLeft()))
                assert viewport.rect().contains(field.mapTo(viewport,field.rect().bottomRight()))
            c.analysis_button.click();assert c.device_kind == 'analyzer'
            app.processEvents()
            assert c.spectrum.parentWidget().rect().contains(c.spectrum.geometry())
            assert c.plots.count() == 4
            c.source_button.click();assert c.device_kind == 'synth'
            assert DesktopPreferences.from_dict(w.preferences.to_dict()).active_case == case.id
        w.board.open('W04','zh-Hant')
        assert w.board.mode == 'wordle'
    finally:w.close();app.processEvents()


@pytest.mark.parametrize('case',CASES,ids=lambda c:c.id)
def test_actual_supercollider_audio_repeatability_and_gain_invariance(case,tmp_path):
    engine = SCEngine(runtime_dir=Path(__file__).parent/'.runtime/category-engine')
    a,b = tmp_path/'聲音 one.wav',tmp_path/'two.wav'
    engine.render_source(case.target,a)
    engine.render_source(case.target,b)
    x,rate = sf.read(a);y,rate2 = sf.read(b)
    assert rate == rate2 == 44100 and x.shape == (158760,2)
    assert np.isfinite(x).all() and 0 < abs(x).max() <= .9
    np.testing.assert_array_equal(x,y)
    assert abs(x[-1]).max() < .0001
    measured = measure_source(x,rate)
    quieter = measure_source(x*.1,rate)
    assert measured['centroid_hz'] == pytest.approx(quieter['centroid_hz'])
    np.testing.assert_allclose(measured['envelope'],quieter['envelope'],atol=1e-9)
    with pytest.raises(FileExistsError):engine.render_source(case.target,a)
    event = threading.Event();event.set()
    with pytest.raises(RenderCancelled):engine.render_source(case.initial,tmp_path/'cancel.wav',cancel_event=event)
    assert not (tmp_path/'cancel.wav').exists()


def test_existing_sc_tone_still_renders(tmp_path):
    engine = SCEngine(runtime_dir=Path(__file__).parent/'.runtime/category-engine')
    result = engine.render(SoundSettings(),tmp_path/'legacy.wav')
    x,rate = sf.read(result.path)
    assert rate == 44100 and len(x) == 114660 and abs(x).max() > .01


def wait(app,predicate,seconds=40):
    deadline = time.monotonic()+seconds
    while not predicate() and time.monotonic() < deadline:
        app.processEvents();time.sleep(.01)
    assert predicate()


def test_actual_background_preview_cache_cancel_export_and_ab(app,tmp_path):
    case = CASES[0]
    renderer = SourcePreviewRenderer(cache_parent=tmp_path/'cache',engine_factory=lambda:SCEngine(
        runtime_dir=Path(__file__).parent/'.runtime/category-engine'))
    player = Player()
    w = SourceCaseWindow(case=case,save_path=tmp_path/'userdata/W03.json',renderer=renderer,player=player)
    w.show();app.processEvents()
    errors = []
    renderer.failed.connect(lambda r,msg:errors.append(msg))
    try:
        w._prepare('current')
        wait(app,lambda:bool(player.items) or bool(errors))
        assert not errors and len(player.items) == 1
        assert w.spectrum.traces and w.envelope.traces
        w.stop();assert not player.items
        ready = []
        renderer.ready.connect(lambda r,data:ready.append(data))
        w._prepare('export')
        wait(app,lambda:bool(list((tmp_path/'userdata/exports').glob('*.wav'))) or bool(errors))
        assert not errors and ready[-1]['current'].cache_hit
        assert sf.info(next((tmp_path/'userdata/exports').glob('*.wav'))).frames == 158760
        w._restore_edit(case.target,record=True);w._submit()
        w._prepare('ab')
        wait(app,lambda:bool(player.items) or bool(errors))
        assert not errors and len(player.items) == 2
        w._prepare('current');w.stop()
        app.processEvents();assert not player.items
    finally:w.close();app.processEvents()
