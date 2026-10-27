"""T09 playback trim: louder auditions, identical synthesis and grading."""
import os,sys,threading
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SoundDetective'))
import numpy as np
import pytest
import soundfile as sf
from PySide6.QtWidgets import QApplication
from sound_detective.audio.audio_output import audition_options
from sound_detective.audio.preview import PreviewRenderer
from sound_detective.audio.sc_client import SCEngine
from sound_detective.game.cases import load_campaign
from sound_detective.game.session import SessionState
from sound_detective.game.debrief import build_debrief
from sound_detective.game.evidence import EvidenceStore
from sound_detective.ui.device_panel import ToneDevicePanel
from sound_detective.ui.debrief import DebriefPanel
from sound_detective.ui.evidence import EvidencePanel
from test_features import Renderer,Player
from test_after_hours import tone_submit

CASE=load_campaign()[-1]

@pytest.fixture(scope='session')
def app():return QApplication.instance() or QApplication([])


def test_trim_is_t09_only_and_does_not_change_case_data():
    assert CASE.id=='T09' and audition_options('T09')=={'playback_rms':.18}
    assert all(not audition_options(key) for key in ('T01','T08','W09','W01','M01',None))
    assert CASE.sequence.events[0].pitch==45 and CASE.sequence.events[0].velocity==110
    assert CASE.revision==1


@pytest.mark.parametrize('cid',['T01','T09'])
def test_all_audition_buttons_and_comparison_use_the_same_profile(app,tmp_path,cid):
    case=next(c for c in load_campaign() if c.id==cid);renderer=Renderer()
    w=ToneDevicePanel(case=case,save_path=tmp_path/(cid+'.json'),renderer=renderer,player=Player())
    try:
        for mode in ('a','b','ab','compare'):
            w._prepare(mode)
            assert renderer.requests[-1][2].get('playback_rms',.1)==(.18 if cid=='T09' else .1)
        assert not w.session.attempt_count
    finally:w.close()


def test_review_and_collected_export_share_the_t09_profile(app,tmp_path):
    session=SessionState(CASE);tone_submit(session,True);record=build_debrief(CASE,session)
    backend=Renderer();panel=DebriefPanel(tone_renderer=backend,source_renderer=Renderer(),music_renderer=Renderer(),player=Player())
    try:
        panel.load(record,CASE);panel.play(('initial','final','target'))
        assert backend.requests[-1][2]['playback_rms']==.18
    finally:panel.shutdown();panel.close()
    store=EvidenceStore(tmp_path/'cabinet.json');store.remember(record)
    backend=Renderer();panel=EvidencePanel(store,load_campaign(),tone_renderer=backend,source_renderer=Renderer(),music_renderer=Renderer(),player=Player())
    try:
        panel.export_final();assert backend.requests[-1][2]['playback_rms']==.18
    finally:panel.shutdown();panel.close()


def test_invalid_profile_is_rejected_before_work_starts(app,tmp_path):
    r=PreviewRenderer(cache_parent=tmp_path)
    try:
        for invalid in (float('nan'),True,0,.3):
            with pytest.raises(ValueError):r.prepare({'a':(CASE.reference,CASE.sequence)},playback_rms=invalid)
    finally:r.close()


def test_real_t09_is_louder_with_no_clipping_raw_change_or_score_change(app,tmp_path):
    r=PreviewRenderer(cache_parent=tmp_path,engine_factory=lambda:SCEngine(runtime_dir=tmp_path/'engine'))
    request={'a':(CASE.reference,CASE.sequence),'b':(CASE.initial,CASE.sequence)}
    try:
        before,score_before=r._work(request,threading.Event(),True,CASE.comparison)
        after,score_after=r._work(request,threading.Event(),True,CASE.comparison,playback_rms=.18)
        assert score_before==score_after
        for key in request:
            raw_before,rate=sf.read(before[key].raw_path);raw_after,_=sf.read(after[key].raw_path)
            np.testing.assert_array_equal(raw_before,raw_after)
            x,_=sf.read(before[key].listening_path);y,_=sf.read(after[key].listening_path)
            gain=np.sum(x*y)/np.sum(x*x)
            assert 4<=20*np.log10(gain)<=5.2
            assert np.max(np.abs(y-gain*x))<3e-7
            assert rate==44100 and x.shape==y.shape and np.max(np.abs(y))<=.900001
            assert np.isfinite(y).all() and not before[key].cache_hit and not after[key].cache_hit
        hit,_=r._work(request,threading.Event(),False,playback_rms=.18)
        assert all(item.cache_hit for item in hit.values())
    finally:r.close()
