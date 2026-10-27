"""Compact equipment pages, direct tape playback and one guidance action."""
import os,sys
from pathlib import Path
os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SoundDetective'))
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton
from sound_detective.ui.hardware import PlaybackDeck
from sound_detective.ui.studio import StudioWindow
from sound_detective.ui.hidden_sound import HiddenSoundWindow
from sound_detective.ui.melody import MelodyWindow
from sound_detective.ui.sound_categories import SourceCaseWindow
from sound_detective.ui.device_panel import ToneDevicePanel,MusicDevicePanel
from sound_detective.game.sound_categories import load_source_cases
from sound_detective.game.cases import load_campaign
from sound_detective.game.parameters import replace_parameters
from sound_detective.game.availability import music_availability
from test_features import Renderer,Player
from test_after_hours import result

@pytest.fixture(scope='session')
def app():
    a=QApplication.instance() or QApplication([])
    for name in ('segoeui.ttf','msyh.ttc','msjh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
    a.setFont(QFont('Microsoft JhengHei UI',10));return a

def inside(root,widget):
    assert widget.isVisible()
    for p in (widget.rect().topLeft(),widget.rect().bottomRight()):assert root.rect().contains(widget.mapTo(root,p))

def test_tapes_route_clicks_keyboard_and_disabled_reference(app):
    buttons=[QPushButton() for _ in range(4)];events=[]
    for name,button in zip(('reference','current','stop','ab'),buttons):button.clicked.connect(lambda checked=False,n=name:events.append(n))
    buttons[0].setEnabled(False)
    deck=PlaybackDeck(*buttons,reference_mode='unlocked');deck.resize(260,160);deck.show();app.processEvents()
    try:
        assert not deck.reference_frame.isVisible() and not any(b.isVisible() for b in (buttons[0],buttons[1],buttons[3]))
        QTest.mouseClick(deck.display,Qt.MouseButton.LeftButton);assert events==['current']
        deck.display.setFocus();QTest.keyClick(deck.display,Qt.Key.Key_Space);assert events==['current','current']
        buttons[0].setEnabled(True);app.processEvents();assert deck.reference_frame.isVisible()
        QTest.mouseClick(deck.reference_display,Qt.MouseButton.LeftButton);assert events[-1]=='reference'
        deck.set_state('playing','Reference');assert deck.reference_display.playing and not deck.display.playing
        deck.set_state('playing','before');assert deck.reference_display.playing and not deck.display.playing
        deck.set_state('playing','Your sound');assert not deck.reference_display.playing and deck.display.playing
        QTest.mouseClick(deck.stop,Qt.MouseButton.LeftButton);assert events[-1]=='stop'
        deck.set_state('stopped','');assert not deck.reference_display.playing and not deck.display.playing
        deck.set_reference_mode('never');assert not deck.reference_frame.isVisible()
        deck.translate('zh-Hant');assert '聲音' in deck.current_title.text() and deck.display.toolTip()
    finally:deck.close()

@pytest.mark.parametrize('language',['en','zh-Hant'])
@pytest.mark.parametrize('cid',['T01','T09','W01','W02','W04','W09','M01'])
def test_scene_workspace_transport_footer_and_hidden_chrome(app,tmp_path,language,cid):
    if cid=='M01' and not music_availability().available:pytest.skip('Optional local music is absent')
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        assert w._accept_case(cid);w._show_page('desk');w._activate_device('synth');w.preferences.language=language;w._translate();app.processEvents()
        c=w.controller;root=w.device_proxy.widget()
        assert w.device_proxy.size().width()==1232 and w.device_proxy.size().height()==624
        machine=getattr(c,'current_group',None) or getattr(c,'machine',None) or getattr(c,'workshop',None) or getattr(c,'tabs',None) or c.editor
        assert machine.width()>=870
        inside(root,c.edit_bar);inside(root,c.deck);inside(root,c.deck.display);inside(root,c.deck.stop)
        bar=c.edit_bar.layout();assert bar.itemAt(0).widget() is c.edit_bar.undo_button and bar.itemAt(1).widget() is c.edit_bar.redo_button
        submit=getattr(c,'compare_button',None) or c.submit_button
        assert bar.itemAt(2).widget() is submit and submit.height()<=30
        inside(root,submit)
        hint=getattr(c,'help_button',None) or getattr(c,'hint_button',None) or c.check_repair_button
        inside(root,hint);assert hint.toolTip() and ('引導' if language=='zh-Hant' else 'guidance') in hint.text()
        assert c.deck.reference_frame.isVisible()==cid.startswith(('T','M'))
        assert not c.deck._reference.isVisible() and not c.deck._current.isVisible()
        for name in ('play_ab','lesson_button','example_button','goto_button','ab_version_button'):
            if hasattr(c,name):assert not getattr(c,name).isVisible()
        if cid=='W02':
            assert not c.tempo_panel.isVisible() and not c.tempo.isVisible()
            assert not any(b.isVisible() for b in c.mode_buttons.values())
            assert c.piano.roll.width()>=800 and c.piano.roll.height()>=270
        w.resize(1600,900);app.processEvents();inside(root,submit);inside(root,hint)
    finally:w.close();app.processEvents()

def test_free_tempo_is_in_workspace_and_survives_board_switch(app,tmp_path):
    w=StudioWindow(progress_dir=tmp_path,animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show()
    try:
        assert w.open_free_composition();w._show_page('desk');w._activate_device('synth');app.processEvents();c=w.controller
        assert c.tempo_panel.isVisible() and c.tempo.isEnabled() and c.machine.isAncestorOf(c.tempo)
        assert c.tempo_label.text().endswith('BPM') and c.tempo.font().pixelSize()>=16
        inside(w.device_proxy.widget(),c.tempo);assert not c.deck.reference_frame.isVisible()
        assert not any(b.isVisible() for b in c.mode_buttons.values())
        c.tempo.setValue(126);assert c.session.current.tempo==126
        assert w._accept_case('W02');w._show_page('desk');w._activate_device('synth');app.processEvents()
        assert not c.tempo_panel.isVisible() and not c.tempo.isVisible()
        assert w.open_free_composition();w._show_page('desk');w._activate_device('synth');app.processEvents()
        assert c.session.current.tempo==126 and c.tempo_panel.isVisible()
    finally:w.close();app.processEvents()

@pytest.mark.parametrize('kind',['hidden','melody','source'])
def test_one_help_click_requests_one_hint_and_opens_device_without_edit(app,tmp_path,kind):
    args=dict(save_path=tmp_path/(kind+'.json'),renderer=Renderer(),player=Player())
    if kind=='source':c=SourceCaseWindow(case=next(x for x in load_source_cases() if x.id=='W09'),**args)
    elif kind=='melody':c=MelodyWindow(**args)
    else:c=HiddenSoundWindow(**args)
    devices=[];c.device_requested.connect(devices.append);c.show();app.processEvents()
    try:
        before=c.session.current;hints=list(c.session.hints) if isinstance(c.session.hints,list) else c.session.hints
        c.hint_button.click();app.processEvents()
        assert devices==['synth'] and c.session.current==before and c.session.attempts==0
        if isinstance(hints,list):assert sum(c.session.hints)==sum(hints)+1
        else:assert c.session.hints==hints+1
        assert not getattr(c,'lesson_button',getattr(c,'example_button',QPushButton())).isVisible()
    finally:c.close();app.processEvents()

def test_tone_help_respects_current_submission_gate_and_opens_diagnosed_device(app,tmp_path):
    case=next(x for x in load_campaign() if x.id=='T08')
    c=ToneDevicePanel(case=case,save_path=tmp_path/'tone.json',renderer=Renderer(),player=Player());devices=[];c.device_requested.connect(devices.append)
    try:
        before=c.session.current;c.help_button.click();assert not devices and c.session.attempt_count==0 and c.session.current==before
        c._restore_edit(replace_parameters(case.reference,{'delay_enabled':False}))
        c.session.complete_submission(c.session.begin_submission(),result(case));c._show_match()
        assert c.session.visible_diagnostics
        c.help_button.click();assert devices==['delay'] and c.session.attempt_count==1 and not c.session.current.effects.delay.enabled
    finally:c.close()
