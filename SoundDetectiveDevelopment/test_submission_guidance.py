"""Submission deltas and answer-safe, non-blocking equipment guidance."""
import os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SoundDetective'))
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from sound_detective.game.submission_feedback import ScoreSnapshot,describe_submission
from sound_detective.game.cases import load_campaign
from sound_detective.game.sound_categories import load_source_cases,assess_source,score_specs
from sound_detective.game.melody import load_melody_cases,Draft,MelodyPattern,GridNote
from sound_detective.game.parameters import PARAMETERS,replace_parameters
from sound_detective.game.hidden_sound import parameters,assess,settings_from_parameters
from sound_detective.ui.device_panel import ToneDevicePanel
from sound_detective.ui.sound_categories import SourceCaseWindow
from sound_detective.ui.hidden_sound import HiddenSoundWindow
from sound_detective.ui.melody import MelodyWindow
from sound_detective.ui.piano_roll import PianoRoll
from sound_detective.ui.investigation_feedback import SubmissionFeedback,WordleGuessFeedback,guidance
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


def test_non_melody_wordle_cases_show_color_coded_submission_feedback(app,tmp_path):
    hidden=HiddenSoundWindow(save_path=tmp_path/'W01.json',renderer=Renderer(),player=Player())
    try:
        hidden._submit()
        assert not hidden.guess_feedback.isHidden()
        submitted=assess(settings_from_parameters(hidden.session.records[-1]['parameters']))
        expected=['correct' if submitted.passed[0] else
                  'close' if submitted.scores[0]>=60 else 'wrong','locked','locked']
        assert [status for _,status in hidden.guess_feedback.statuses]==expected
        assert not hidden.play_reference.isEnabled()
    finally:hidden.close()

    for case in load_source_cases():
        window=SourceCaseWindow(case=case,save_path=tmp_path/(case.id+'.json'),
                                renderer=Renderer(),player=Player())
        try:
            window._submit()
            scores=assess_source(case,case.initial).scores
            expected=tuple((spec.labels[False],
                'correct' if scores[spec.key]>=85 else 'close' if scores[spec.key]>=60 else 'wrong')
                for spec in score_specs(case)
                if spec.key in scores)
            assert window.guess_feedback.statuses==expected,case.id
            assert not window.guess_feedback.isHidden(),case.id
        finally:window.close()


def test_wordle_guess_feedback_hides_when_no_submission_and_localizes(app):
    feedback=WordleGuessFeedback()
    feedback.show_guesses((('Pitch','correct'),('Density','close'),('Noise','wrong')),'zh-Hant')
    assert feedback.isVisible() and all(text in feedback.text() for text in ('正確','接近','需調整'))
    assert all(color in feedback.text() for color in ('#347a50','#a87824','#58635e'))
    assert feedback.accessibleDescription()=='Pitch: 正確; Density: 接近; Noise: 需調整'
    feedback.show_guesses(())
    assert not feedback.isVisible() and not feedback.statuses


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


def test_piano_roll_feedback_stays_with_notes_after_add_delete_and_move(app):
    roll=PianoRoll()
    roll.set_pattern(MelodyPattern((GridNote(0,1,60),GridNote(4,1,61))))
    roll.feedback_marks=('correct','wrong')

    roll.add(2,60)
    assert roll.feedback_marks==('correct','unscored','wrong')

    roll.selection=0
    roll.delete()
    assert roll.feedback_marks==('unscored','wrong')

    roll.selection=1
    assert roll.replace_selected(GridNote(6,1,61))
    assert roll.feedback_marks==('unscored','wrong')
    assert tuple(note.start for note in roll.pattern.notes)==(2,6)


def test_melody_submission_feedback_survives_structural_edits(app,tmp_path):
    case=next(c for c in load_melody_cases() if c.id=='W02')
    w=MelodyWindow(case=case,save_path=tmp_path/'W02.json',renderer=Renderer(),player=Player())
    try:
        submitted=Draft(MelodyPattern((GridNote(0,1,60),)),case.initial)
        w._update(submitted)
        w._submit()
        original_mark=w.piano.roll.feedback_marks[0]

        w.piano.roll.add(4,60)
        assert w.piano.roll.feedback_marks==(original_mark,'unscored')
        assert 'New notes have no feedback' in w.feedback.text()

        w.piano.roll.selection=0
        w.piano.roll.delete()
        assert w.piano.roll.feedback_marks==('unscored',)
    finally:w.close()


def test_long_guidance_text_can_be_scrolled(app,tmp_path):
    summary=SubmissionFeedback()
    summary.setText('\n'.join(['Detailed submission feedback.']*8))
    assert summary.maximumHeight()>62
    assert summary.sizeHint().height()>62

    w=MelodyWindow(save_path=tmp_path/'W02.json',renderer=Renderer(),player=Player())
    w.resize(1220,760);w.show();app.processEvents()
    try:
        w.feedback.setText('\n'.join(['Detailed melody guidance for the current stage.']*10))
        app.processEvents()
        assert w.feedback.maximumHeight()>90
        assert w.feedback.sizeHint().height()>90
        scrollbar=w.note_scroll.verticalScrollBar()
        w.note_scroll.ensureWidgetVisible(w.feedback)
        app.processEvents()
        assert scrollbar.maximum()>0
    finally:w.close();app.processEvents()


def test_timbre_case_long_guidance_scrolls_in_embedded_device(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0)
    w.resize(1280,720);w.volume_slider.setValue(0);w.show();app.processEvents()
    try:
        assert w._accept_case('T08')
        w._show_page('desk');w._activate_device('synth');app.processEvents()
        panel=w.controller
        panel.clue.setText('\n'.join(
            f'Guidance detail {index}: adjust the highlighted control and listen again.'
            for index in range(24)))
        panel._fit_notes()
        app.processEvents()
        scrollbar=panel.note_scroll.verticalScrollBar()
        assert scrollbar.maximum()>0
        scrollbar.setValue(0)
        proxy_rect=w.device_proxy.subWidgetRect(panel.note_scroll.viewport())
        position=w.view.mapFromScene(w.device_proxy.mapToScene(proxy_rect.center()))
        event=QWheelEvent(position,w.view.viewport().mapToGlobal(position),QPoint(0,0),QPoint(0,-120),
            Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
        QApplication.sendEvent(w.view.viewport(),event)
        app.processEvents()
        assert scrollbar.value()>0
    finally:w.close();app.processEvents()


def test_timbre_submission_results_are_not_vertically_compressed(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0)
    w.resize(1280,720);w.volume_slider.setValue(0);w.show();app.processEvents()
    try:
        assert w._accept_case('T08')
        w._show_page('desk');w._activate_device('synth');app.processEvents()
        panel=w.controller
        panel.session.complete_submission(panel.session.begin_submission(),result(panel.case,40))
        panel._show_match()
        app.processEvents()

        assert panel.score.height()>=panel.score.sizeHint().height()
        assert panel.submission_feedback.height()>=panel.submission_feedback.minimumHeight()

        panel._restore_edit(replace_parameters(panel.case.reference,{'delay_enabled':False}))
        panel.session.complete_submission(panel.session.begin_submission(),result(panel.case,80))
        panel._show_match()
        app.processEvents()
        assert panel.target_info.height()>=panel.target_info.sizeHint().height()
        assert panel.score.height()>=panel.score.sizeHint().height()

        panel.score.setText('\n'.join(f'Result detail {index}: keep adjusting the sound controls.'
                                      for index in range(12)))
        panel._fit_notes()
        app.processEvents()
        scrollbar=panel.note_scroll.verticalScrollBar()
        assert scrollbar.maximum()>0
        scrollbar.setValue(scrollbar.maximum())
        app.processEvents()
        score_bottom=panel.score.mapTo(panel.note_scroll.viewport(),QPoint(0,panel.score.height())).y()
        assert score_bottom<=panel.note_scroll.viewport().height()
    finally:w.close();app.processEvents()


@pytest.mark.parametrize(('cid','expected_rms'),[('W02',.25),('W08',.1)])
def test_melody_preview_level_is_case_specific(app,tmp_path,cid,expected_rms):
    case=next(c for c in load_melody_cases() if c.id==cid)
    renderer=Renderer()
    w=MelodyWindow(case=case,save_path=tmp_path/(cid+'.json'),renderer=renderer,player=Player())
    try:
        w._update(Draft(MelodyPattern((GridNote(0,1,60),)),case.initial))
        w._prepare('current')
        _,_,options=renderer.requests[-1]
        assert options.get('playback_rms',.1)==expected_rms
    finally:w.close()


@pytest.mark.parametrize('cid',['W02','W07','W08'])
def test_piano_roll_cases_give_wordle_like_note_feedback(app,tmp_path,cid):
    case=next(c for c in load_melody_cases() if c.id==cid)
    w=MelodyWindow(case=case,save_path=tmp_path/(cid+'.json'),renderer=Renderer(),player=Player())
    try:
        rhythm=MelodyPattern(tuple(GridNote(note.start,note.length,60) for note in case.pattern.notes))
        w._update(Draft(rhythm,case.initial));w._submit()
        assert w.piano.roll.feedback_marks==('correct',)*len(case.pattern.notes),cid
        assert 'Rhythm guess' in w.feedback.text() and 'Green = exact timing' in w.feedback.text()

        if 1 in case.stages:
            pitch=MelodyPattern(tuple(
                GridNote(note.start,note.length,note.pitch+1 if index==0 else note.pitch)
                for index,note in enumerate(case.pattern.notes)))
            w._update(Draft(pitch,case.initial))
            assert w.piano.roll.feedback_marks==('correct',)*len(case.pattern.notes),cid
            w._submit()
            assert w.piano.roll.feedback_marks==('close',)+('correct',)*(len(case.pattern.notes)-1),cid
            assert 'Pitch guess' in w.feedback.text() and 'Green = exact pitch and timing' in w.feedback.text()

            shorter_last_note=MelodyPattern(tuple(
                GridNote(note.start,note.length-1 if index==len(case.pattern.notes)-1 else note.length,note.pitch)
                for index,note in enumerate(case.pattern.notes)))
            assert w._wordle_marks(Draft(shorter_last_note,case.initial),1)==(
                ('correct',)*(len(case.pattern.notes)-1)+('close',)),cid
        else:
            changed_length=MelodyPattern(tuple(
                GridNote(note.start,note.length+1 if index==0 else note.length,note.pitch)
                for index,note in enumerate(case.pattern.notes)))
            w._update(Draft(changed_length,case.initial))
            assert w.piano.roll.feedback_marks==('correct',)*len(case.pattern.notes),cid
    finally:w.close()


def test_piano_roll_paints_wordle_feedback_colors(app):
    roll=PianoRoll()
    roll.resize(1000,500)
    roll.set_pattern(MelodyPattern((GridNote(0,2,60),GridNote(4,2,60),GridNote(8,2,60))))
    roll.feedback_marks=('correct','close','wrong')
    roll.show();app.processEvents()
    try:
        image=roll.grab().toImage()
        colors=[]
        for note in roll.pattern.notes:
            rect=roll.note_rect(note)
            colors.append(image.pixelColor(round(rect.left()+15),round(rect.top()+2)).name())
        assert colors==['#347a50','#a87824','#58635e']
    finally:roll.close();app.processEvents()


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
