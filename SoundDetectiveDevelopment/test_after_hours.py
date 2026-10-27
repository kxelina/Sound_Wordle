"""Original non-song cases, stage isolation, authored rests and durable reviews."""
import copy,json,os
from pathlib import Path
import sys

os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
GAME=Path(__file__).resolve().parents[1]/'SoundDetective';sys.path.insert(0,str(GAME))
import pytest
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont,QFontDatabase
from sound_detective.audio.matching import MatchResult
from sound_detective.audio.sc_client import SCEngine
from sound_detective.game.cases import load_campaign
from sound_detective.game.catalog import CASE_IDS
from sound_detective.game.desktop import DesktopPreferences
from sound_detective.game.melody import (MelodyCase,MelodyPattern,GridNote,Draft,MelodySession,
    load_melody_cases,load_melody_session,save_melody_session,compare_draft,authored_melody_clue)
from sound_detective.game.session import SessionState
from sound_detective.game.debrief import build_debrief,Debrief
from sound_detective.game.evidence import EvidenceStore
from sound_detective.game.player_journey import JourneyStore
from sound_detective.ui.melody import MelodyWindow
from sound_detective.ui.device_panel import ToneDevicePanel
from sound_detective.ui.studio import StudioWindow
from test_features import Renderer,Player

CASES={c.id:c for c in load_melody_cases()}
KNOCK=load_campaign()[-1]

@pytest.fixture(scope='session')
def app():
    app=QApplication.instance() or QApplication([])
    for name in ('segoeui.ttf','msyh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
    app.setFont(QFont('Microsoft YaHei UI',10));return app

def result(case,value=0):return MatchResult(value,value,value,value,value==100,('close',),{},case.comparison)

def tone_submit(session,passing=False):
    if passing:session.update(**session.case.parameters(session.case.reference))
    return session.complete_submission(session.begin_submission(),result(session.case,100 if passing else 0))

def rhythm(case):return MelodyPattern(tuple(GridNote(n.start,n.length,60) for n in case.pattern.notes))

def solve(case):
    session=MelodySession(case=case)
    session.update(Draft(rhythm(case),case.initial));session.submit()
    if not session.solved:session.update(Draft(case.pattern,case.reference));session.submit()
    assert session.solved
    return session

def test_catalog_and_preferences_accept_new_cases_only():
    assert len(load_campaign())==9 and KNOCK.id=='T09'
    assert set(CASES)=={'W02','W07','W08'}
    for cid in ('T09','W07','W08'):
        p=DesktopPreferences(active_case=cid);assert DesktopPreferences.from_dict(p.to_dict()).active_case==cid
    with pytest.raises(ValueError):DesktopPreferences.from_dict(DesktopPreferences(active_case='W99').to_dict())

def test_doorbell_stages_are_independent_and_reachable(tmp_path):
    case=CASES['W07'];s=MelodySession(case=case)
    with pytest.raises(ValueError):s.update(Draft(case.pattern,case.initial))
    s.update(Draft(rhythm(case),case.initial));r=s.submit()
    assert r.scores[0]==100 and r.total==50 and s.unlocked==1 and not s.solved
    assert s.focus==1
    s.update(Draft(case.pattern,case.reference));r=s.submit()
    assert r.total==100 and s.solved and s.unlocked==1
    with pytest.raises(ValueError):s.set_mode('free')
    path=tmp_path/'門鈴.json';save_melody_session(path,s)
    assert load_melody_session(path,case).to_dict()==s.to_dict()
    with pytest.raises(ValueError):load_melody_session(path,CASES['W08'])

def test_silent_beat_rejects_extra_and_quiet_overlap():
    case=CASES['W08'];s=MelodySession(case=case)
    extra=MelodyPattern(tuple(GridNote(n,1,60) for n in (0,4,8,12)))
    s.update(Draft(extra,case.initial));r=s.submit()
    assert r.total==75 and not s.solved and s.unlocked==0
    # A one-cell early third note would otherwise earn 91.67 rhythm points.
    overlap=MelodyPattern((GridNote(0,1),GridNote(4,1),GridNote(11,1)))
    s.update(Draft(overlap,case.initial));r=s.submit()
    assert r.total<90 and not all(r.passed)
    s.update(Draft(case.pattern,case.reference));r=s.submit()
    assert r.total==100 and s.solved and s.unlocked==0
    with pytest.raises(ValueError):s.update(Draft(MelodyPattern((GridNote(0,1,61),)),case.initial))

def test_authored_clues_do_not_use_four_note_message():
    for cid in ('W07','W08'):
        case=CASES[cid];draft=Draft(sound=case.initial);r=compare_draft(draft,case)
        for language in ('en','zh-Hant'):
            for tier in range(4):
                clue=authored_melody_clue(case,draft,r,0,tier,language)
                assert clue and 'Four onsets' not in clue and '四個音各' not in clue
    case=CASES['W08'];draft=Draft(MelodyPattern(tuple(GridNote(n,1) for n in (0,4,8,12))),case.initial)
    assert 'silent third beat' in authored_melody_clue(case,draft,compare_draft(draft,case),0,1,'en')

def test_w02_save_format_and_free_composition_are_unchanged(tmp_path):
    s=MelodySession();s.set_mode('free');s.update(Draft(MelodyPattern((GridNote(0,2,65),)),s.free.sound,120))
    data=s.to_dict();assert 'case_id' not in data and data['version']=='melody-workshop-v1'
    path=tmp_path/'W02.json';path.write_text(json.dumps(data),'utf-8')
    loaded=load_melody_session(path);assert loaded.to_dict()==data and loaded.mode=='free'

@pytest.mark.parametrize('cid',['W07','W08'])
def test_authored_save_rejects_case_revision_or_illegal_stage(cid):
    case=CASES[cid];data=solve(case).to_dict()
    for key,value in (('case_fingerprint','changed'),('case_id','W02'),('unlocked',2)):
        bad=copy.deepcopy(data);bad[key]=value
        with pytest.raises(ValueError):MelodySession.from_dict(bad,case)

def test_t09_has_rolling_history_and_preserves_first_clear_after_practice():
    now=[100.];s=SessionState(KNOCK,clock=lambda:now[0])
    for _ in range(1005):tone_submit(s)
    assert s.attempt_count==1005 and len(s.records)==30 and s.last.number==1005
    now[0]=115.;tone_submit(s,True);first=s.first_pass
    assert first.number==1006 and first.elapsed_seconds==15
    loaded=SessionState.from_dict(KNOCK,s.to_dict(),clock=lambda:now[0]);assert loaded.first_pass==first
    now[0]=200.;loaded.restart();now[0]=201.
    for _ in range(35):tone_submit(loaded)
    assert len(loaded.records)==30 and loaded.attempt_count==35 and loaded.first_pass==first
    restored=SessionState.from_dict(KNOCK,loaded.to_dict(),clock=lambda:now[0])
    assert restored.first_pass==first and restored.practice and restored.last.number==35
    record=build_debrief(KNOCK,restored)
    assert record.attempts==1006 and record.clips['final']['settings']==KNOCK.reference.to_dict()

def test_rolling_history_rejects_inconsistent_counts_and_snapshot():
    s=SessionState(KNOCK,clock=lambda:0.);tone_submit(s,True);data=s.to_dict()
    for field,value in (('submitted',2),('first_pass',None)):
        bad=copy.deepcopy(data);bad[field]=value
        with pytest.raises(ValueError):SessionState.from_dict(KNOCK,bad)
    bad=copy.deepcopy(data);bad['records'][0]['number']=4
    with pytest.raises(ValueError):SessionState.from_dict(KNOCK,bad)

@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_t09_theory_never_counts_as_attempt_or_changes_controls(app,tmp_path,language):
    w=ToneDevicePanel(case=KNOCK,save_path=tmp_path/'T09.json',renderer=Renderer(),player=Player())
    try:
        before=w.session.current
        for index in range(3):
            w.theories.buttons[index].click()
            assert w.theory_feedback.text() and w.session.current==before and w.session.attempt_count==0
        w._language=language;w._translate()
        assert w.question.text()==KNOCK.investigation['question'][language]
        assert all(b.toolTip() for b in w.theories.buttons)
    finally:w.close()

@pytest.mark.parametrize('cid',['W07','W08'])
@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_new_workshop_stages_clues_and_target_unlock(app,tmp_path,cid,language):
    case=CASES[cid];renderer,player=Renderer(),Player()
    w=MelodyWindow(case=case,save_path=tmp_path/(cid+'.json'),renderer=renderer,player=player,language=language)
    w.show();app.processEvents()
    try:
        assert 'W02' not in w.title.text() and not w.mode_buttons['free'].isVisible()
        w._prepare('target');assert not renderer.requests
        for _ in range(3):w._hint()
        assert w.piano.roll.rhythm_hints
        w._update(Draft(rhythm(case),case.initial));w._submit()
        assert w.session.attempts==1
        if cid=='W07':
            assert w.session.unlocked==1 and not w.play_reference.isEnabled()
            w._update(Draft(case.pattern,case.reference));w._submit()
        assert w.play_reference.isEnabled() and w.session.solved
        w._prepare('ab');assert set(renderer.requests[-1][1][0])=={'target','current'}
        attempts=w.session.attempts;w._set_mode('free');assert w.session.mode=='challenge' and w.session.attempts==attempts
        assert not w.work_tabs.isTabVisible(1)
        app.processEvents();w.piano._reveal_selection();app.processEvents()
        viewport=w.piano_scroll.viewport()
        for widget in (w.piano.length,w.piano.add_button,w.piano.delete_button):
            assert viewport.rect().contains(widget.mapTo(viewport,widget.rect().bottomRight()))
        if cid=='W07':
            viewport=w.piano.viewport.viewport()
            for note in w.session.current.pattern.notes:
                assert viewport.rect().contains(w.piano.roll.mapTo(viewport,w.piano.roll.note_rect(note).center().toPoint()))
    finally:w.close()

@pytest.mark.parametrize('cid',['T09','W07','W08'])
@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_new_cases_embed_clear_review_collect_and_restore(app,tmp_path,cid,language):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        assert w._accept_case(cid);w._show_page('desk');w._activate_device('delay' if cid=='T09' else 'synth')
        w.preferences.language=language;w._translate();app.processEvents();c=w.controller
        root=w.device_proxy.widget()
        buttons=(c.compare_button,*c.theories.buttons) if cid=='T09' else (c.submit_button,c.deck.display,c.stop_button,c.hint_button)
        for button in buttons:
            assert root.rect().contains(button.mapTo(root,button.rect().topLeft()))
            assert root.rect().contains(button.mapTo(root,button.rect().bottomRight()))
            assert button.toolTip()
        if cid=='T09':
            c.session.update(**c.case.parameters(c.case.reference));c._sync_controls()
            c._submission_token=c.session.begin_submission();c._revision=c._match_revision=1;c._matched(1,result(c.case,100))
        else:
            c._update(Draft(rhythm(c.case),c.case.initial));c._submit()
            if not c.session.solved:c._update(Draft(c.case.pattern,c.case.reference));c._submit()
        app.processEvents();assert w.page=='review'
        record=w.debrief_panel.record;assert record.case_id==cid and record.clips['final']
        assert Debrief.from_dict(record.to_dict())==record
        assert cid+':advanced' in w.evidence_store.entries
        w.open_cabinet();assert w.cabinet_panel.record.case_id==cid
        w.go_back();w._review_cases();w.board.set_mode('tone' if cid=='T09' else 'wordle')
        assert w.board.cards[cid].isEnabled()
    finally:w.close();app.processEvents()
    state=DesktopPreferences.from_dict(json.loads((tmp_path/'desktop.json').read_text('utf-8'))) if (tmp_path/'desktop.json').exists() else None
    store=JourneyStore(tmp_path/'player-journey.json');assert cid in store.reviews

@pytest.mark.parametrize('cid',['T09','W07','W08'])
def test_new_reference_is_real_audio_with_expected_timing(cid,tmp_path):
    import soundfile as sf
    from scipy.signal import find_peaks
    engine=SCEngine(runtime_dir=tmp_path/'engine');case=KNOCK if cid=='T09' else CASES[cid]
    settings=case.reference;rendered=engine.render_sequence(settings,case.sequence,tmp_path/(cid+'.wav'))
    x,rate=sf.read(rendered.path);assert rate==44100 and np.isfinite(x).all() and 0<abs(x).max()<=.9
    if cid=='T09':
        mono=np.mean(x*x,axis=1);frame=round(rate*.01);starts=np.arange(0,len(mono)-frame,round(rate*.005))
        energy=np.sqrt(np.array([mono[p:p+frame].mean() for p in starts]))
        peaks,_=find_peaks(energy,distance=round(.18/.005),prominence=energy.max()*.015)
        assert len(peaks)>=3
        times=starts[peaks]/rate
        assert np.median(np.diff(times[:4]))==pytest.approx(.24,abs=.025)
    elif cid=='W08':
        assert np.max(np.abs(x[round(1.27*rate):round(1.82*rate)]))<1e-5
        assert np.max(np.abs(x[round(1.87*rate):round(2.0*rate)]))>.001
    else:
        assert len(case.sequence.events)==2
        assert case.sequence.events[1].duration_seconds==pytest.approx(3*case.sequence.events[0].duration_seconds)
