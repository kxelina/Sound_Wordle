"""Multi-solution harmonic construction: ratios, faders, clues and actual audio."""
import copy
import os
from pathlib import Path
import sys

os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SoundDetective'))
import numpy as np
import pytest
import soundfile as sf
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QSlider
from sound_detective.audio.sc_client import SCEngine
from sound_detective.audio.sound_sources import SourcePatch
from sound_detective.game.harmonic_rules import features
from sound_detective.game.sound_categories import (load_source_cases,assess_source,source_clue,
    SourceSession,save_source_session,load_source_session)
from sound_detective.game.source_learning import with_difficulty,concept_pair,example_control
from sound_detective.game.debrief import build_debrief,Debrief
from sound_detective.game.evidence import EvidenceStore
from sound_detective.ui.sound_categories import SourceCaseWindow
from test_features import Renderer,Player

CASE=next(c for c in load_source_cases() if c.id=='W09')


def patch(**changes):
    return SourcePatch.make('harmonic',dict(dict(CASE.target.values),**changes))


@pytest.fixture(scope='session')
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize('difficulty,count',[('beginner',2),('standard',4),('advanced',5)])
def test_grouped_requirements_solvable_alternatives_and_locked_controls(difficulty,count):
    case=with_difficulty(CASE,difficulty)
    assert len(case.editable_parameters)==count
    assert assess_source(case,case.target).total==100
    assert not assess_source(case,case.initial).passed
    alternative=patch(h2=.10,h3=.60)
    assert alternative!=case.target and assess_source(case,alternative).passed
    scores=[]
    for t in np.linspace(0,1,21):
        values={k:(dict(case.initial.values)[k]*(1-t)+v*t if k in case.editable_parameters else v) for k,v in case.target.values}
        scores.append(assess_source(case,SourcePatch.make('harmonic',values)).total)
    assert all(b>=a-1e-8 for a,b in zip(scores,scores[1:]))
    for key in set(dict(case.target.values))-set(case.editable_parameters):
        with pytest.raises(ValueError):assess_source(case,patch(**{key:0}))


@pytest.mark.parametrize('values',[
    dict(h1=1,h2=0,h3=0,h4=0,h5=0),
    dict(h1=1,h2=.6,h3=0,h4=.4,h5=0),
    dict(h1=0,h2=0,h3=1,h4=0,h5=0),
    dict(h1=.1,h2=0,h3=0,h4=0,h5=1),
    dict(h1=.15,h2=.1,h3=.8,h4=.1,h5=.6),
])
def test_pure_even_fundamental_missing_and_overbright_sounds_do_not_pass(values):
    assert not assess_source(CASE,SourcePatch.make('harmonic',values)).passed


@pytest.mark.parametrize('gain',[.01,.1,.3,.7])
def test_common_amplitude_scaling_preserves_features_and_score(gain):
    scaled=SourcePatch.make('harmonic',{k:v*gain for k,v in CASE.target.values})
    assert features(scaled)==pytest.approx(features(CASE.target))
    assert assess_source(CASE,scaled).total==100


@pytest.mark.parametrize('changes,key,direction',[
    ({'h2':.8,'h3':.1,'h4':.6,'h5':.1},'odd_upper',-1),
    ({'h2':0,'h4':0},'odd_upper',1),
    ({'h2':.01,'h3':.02,'h4':.01,'h5':.01},'upper_power',-1),
    ({'h1':.1},'upper_power',1),
    ({'h2':.01,'h3':.04,'h4':.005,'h5':.015},'upper_power',-1),
    ({'h1':.8,'h2':.075**.5,'h3':0,'h4':0,'h5':.285**.5},'spectral_center',1),
    ({'h1':.8**.5,'h2':.044**.5,'h3':.156**.5,'h4':0,'h5':0},'spectral_center',-1),
])
def test_group_clues_follow_measured_directions(changes,key,direction):
    p=patch(**changes);result=assess_source(CASE,p)
    assert min(result.scores,key=result.scores.get)==key
    assert result.directions[key]==direction
    for language in ('en','zh-Hant'):
        assert source_clue(CASE,p,1,language)
        assert len(source_clue(CASE,p,3,language))>len(source_clue(CASE,p,1,language))
    assert 'Accepted band' in source_clue(CASE,p,3)


def test_fingerprint_difficulty_and_old_case_serialization(tmp_path):
    s=SourceSession(CASE);s.submit();s.update(patch(h2=.1,h3=.6));s.submit()
    path=tmp_path/'中文 saves/W09.json';save_source_session(path,s)
    assert load_source_session(path,CASE).to_dict()==s.to_dict()
    assert 'case_fingerprint' in s.to_dict()
    for field,value in [('case_fingerprint','bad'),('scoring_version','source-bands-v1'),('case','W06')]:
        bad=copy.deepcopy(s.to_dict());bad[field]=value
        with pytest.raises(ValueError):SourceSession.from_dict(bad,CASE)
    with pytest.raises(ValueError):SourceSession.from_dict(s.to_dict(),with_difficulty(CASE,'beginner'))
    legacy=SourceSession(load_source_cases()[0]).to_dict()
    assert 'case_fingerprint' not in legacy and legacy['scoring_version']=='source-bands-v1'
    assert SourceSession.from_dict(legacy,load_source_cases()[0]).to_dict()==legacy


def test_pure_sine_hint_establishes_upper_components_before_odd_even_balance():
    for scale in (0,.01,.1):
        p=patch(h2=.15*scale,h3=.55*scale,h4=.13*scale,h5=.28*scale)
        assert 'pure whistle' in source_clue(CASE,p,1)
        assert '高次諧波能量' in source_clue(CASE,p,1,'zh-Hant')
        assert example_control(CASE,p)=='h3'


def test_silence_is_saved_as_draft_but_not_submitted_or_played(app,tmp_path):
    renderer=Renderer();w=SourceCaseWindow(case=CASE,save_path=tmp_path/'W09.json',renderer=renderer,player=Player())
    try:
        silent=SourcePatch.make('harmonic',dict.fromkeys(dict(CASE.target.values),0))
        w._restore_edit(silent,record=True)
        assert assess_source(CASE,silent).total==0
        w._submit();w._prepare('current');w._prepare('export')
        assert not w.session.attempts and not renderer.requests
        assert 'silence' in w.status.text()
        assert load_source_session(w.save_path,CASE).current==silent
        with pytest.raises(ValueError):w.session.submit()
        w._prepare('example');assert renderer.requests
    finally:w.close()


@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_faders_hidden_target_clue_readout_and_collection(app,tmp_path,language):
    from sound_detective.ui.studio import StudioWindow
    window=StudioWindow(progress_dir=tmp_path,animation_ms=0)
    window.resize(1280,720);window.volume_slider.setValue(0);window.show()
    try:
        window.board.open(None,language);window.board.set_mode('wordle');window.board.set_category('noise')
        assert 'W09' in window.board.cards and window._accept_case('W09')
        window.language_combo.setCurrentIndex(window.language_combo.findData(language))
        window._show_page('desk');window._activate_device('synth');app.processEvents()
        c=window.controller
        assert len(c.case.editable_parameters)==2 and not c.play_reference.isEnabled()
        assert all(isinstance(f,QSlider) and f.orientation()==Qt.Orientation.Vertical for f in c.editor.knobs.values())
        assert not c.feature_readout.isVisible()
        c._hint();c._hint();app.processEvents();assert c.feature_readout.isVisible()
        assert '[' not in c.feature_readout.text()
        c._hint();assert '[' in c.feature_readout.text()
        assert all(widget.toolTip() for widget in c.editor.knobs.values())
        c.editor.controls['h2'].setValue(.10);c.editor.controls['h3'].setValue(.60)
        c._submit();app.processEvents()
        assert c.session.solved and c.play_reference.isEnabled()
        record=build_debrief(c.case,c.session)
        assert set(record.after)=={'odd_upper','upper_power','spectral_center'}
        assert record.label('odd_upper',language=='zh-Hant')!='odd_upper'
        assert Debrief.from_dict(record.to_dict())==record
        assert any(r.case_id=='W09' for _,r in window.evidence_store.entries.values())
        for widget in c.editor.controls.values():
            assert window.device_proxy.widget().rect().contains(widget.mapTo(window.device_proxy.widget(),widget.rect().bottomRight()))
    finally:window.close();app.processEvents()


def test_actual_audio_agrees_with_harmonic_features_and_examples(tmp_path):
    engine=SCEngine(runtime_dir=Path(__file__).parent/'.runtime/wire-engine')
    sounds=[CASE.target,patch(h2=.10,h3=.60),CASE.initial]
    example_key=example_control(CASE,CASE.initial)
    low,high=concept_pair('harmonic',example_key)
    assert [k for k,v in low.values if v!=dict(high.values)[k]]==[example_key]
    sounds.extend((low,high))
    audio=[]
    for i,p in enumerate(sounds):
        path=tmp_path/f'音色 {i}.wav';engine.render_source(p,path)
        x,rate=sf.read(path);audio.append(x)
        assert rate==44100 and x.shape==(158760,2)
        assert np.isfinite(x).all() and .001<abs(x).max()<=.9 and abs(x[-1]).max()<.0001
        stable=x[round(.45*rate):round(.95*rate)].mean(axis=1)
        spectrum=abs(np.fft.rfft(stable))**2
        power=[spectrum[110*k] for k in range(1,6)]
        measured={'odd_upper':(power[2]+power[4])/sum(power[1:]),'upper_power':sum(power[1:])/sum(power),
                  'spectral_center':sum((k+1)*v for k,v in enumerate(power))/sum(power)}
        assert measured==pytest.approx(features(p),abs=.002)
    assert not np.allclose(audio[0],audio[2]) and not np.allclose(audio[-1],audio[-2])
    again=tmp_path/'repeat.wav';engine.render_source(CASE.target,again)
    np.testing.assert_array_equal(sf.read(again)[0],audio[0])
