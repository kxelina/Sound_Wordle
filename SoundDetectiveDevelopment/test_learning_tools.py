"""Difficulty, latest-only looping, teaching examples, collection and pilot logs."""
import copy
import csv
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace

os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
GAME=Path(__file__).resolve().parents[1]/'SoundDetective'
sys.path.insert(0,str(GAME))
import pytest
import numpy as np
from PySide6.QtCore import Qt,QPointF
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from sound_detective.audio.sound_sources import CONTROLS,SourcePatch,source_events
from sound_detective.audio.sc_client import SCEngine
from sound_detective.game.sound_categories import SourceSession,load_source_cases,assess_source,save_source_session,load_source_session,source_clue
from sound_detective.game.source_learning import with_difficulty,source_path,selected_difficulty,concept_pair,DIFFICULTIES
from sound_detective.game.debrief import build_debrief
from sound_detective.game.evidence import EvidenceStore
from sound_detective.game.playtest import PlaytestLog
from sound_detective.ui.sound_categories import SourceCaseWindow
from sound_detective.ui.evidence import EvidencePanel
from sound_detective.ui.studio import StudioWindow
from test_features import Renderer,Player

CASES=load_source_cases()

@pytest.fixture(scope='session')
def app():
    result=QApplication.instance() or QApplication([])
    for name in ('segoeui.ttf','msyh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
    result.setFont(QFont('Microsoft YaHei UI',10));return result


@pytest.mark.parametrize('base',[c for c in CASES if c.scoring=='control_bands'],ids=lambda c:c.id)
@pytest.mark.parametrize('difficulty,count',[('beginner',2),('standard',4),('advanced',5)])
def test_difficulty_is_solvable_and_locked_controls_cannot_change(base,difficulty,count):
    case=with_difficulty(base,difficulty)
    assert len(case.editable_parameters)==count
    assert assess_source(case,case.target).total==100
    assert not assess_source(case,case.initial).passed
    previous=assess_source(case,case.initial).total
    values=dict(case.initial.values)
    for key in case.editable_parameters:
        values[key]=dict(case.target.values)[key]
        score=assess_source(case,SourcePatch.make(case.target.recipe,values,case.target.seed)).total
        assert score>previous;previous=score
    alternative=dict(case.target.values)
    for key in case.editable_parameters:
        lo,hi=case.bands[key];alternative[key]=lo+(hi-lo)*.3
    assert assess_source(case,SourcePatch.make(case.target.recipe,alternative,case.target.seed)).passed
    for spec in CONTROLS[case.target.recipe]:
        values=dict(case.target.values);values[spec.key]=spec.low
        patch=SourcePatch.make(case.target.recipe,values,case.target.seed)
        if spec.key not in case.editable_parameters:
            with pytest.raises(ValueError):assess_source(case,patch)
        else:
            assert spec.help[0] in source_clue(case,patch,1)


def test_legacy_save_migration_and_difficulties_are_independent(app,tmp_path):
    base=CASES[1];path=tmp_path/'鳥鳴 save.json'
    session=SourceSession(base);session.submit()
    legacy=session.to_dict();legacy.pop('difficulty');legacy['schema_version']=1
    original=json.dumps(legacy).encode();path.write_bytes(original)
    w=SourceCaseWindow(case=base,save_path=path,difficulty=None,renderer=Renderer(),player=Player())
    try:
        assert w.case.difficulty=='advanced' and w.session.attempts==1
        w.difficulty.setCurrentIndex(0);w._submit();w._hint()
        assert w.case.difficulty=='beginner' and w.session.attempts==1
        w.difficulty.setCurrentIndex(1);assert not w.session.attempts
        w.difficulty.setCurrentIndex(0);assert w.session.attempts==1 and w.session.hints==1
        assert not w.edit_bar.stack.can_undo
        w.difficulty.setCurrentIndex(2);assert w.session.attempts==1 and not w.session.hints
        assert next(tmp_path.glob('*.before-difficulty-v2-*.json')).read_bytes()==original
        assert selected_difficulty(path)=='advanced'
        assert load_source_session(source_path(path,'beginner'),with_difficulty(base,'beginner')).hints==1
    finally:w.close()


@pytest.mark.parametrize('difficulty',['beginner','standard'])
def test_chirp_drag_preserves_locked_controls(app,tmp_path,difficulty):
    w=SourceCaseWindow(case=CASES[1],save_path=tmp_path/'bird.json',difficulty=difficulty,renderer=Renderer(),player=Player())
    w.show();app.processEvents()
    try:
        curve=w.editor.curve;start=dict(w.session.current.values)
        point=curve.points()[1].toPoint()
        QTest.mousePress(curve,Qt.MouseButton.LeftButton,pos=point)
        QTest.mouseMove(curve,pos=point+QPointF(-60,-9).toPoint())
        QTest.mouseRelease(curve,Qt.MouseButton.LeftButton,pos=point+QPointF(-60,-9).toPoint())
        current=dict(w.session.current.values)
        assert current['length']<start['length']
        if difficulty=='beginner':assert current['sweep']==start['sweep'] and current['pitch']!=start['pitch']
        assert assess_source(w.case,w.session.current)
    finally:w.close()


def preview(path):
    return SimpleNamespace(listening_path=path,measurements={'spectrum_hz':np.array([0,1]),'spectrum_db':np.array([0,0]),'envelope_seconds':np.array([0,1]),'envelope':np.array([0,1])})


def test_loop_debounces_latest_edits_and_stop_cancels_pending_audio(app,tmp_path):
    renderer,player=Renderer(),Player()
    w=SourceCaseWindow(case=CASES[1],save_path=tmp_path/'w.json',renderer=renderer,player=player)
    try:
        w.loop_button.click();revision=w._revision
        renderer.ready.emit(revision,{'current':preview(tmp_path/'first.wav')})
        assert len(player.items)==1 and player.items[0].loop
        w.editor.controls['pitch'].setValue(80)
        w.editor.controls['pitch'].setValue(81)
        assert len(renderer.requests)==1 and w.update_timer.isActive()
        w.update_timer.stop();w.update_timer.timeout.emit()
        assert len(renderer.requests)==2 and dict(renderer.requests[-1][1][0]['current'].values)['pitch']==81
        renderer.ready.emit(revision,{'current':preview(tmp_path/'stale.wav')});assert not player.items
        renderer.ready.emit(w._revision,{'current':preview(tmp_path/'new.wav')});assert player.items[0].path.name=='new.wav'
        w.editor.controls['pitch'].setValue(82);w.stop()
        assert not w.loop_button.isChecked() and not w.update_timer.isActive()
        renderer.ready.emit(w._revision-1,{});assert not player.items
        assert w.session.attempts==0
    finally:w.close()


def test_loop_error_difficulty_and_example_cannot_restart_playback(app,tmp_path):
    renderer,player=Renderer(),Player()
    w=SourceCaseWindow(case=CASES[1],save_path=tmp_path/'w.json',renderer=renderer,player=player)
    try:
        w.loop_button.click();renderer.failed.emit(w._revision,'Device failure')
        assert not w.loop_button.isChecked() and 'failure' in w.status.text()
        w.loop_button.click();renderer.ready.emit(w._revision,{})
        assert not w.loop_button.isChecked() and not player.items
        w.loop_button.click();w.difficulty.setCurrentIndex(0)
        assert not w.loop_button.isChecked() and w._armed is None
        original=w.session.current;w._prepare('example')
        patches=renderer.requests[-1][1][0]
        assert set(patches)=={'low','high'}
        low,high=patches.values()
        assert low.seed==high.seed==101
        assert sum(a!=b for (_,a),(_,b) in zip(low.values,high.values))==1
        renderer.ready.emit(w._revision,{k:preview(tmp_path/(k+'.wav')) for k in patches})
        assert len(player.items)==2 and not any(item.loop for item in player.items)
        assert original==w.session.current and w.session.attempts==0 and w.session.hints==0
        assert not w.play_reference.isEnabled()
    finally:w.close()


@pytest.mark.parametrize('language',['en','zh-Hant'])
@pytest.mark.parametrize('base',CASES,ids=lambda c:c.id)
def test_embedded_difficulty_buttons_and_transport_fit(app,tmp_path,language,base):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        assert w._accept_case(base.id);w._show_page('desk');w._activate_device('synth')
        w.preferences.language=language;w._translate();c=w.controller
        for index in range(3):
            c.difficulty.setCurrentIndex(index);app.processEvents()
            root=w.device_proxy.widget()
            for button in (*c.difficulty.buttons,c.deck.display,c.stop_button,c.hint_button,c.loop_button,c.submit_button):
                assert button.isVisible()
                assert root.rect().contains(button.mapTo(root,button.rect().topLeft()))
                assert root.rect().contains(button.mapTo(root,button.rect().bottomRight()))
                assert button.toolTip()
            for button in (c.deck.display,c.stop_button):
                assert c.deck.rect().contains(button.mapTo(c.deck,button.rect().topLeft()))
                assert c.deck.rect().contains(button.mapTo(c.deck,button.rect().bottomRight()))
            assert not any(b.isVisible() for b in (c.play_current,c.play_reference,c.play_ab,c.example_button))
            assert sum(control.isEnabled() for control in c.editor.controls.values())==(2,4,5)[index]
        c.loop_button.click();c.editor.controls[next(iter(c.editor.controls))].setValue(dict(c.case.target.values)[next(iter(c.editor.controls))])
        w._show_page('desk');assert not c.update_timer.isActive() and not c.loop_button.isChecked()
    finally:w.close();app.processEvents()


def solved_record(case):
    session=SourceSession(case);session.update(case.target);session.submit()
    return build_debrief(case,session)


def test_collection_validates_snapshots_preserves_first_and_recovers(tmp_path):
    path=tmp_path/'聲音 collection.json';store=EvidenceStore(path)
    for difficulty in DIFFICULTIES:
        record=solved_record(with_difficulty(CASES[1],difficulty));assert store.remember(record,difficulty)
    assert len(EvidenceStore(path).entries)==3
    first=copy.deepcopy(store.entries)
    assert store.remember(record,difficulty) and store.entries==first
    bad=json.loads(path.read_text('utf-8'))
    key=next(iter(bad['entries']))
    bad['entries'][key]['review']['clips']['final']={'type':'file','path':'C:/external.wav'}
    path.write_text(json.dumps(bad),'utf-8');recovered=EvidenceStore(path)
    assert recovered.warning=='backup' and not recovered.entries and list(tmp_path.glob('*.invalid-*.json'))


def test_cabinet_readonly_export_and_cancel(app,tmp_path):
    store=EvidenceStore(tmp_path/'cabinet.json');store.remember(solved_record(CASES[1]))
    tone,source,music,player=Renderer(),Renderer(),Renderer(),Player()
    panel=EvidencePanel(store,CASES,tone_renderer=tone,source_renderer=source,music_renderer=music,player=player)
    panel.resize(1180,610);panel.show();app.processEvents()
    wav=tmp_path/'generated.wav';wav.write_bytes(b'test pipeline output')
    try:
        panel.export_final();revision=panel._revision;panel.stop()
        source.ready.emit(revision,{'final':preview(wav)})
        assert not (tmp_path/'evidence-exports').exists()
        panel.export_final();source.ready.emit(panel._revision,{'final':preview(wav)})
        exported=list((tmp_path/'evidence-exports').glob('*.wav'))
        assert len(exported)==1 and exported[0].read_bytes()==wav.read_bytes() and not player.items
        panel.translate('zh-Hant');assert '收藏' in panel.heading.text() and panel.export_button.toolTip()
    finally:panel.shutdown();panel.close()


def test_studio_difficulties_keep_reviews_and_collection_separate(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0);w.volume_slider.setValue(0);w.show()
    try:
        w._accept_case('W04');w._show_page('desk');w._activate_device('synth');c=w.controller
        for index in range(3):
            c.difficulty.setCurrentIndex(index);c._restore_edit(c.case.target,record=True);c._submit();app.processEvents()
            assert w.page=='review' and w.debrief_panel.record.title==c.case.title
            w._leave_review()
        assert len(w.evidence_store.entries)==3
        w.open_cabinet();assert w.page=='cabinet' and w.cabinet_panel.selector.count()==3
        w.cabinet_panel.selector.setCurrentIndex(0);assert 'Beginner' in w.cabinet_panel.record.title['en']
        w.go_back();assert w.page=='device'
        assert c.session.attempts==1
    finally:w.close();app.processEvents()


def test_playtest_records_failures_and_exports_without_personal_data(tmp_path):
    now=[1.];log=PlaytestLog(tmp_path,clock=lambda:now[0]);case=with_difficulty(CASES[0],'beginner')
    log.record(case,'start');now[0]=4.;log.record(case,'submit',attempts=1,score=22)
    now[0]=9.;log.record(case,'submit',attempts=2,score=100)
    output=log.export_csv()
    with output.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    assert rows[1]['score']=='22' and rows[2]['elapsed_seconds']=='8.0'
    assert all(set(row)==set(PlaytestLog.FIELDS) for row in rows)
    assert len(log.path.read_text('utf-8').splitlines())==3
    with pytest.raises(ValueError):log.record(case,'secret arbitrary event')


def test_playtest_ui_is_opt_in_and_keeps_every_submission(app,tmp_path):
    w=SourceCaseWindow(case=CASES[0],save_path=tmp_path/'w.json',renderer=Renderer(),player=Player())
    try:
        w._submit();assert not (tmp_path/'playtests').exists()
        w.record_button.click();w._submit();w._hint();w._prepare('example');w.record_button.click()
        assert not w._recording
        events=[r['event'] for r in w.playtest_log.records]
        assert events==['start','submit','hint','example','end']
        assert w.playtest_log.records[1]['score']<90
        assert w.playtest_log.export_csv().is_file()
    finally:w.close()


@pytest.mark.parametrize('recipe,key',[('rain','brightness'),('bird','length'),('pluck','decay'),('static','rate')])
def test_teaching_examples_render_actual_different_audio(recipe,key,tmp_path):
    import soundfile as sf
    low,high=concept_pair(recipe,key)
    engine=SCEngine(runtime_dir=tmp_path/'engine')
    outputs=[]
    for name,patch in (('low',low),('high',high)):
        result=engine.render_source(patch,tmp_path/(name+'.wav'))
        audio,rate=sf.read(result)
        assert rate==44100 and np.isfinite(audio).all() and 0<abs(audio).max()<=.9
        outputs.append(audio)
    assert not np.allclose(*outputs)
