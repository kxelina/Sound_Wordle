"""Submission deltas and answer-safe, non-blocking equipment guidance."""
import os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SoundDetective'))
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from sound_detective.game.submission_feedback import ScoreSnapshot,describe_submission
from sound_detective.game.cases import load_campaign
from sound_detective.game.sound_categories import load_source_cases,assess_source
from sound_detective.game.melody import load_melody_cases,Draft,MelodyPattern,GridNote
from sound_detective.game.parameters import PARAMETERS,replace_parameters
from sound_detective.game.hidden_sound import parameters
from sound_detective.game.availability import music_availability
from sound_detective.ui.device_panel import ToneDevicePanel,MusicDevicePanel
from sound_detective.ui.sound_categories import SourceCaseWindow
from sound_detective.ui.hidden_sound import HiddenSoundWindow
from sound_detective.ui.melody import MelodyWindow
from sound_detective.ui.investigation_feedback import guidance
from sound_detective.ui.studio import StudioWindow
from test_features import Renderer,Player
from test_after_hours import result


@pytest.fixture(scope='session')
def app():return QApplication.instance() or QApplication([])


def snap(total=80,number=2,version='v1',**components):return ScoreSnapshot(total,components,version,number)


@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_delta_baselines_gates_rounding_and_setbacks(language):
    before=snap(76,1,harmonics=60,envelope=92)
    now=snap(84,2,harmonics=76,envelope=92)
    text=describe_submission(now,before,language=language,labels={'harmonics':'Harmonics'})
    assert '76.0 → 84.0' in text and '+8.0' in text and 'Harmonics' in text
    assert 'Harmonics' not in describe_submission(now,before,language=language,labels={'harmonics':'Harmonics'},details=False)
    assert '→' not in describe_submission(now,None,language=language)
    assert '→' not in describe_submission(now,snap(76,1,'v0',harmonics=60,envelope=92),language=language)
    assert '→' not in describe_submission(now,snap(76,0,harmonics=60,envelope=92),language=language)
    rounded=describe_submission(snap(74.999),snap(74.91,1),language=language)
    assert '74.9 → 74.9' in rounded and '+0.0' in rounded
    assert '75.0' not in describe_submission(snap(74.99999999999999),snap(74.91,1),language=language)
    assert '84.0 → 85.0' in describe_submission(snap(84.96),snap(83.96,1),language=language,rounding='round')
    worse=describe_submission(snap(70,2,harmonics=90,envelope=50),before,language=language,labels={'envelope':'ADSR'})
    assert 'ADSR' in worse and '-6.0' in worse


def submit_tone(w):
    w.session.complete_submission(w.session.begin_submission(),result(w.case))
    w._show_match();w._save()


def test_tone_gate_highlights_missing_device_then_clears_stale_hint(app,tmp_path):
    case=next(c for c in load_campaign() if c.id=='T08')
    w=ToneDevicePanel(case=case,save_path=tmp_path/'tone.json',renderer=Renderer(),player=Player())
    w.show();app.processEvents()
    try:
        submit_tone(w);assert w.session.last.total<case.hint_threshold
        assert not guidance(w).keys and not guidance(w).device
        assert 'baseline' in w.submission_feedback.text()
        near=replace_parameters(case.reference,{'delay_enabled':False})
        w._restore_edit(near);submit_tone(w)
        assert w.session.last.total>=case.hint_threshold and not w.session.solved
        assert guidance(w).device=='delay' and 'delay_enabled' in guidance(w).keys
        assert '→' in w.submission_feedback.text()
        w.present_device('delay');app.processEvents()
        switch=w.editor.controls['delay_enabled']
        assert switch.property('hintTarget') and not switch.isChecked()
        QTest.mouseClick(switch,Qt.MouseButton.LeftButton,pos=switch.rect().center());app.processEvents()
        assert switch.isChecked() and w.session.current.effects.delay.enabled
        assert not guidance(w).keys  # the old submitted diagnosis is stale
        assert w.session.attempt_count==2
    finally:w.close();app.processEvents()


def test_async_comparison_restores_controls_before_showing_guidance(app,tmp_path):
    case=next(c for c in load_campaign() if c.id=='T08')
    renderer=Renderer();w=ToneDevicePanel(case=case,save_path=tmp_path/'async.json',renderer=renderer,player=Player())
    try:
        w._restore_edit(replace_parameters(case.reference,{'delay_enabled':False}))
        w._prepare('compare');revision=w._revision
        assert w._submission_token is not None and not w.editor.controls['delay_enabled'].isEnabled()
        renderer.matched.emit(revision-1,result(case))
        assert not w.session.attempt_count and not guidance(w).keys
        renderer.matched.emit(revision,result(case))
        assert w.session.attempt_count==1 and w.editor.controls['delay_enabled'].isEnabled()
        assert guidance(w).keys==('delay_enabled',) and guidance(w).device=='delay'
    finally:w.close()


@pytest.mark.parametrize('language',['en','zh-Hant'])
@pytest.mark.parametrize('cid',['W04','W09'])
def test_category_delta_hint_state_and_reopen(app,tmp_path,language,cid):
    case=next(c for c in load_source_cases() if c.id==cid);path=tmp_path/(cid+'.json')
    w=SourceCaseWindow(case=case,save_path=path,language=language,renderer=Renderer(),player=Player())
    try:
        w._submit();baseline=w.session.to_dict();assert '→' not in w.submission_feedback.text()
        w._hint();assert guidance(w).keys and guidance(w).device=='synth'
        assert w.session.current.to_dict()==baseline['current'] and w.session.attempts==1
        for key in guidance(w).keys:
            assert key in w.case.editable_parameters and w.editor.controls[key].property('hintTarget')
        w._restore_edit(case.target,record=True);w._submit()
        assert w.session.solved and not guidance(w).keys
        assert '→ 100.0' in w.submission_feedback.text()
    finally:w.close()
    w=SourceCaseWindow(case=case,save_path=path,language=language,renderer=Renderer(),player=Player())
    try:
        assert '→ 100.0' in w.submission_feedback.text()
        w.difficulty.setCurrentIndex(0)
        assert not w.submission_feedback.text() and not guidance(w).keys
    finally:w.close()


def test_hidden_sound_hint_opens_only_unlocked_controls_and_counts_only_submits(app,tmp_path):
    w=HiddenSoundWindow(save_path=tmp_path/'W01.json',renderer=Renderer(),player=Player())
    try:
        w._submit();first=w.session.attempts
        assert not guidance(w).keys
        w._hint();assert guidance(w).keys and set(guidance(w).keys)<={'attack','release'}
        assert w.session.attempts==first and not w.play_reference.isEnabled()
        w.editor.controls['attack'].setValue(.02)
        w.editor.controls['release'].setValue(.12)
        w._submit();assert w.session.unlocked>=1 and '→' in w.submission_feedback.text()
        assert not guidance(w).keys  # new stage has no hints yet
        w._hint();assert set(guidance(w).keys)<={'h2','h3','h4'}
    finally:w.close()


def test_harmonic_guidance_avoids_pointing_at_an_already_zero_fader(app,tmp_path):
    from sound_detective.audio.sound_sources import SourcePatch
    case=next(c for c in load_source_cases() if c.id=='W09')
    w=SourceCaseWindow(case=case,save_path=tmp_path/'W09.json',renderer=Renderer(),player=Player())
    try:
        values={'h1':1,'h2':0,'h3':.1,'h4':.8,'h5':.1}
        w._restore_edit(SourcePatch.make('harmonic',values),record=True);w._hint()
        assert guidance(w).keys==('h4',)
        assert dict(w.session.current.values)==values and not w.session.attempts
    finally:w.close()


@pytest.mark.parametrize('cid',['W02','W07','W08'])
def test_melody_rhythm_pitch_highlights_and_free_mode_clear(app,tmp_path,cid):
    case=next(c for c in load_melody_cases() if c.id==cid)
    w=MelodyWindow(case=case,save_path=tmp_path/(cid+'.json'),renderer=Renderer(),player=Player())
    try:
        w._hint();assert w.piano.add_button.property('hintTarget')
        assert not w.session.attempts and not w.play_reference.isEnabled()
        initial=MelodyPattern((GridNote(0,1),))
        w._update(Draft(initial,case.initial));w._submit()
        w._update(Draft(MelodyPattern(tuple(GridNote(n.start,n.length,60) for n in case.pattern.notes)),case.initial))
        w._submit();assert '→' in w.submission_feedback.text()
        if 1 in case.stages:
            w._hint();assert w.piano.pitch.property('hintTarget')
        if cid=='W02':
            w._set_mode('free');assert not w.submission_feedback.text() and not guidance(w).device
            assert not w.piano.pitch.property('hintTarget')
    finally:w.close()


def test_guidance_survives_hover_but_does_not_change_scene_or_edit(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        assert w._accept_case('W09');w._show_page('desk');w._activate_device('synth');app.processEvents()
        c=w.controller;original=c.session.current
        c._hint();assert w.page=='device' and c.session.current==original
        assert w.device_hotspots['synth'].guided
        w.go_back();assert w.page=='desk' and w.device_hotspots['synth'].guided
        item=w.device_hotspots['synth'];item.highlighted=False;item.update()
        assert item.guided
        assert w._accept_case('W07');assert not any(i.guided for i in w.device_hotspots.values())
    finally:w.close();app.processEvents()


def test_first_clear_review_retains_delta_without_practice_replacement(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        w._accept_case('W09');w._show_page('desk');w._activate_device('synth');c=w.controller
        c._submit();c._restore_edit(c.case.target,record=True);c._submit();app.processEvents()
        assert w.page=='review' and '→ 100.0' in w.debrief_panel.submission_feedback.text()
        first=w.debrief_panel.submission_feedback.text()
        w._leave_review();c._restore_edit(c.case.initial,record=True);c._submit();w.open_review()
        assert w.debrief_panel.submission_feedback.text()==first
        w.preferences.language='zh-Hant';w._translate()
        assert '比上次' in w.debrief_panel.submission_feedback.text()
    finally:w.close();app.processEvents()


@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_melody_guidance_inspector_and_buttons_fit_scene(app,tmp_path,language):
    from PySide6.QtGui import QFont
    previous=app.font();app.setFont(QFont('Microsoft YaHei UI',10))
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        w._accept_case('W07');w._show_page('desk');w._activate_device('synth');c=w.controller
        c._update(Draft(MelodyPattern(tuple(GridNote(n.start,n.length,60) for n in c.case.pattern.notes)),c.case.initial))
        c._submit();c._hint();w.preferences.language=language;w._translate();app.processEvents()
        frame=w.device_proxy.widget()
        for control in (c.piano.pitch,c.piano.start,c.piano.length,c.piano.add_button,c.piano.delete_button):
            assert frame.rect().contains(control.mapTo(frame,control.rect().bottomRight()))
    finally:w.close();app.processEvents();app.setFont(previous)


@pytest.mark.skipif(not music_availability().available,reason='Local M01 recording not included')
def test_music_submissions_are_separate_from_checks_and_steps(app,tmp_path):
    w=MusicDevicePanel(save_path=tmp_path/'M01.json',renderer=Renderer(),player=Player())
    try:
        w._check_repair();assert guidance(w).device=='synth' and guidance(w).keys==('filter_enabled',)
        assert not w.session.attempts and not w.submission_feedback.text()
        w._submit();assert 'baseline' in w.submission_feedback.text()
        before=w.submission_feedback.text();w._check_repair();assert w.submission_feedback.text()==before
        from sound_detective.audio.models import SoundSettings
        current=SoundSettings(effects=w.session.settings.repair.estimates)
        w.effects_editor.set_settings(replace_parameters(current,{'filter_enabled':True}))
        w._controls_changed();assert not guidance(w).keys
        w._submit();assert '→' in w.submission_feedback.text() and w.session.attempts==2
        w._restart();assert not w.submission_feedback.text() and not w._submission_snapshots
    finally:w.close()
