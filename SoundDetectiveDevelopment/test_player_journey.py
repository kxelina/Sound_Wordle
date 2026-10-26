"""Public startup, isolated interactive lessons and immutable case reviews."""

import copy
import importlib.util
import os
from pathlib import Path
import sys

os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
GAME=Path(__file__).resolve().parents[1]/'SoundDetective'
sys.path.insert(0,str(GAME))
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtWidgets import QApplication
from sound_detective.audio.preview import PreviewAudio
from sound_detective.audio.models import SoundSettings
from sound_detective.audio.matching import MatchResult
from sound_detective.game.availability import music_availability
from sound_detective.game.debrief import Debrief,build_debrief
from sound_detective.game.player_journey import JourneyStore
from sound_detective.game.sound_categories import SourceSession,load_source_cases
from sound_detective.game.hidden_sound import HiddenSession,load_hidden_case,parameters
from sound_detective.game.melody import Draft,MelodyCase,MelodySession
from sound_detective.ui.debrief import DebriefPanel
from sound_detective.ui.tutorial import TutorialPanel
from sound_detective.ui.studio import StudioWindow
from test_features import Player,Renderer


@pytest.fixture(scope='session')
def app():
    result=QApplication.instance() or QApplication([])
    for name in ('segoeui.ttf','msyh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
    result.setFont(QFont('Microsoft YaHei UI',10))
    return result


def test_music_is_optional_but_core_content_is_required(tmp_path):
    from sound_detective.diagnostics import collect_diagnostics
    import shutil
    for name in ('content','assets','supercollider'):
        shutil.copytree(GAME/name,tmp_path/name,ignore=shutil.ignore_patterns('M01-evidence.wav'))
    assert not music_availability(root=tmp_path).available
    report=collect_diagnostics(root=tmp_path,probe_audio=False)
    assert report['ok']
    assert next(c for c in report['checks'] if c['code']=='optional_music')['status']=='warning'
    assert next(c for c in report['checks'] if c['code']=='content')['status']=='ok'
    (tmp_path/'assets/audio/ui-click.wav').unlink()
    report=collect_diagnostics(root=tmp_path,probe_audio=False)
    assert not report['ok']
    assert next(c for c in report['checks'] if c['code']=='content')['status']=='error'


def test_public_package_allowlist():
    spec=importlib.util.spec_from_file_location('sd_package',GAME/'launcher/package_release.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    public={p.relative_to(GAME).as_posix() for p in module.game_files(public=True)}
    assert 'assets/audio/ui-click.wav' in public
    assert 'content/music_cases/M01.json' in public
    assert 'content/music_cases/assets/M01-evidence.wav' not in public
    assert not any(p.startswith('source/') and p!='source/README.md' for p in public)
    assert not any(p.endswith('.mp3') for p in public)
    if any((GAME/'source').glob('*.mp3')):
        assert any(p.startswith('source/') and p.endswith('.mp3') for p in (q.relative_to(GAME).as_posix() for q in module.game_files()))


def test_sc_process_alias_keeps_same_file_and_missing_path_falls_back(tmp_path):
    from sound_detective.audio.sc_client import process_executable
    executable=tmp_path/'engine with spaces 引擎'/('sclang.exe')
    executable.parent.mkdir();executable.write_bytes(b'alias identity probe')
    alias=Path(process_executable(str(executable)))
    assert alias.samefile(executable)
    assert len(str(alias))<=len(str(executable))
    missing=str(tmp_path/'not-present/sclang.exe')
    assert process_executable(missing)==missing


def test_sc_launch_does_not_expand_alias_before_process_start(monkeypatch,tmp_path):
    from sound_detective.audio import sc_client
    engine=sc_client.SCEngine(runtime_dir=tmp_path)
    alias='C:/bundled-engine-short/sclang.exe'
    calls=[]
    monkeypatch.setattr(sc_client,'process_executable',lambda path:alias)
    class Process:
        returncode=0
        def __init__(self,command,**options):
            calls.append((command,options['cwd']))
            options['stdout'].write(b'compiled successfully')
        def wait(self,timeout=None):return 0
    monkeypatch.setattr(sc_client.subprocess,'Popen',Process)
    assert engine._run([str(engine.sclang),'-D','script.scd'],'alias.log',1)=='compiled successfully'
    assert calls==[([alias,'-D','script.scd'],Path(alias).parent)]


def heard(panel,renderer,*,source=False):
    panel.play()
    revision=panel._revision
    renderer.ready.emit(revision,{'now':PreviewAudio(Path('dummy.wav'),Path('dummy.wav'),False)})
    panel.player.state_changed.emit('playing','now')


@pytest.mark.parametrize('language',['en','zh-Hant'])
def test_tutorial_requires_real_actions_and_keeps_game_progress(app,tmp_path,language):
    sentinel=tmp_path/'T01.json';sentinel.write_text('existing case progress','utf-8')
    store=JourneyStore(tmp_path/'player-journey.json')
    tone,source,player=Renderer(),Renderer(),Player()
    panel=TutorialPanel(store,language=language,tone_renderer=tone,source_renderer=source,player=player)
    panel.resize(1180,610);panel.show();app.processEvents()
    finished=[];panel.finished.connect(finished.append)
    try:
        assert not panel.next_button.isEnabled()
        heard(panel,tone);assert panel.next_button.isEnabled();panel.next()
        assert store.tutorial['step']==1 and not panel.next_button.isEnabled()
        panel.release.setValue(.12);assert not panel.next_button.isEnabled()
        heard(panel,tone);panel.next();assert store.tutorial['step']==2
        panel.h2.setValue(.5);heard(panel,tone);panel.next();assert store.tutorial['step']==3
        panel._curve_changed(76.5,9,.18)
        heard(panel,source);panel.next();assert store.tutorial['step']==4
        assert not panel.next_button.isEnabled()
        panel._submit();assert panel.next_button.isEnabled()
        panel.next();assert finished==[True]
        assert sentinel.read_text('utf-8')=='existing case progress'
        assert store.tutorial['completed']
        assert all(b.toolTip() for b in (panel.next_button,panel.back_button,panel.skip_button,panel.practice,panel.play_ab))
    finally:panel.shutdown();panel.close()
    assert JourneyStore(store.path).tutorial['completed']


def test_tutorial_skip_replay_and_stale_audio(app,tmp_path):
    store=JourneyStore(tmp_path/'journey.json');tone,source,player=Renderer(),Renderer(),Player()
    panel=TutorialPanel(store,tone_renderer=tone,source_renderer=source,player=player)
    try:
        panel.play();old=panel._revision
        panel.release.setValue(.2)
        panel._ready(tone,old,{'now':PreviewAudio(Path('x'),Path('x'),False)})
        assert not player.items
        panel.skip();assert not JourneyStore(store.path).should_offer_tutorial
        store.tutorial['completed']=True
        panel.start(replay=True)
        assert store.tutorial['step']==0 and store.tutorial['release']==.85
        assert store.tutorial['completed']
    finally:panel.shutdown()


@pytest.mark.parametrize('language',['en','zh-Hant'])
@pytest.mark.parametrize('step',range(5))
def test_tutorial_controls_and_navigation_fit(app,tmp_path,language,step):
    store=JourneyStore(tmp_path/'journey.json');store.tutorial['step']=step
    panel=TutorialPanel(store,language=language,tone_renderer=Renderer(),source_renderer=Renderer(),player=Player())
    panel.setStyleSheet(__import__('sound_detective.ui.studio',fromlist=['STYLE']).STYLE)
    panel.setFixedSize(1180,610);panel.show();app.processEvents()
    try:
        for button in (panel.play_current,panel.play_contrast,panel.play_ab,panel.stop_button,panel.next_button,panel.skip_button):
            assert panel.rect().contains(button.mapTo(panel,button.rect().bottomRight()))
        if step==3:
            assert panel.curve_box.rect().contains(panel.length.mapTo(panel.curve_box,panel.length.rect().bottomRight()))
    finally:panel.shutdown();panel.close()


def source_solution(case):
    session=SourceSession(case);session.submit();session.update(case.target);session.hints=2;session.submit()
    return session


@pytest.mark.parametrize('case',load_source_cases(),ids=lambda c:c.id)
def test_first_clear_review_persists_and_history_cannot_forge_final(case,tmp_path):
    session=source_solution(case)
    record=build_debrief(case,session,seconds=12)
    assert all(v==100 for v in record.after.values()) and record.attempts==2
    assert record.clips['final']['patch']==case.target.to_dict()
    store=JourneyStore(tmp_path/'journey.json');store.remember(record)
    session.update(case.initial)
    for _ in range(35):session.submit()
    old=build_debrief(case,session)
    assert old.clips['final'] is None and all(v is None for v in old.after.values())
    store.remember(old)
    loaded=JourneyStore(store.path)
    assert loaded.reviews[case.id]==record
    assert Debrief.from_dict(record.to_dict())==record


def test_locked_reviews_and_melody_empty_start():
    case=load_hidden_case();session=HiddenSession()
    with pytest.raises(ValueError):build_debrief(case,session)
    session.unlocked=2;session.update(parameters(case.reference));session.submit()
    assert build_debrief(case,session).clips['final']
    case=MelodyCase();session=MelodySession();session.unlocked=2
    session.update(Draft(case.pattern,case.reference));session.submit()
    record=build_debrief(case,session)
    assert record.clips['initial'] is None and record.clips['final']
    session.set_mode('free')
    with pytest.raises(ValueError):build_debrief(case,session)


def test_journey_invalid_backup_and_independent_case_file(tmp_path):
    formal=tmp_path/'W03.json';formal.write_text('untouched','utf-8')
    path=tmp_path/'journey.json';path.write_text('{broken','utf-8')
    store=JourneyStore(path)
    assert store.warning=='backup' and list(tmp_path.glob('journey.invalid-*.json'))
    assert store.save() and formal.read_text('utf-8')=='untouched'
    case=load_source_cases()[0];record=build_debrief(case,source_solution(case))
    data=record.to_dict();data['clips']['target']={'type':'file','path':'C:/secret'}
    with pytest.raises(ValueError):Debrief.from_dict(data)


def test_debrief_playback_is_read_only_cancellable_and_bilingual(app,tmp_path):
    case=load_source_cases()[0];session=source_solution(case);saved=copy.deepcopy(session.to_dict())
    record=build_debrief(case,session)
    tone,source,music,player=Renderer(),Renderer(),Renderer(),Player()
    panel=DebriefPanel(tone_renderer=tone,source_renderer=source,music_renderer=music,player=player)
    panel.resize(1180,610);panel.show()
    try:
        panel.load(record,case);panel.play(('initial','final','target'))
        revision=panel._revision
        assert len(source.requests[-1][1][0])==3
        source.ready.emit(revision,{key:PreviewAudio(Path('x'),Path('x'),False) for key in ('initial','final','target')})
        assert len(player.items)==3
        panel.stop();assert not player.items
        panel.play(('target',));old=panel._revision;panel.stop()
        panel._ready(source,old,{});assert not player.items
        panel.translate('zh-Hant');app.processEvents()
        assert '結案' in panel.heading.text()
        assert panel.audio_buttons['final'].toolTip()
        assert session.to_dict()==saved
    finally:panel.shutdown();panel.close()


def test_studio_first_visit_and_existing_progress_tutorial(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path/'fresh',animation_ms=0)
    w.show();app.processEvents()
    try:
        w.start_game();assert w.page=='tutorial'
        w.tutorial_panel.skip();assert w.page=='room'
        w._show_page('menu');w.start_game();assert w.page=='room'
        w._show_page('menu');w.tutorial_button.click();assert w.page=='tutorial'
    finally:w.close();app.processEvents()
    old=tmp_path/'existing';old.mkdir();(old/'T01.json').write_text('existing save','utf-8')
    w=StudioWindow(progress_dir=old,animation_ms=0)
    try:w.start_game();assert w.page=='room'
    finally:w.close();app.processEvents()


def test_studio_auto_review_free_mode_and_first_snapshot(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0)
    w.resize(1280,720);w.volume_slider.setValue(0);w.show();app.processEvents()
    try:
        assert w._accept_case('W04')
        clock=[100.];w._play_clock=lambda:clock[0]
        w._show_page('desk');w._activate_device('synth')
        c=w.controller;c._restore_edit(c.case.target,record=True)
        w._device_started=100.;clock[0]=120.;c._submit();app.processEvents()
        assert w.page=='review' and w._case_journey().reviews['W04'].seconds==20
        saved=w._case_journey().reviews['W04'].to_dict()
        journey_path=w._case_journey().path
        w._leave_review();c._restore_edit(c.case.initial,record=True);c._submit();app.processEvents()
        assert w.page=='device'
        assert w.open_review() and w.debrief_panel.record.to_dict()==saved
        w._review_cases();assert w.page=='board'
        assert w.open_free_composition()
        assert not w._review_available() and not w.open_review()
    finally:w.close();app.processEvents()
    assert JourneyStore(journey_path).reviews['W04'].to_dict()==saved


def test_tone_signal_opens_new_review(app,tmp_path):
    from sound_detective.ui.device_panel import ToneDevicePanel
    factory=lambda **kwargs:ToneDevicePanel(**kwargs,player=Player(),renderer=Renderer())
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0,tone_factory=factory)
    try:
        w._accept_case('T01');w._show_page('desk');w._activate_device('synth')
        c=w.controller;c.session.update(**c.case.parameters(c.case.reference));c._sync_controls()
        c._submission_token=c.session.begin_submission();c._revision=c._match_revision=1
        result=MatchResult(100,100,100,100,True,('close',),{},c.case.comparison)
        c._matched(1,result);app.processEvents()
        assert w.page=='review'
        assert w.debrief_panel.record.case_id=='T01'
        assert w.journey.reviews['T01'].clips['final']['settings']==c.case.reference.to_dict()
    finally:w.close();app.processEvents()


def test_music_clear_keeps_full_song_loop_and_review_is_manual(app,tmp_path):
    from dataclasses import replace
    from sound_detective.ui.device_panel import MusicDevicePanel
    from sound_detective.game.music_cases import MusicSettings
    from sound_detective.game.music_repair import RepairSettings
    if not music_availability().available:pytest.skip('Requires local M01 recordings')
    factory=lambda **kwargs:MusicDevicePanel(**kwargs,player=Player(),renderer=Renderer())
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0,music_factory=factory)
    try:
        assert w.open_music_studio()
        w._show_page('desk');w._activate_device('synth');c=w.controller
        while not c.session.solved:
            settings=c.session.settings;stage=c.session.stage
            if stage=='pitch':settings=MusicSettings(tuple(-r.cents for r in c.case.regions),settings.repair)
            else:settings=MusicSettings(settings.corrections,RepairSettings(replace(settings.repair.estimates,**{stage:getattr(c.case.initial_effects,stage)})))
            c.session.settings=settings;c._sync_controls();c._submit()
        app.processEvents()
        assert w.page=='device' and c.player.items[0].loop
        assert 'M01' in w.journey.reviews
        assert w.open_review() and w.page=='review'
        assert not c.player.items
        panel=w.debrief_panel
        assert panel.record.kind=='music'
        # Three serial renderer jobs, followed by one sequential player queue.
        panel.music_renderer.close()
        panel.music_renderer=Renderer()
        panel.music_renderer.ready.connect(lambda revision,data:panel._ready(panel.music_renderer,revision,data))
        panel.player.close();panel.player=Player()
        panel.play(('initial','final','target'))
        for _ in range(3):panel.music_renderer.ready.emit(panel._revision,PreviewAudio(Path('x'),Path('x'),False))
        assert len(panel.player.items)==3
    finally:w.close();app.processEvents()


def test_menu_and_review_buttons_fit_desktop(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0)
    w.resize(1280,720);w.show();app.processEvents()
    try:
        root=w.menu_proxy.widget()
        for button in (w.start_button,w.tutorial_button,w.settings_button,w.exit_button):
            assert root.rect().contains(button.mapTo(root,button.rect().bottomRight()))
        w.open_tutorial()
        assert w.page=='tutorial'
        w.tutorial_panel.play_current.click()
        w.tutorial_panel.stop()
        w._check_focus()
        assert not w.tutorial_panel._armed
    finally:w.close();app.processEvents()
