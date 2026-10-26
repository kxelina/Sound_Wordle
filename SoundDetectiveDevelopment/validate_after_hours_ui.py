"""Scene-pointer and real audio checks for T09, W07 and W08, with muted output."""
import json,os,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ['QT_QPA_PLATFORM']='offscreen';os.environ['SOUND_DETECTIVE_UI_AUDIO']='0'
GAME=Path(os.environ.get('SOUND_DETECTIVE_QA_GAME',str(Path(__file__).resolve().parents[1]/'SoundDetective'))).resolve()
sys.path.insert(0,str(GAME))
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QFont,QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from sound_detective.ui.studio import StudioWindow
from sound_detective.game.melody import Draft,GridNote,MelodyPattern
from sound_detective.audio.sc_client import find_executable
import soundfile as sf

app=QApplication([])
for name in ('segoeui.ttf','msyh.ttc'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+name)
app.setFont(QFont('Microsoft YaHei UI',10))
out=Path(__file__).resolve().parent/'.runtime/after-hours-ui';out.mkdir(parents=True,exist_ok=True)

def wait(predicate,limit=90):
    deadline=time.monotonic()+limit
    while not predicate() and time.monotonic()<deadline:app.processEvents();time.sleep(.01)
    assert predicate(),'Timed out waiting for audio or scene change'

with TemporaryDirectory(dir=out) as folder:
    w=StudioWindow(progress_dir=Path(folder),animation_ms=0);w.resize(1280,720);w.volume_slider.setValue(0);w.show();app.processEvents()
    errors=[]
    def activate(cid,device='synth'):
        assert w._accept_case(cid);w._show_page('desk');w._activate_device(device);app.processEvents()
        c=w.controller;c.player.error.connect(errors.append);c.renderer.failed.connect(lambda r,e:errors.append(e));return c
    def point(widget,p):return w.view.mapFromScene(w.device_proxy.mapToScene(QPointF(widget.mapTo(w.device_proxy.widget(),p.toPoint()))))
    def click(button):
        QTest.mouseClick(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(button,QPointF(button.rect().center())));app.processEvents()
    def drag(widget,a,b):
        QTest.mousePress(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(widget,a))
        QTest.mouseMove(w.view.viewport(),pos=point(widget,b))
        QTest.mouseRelease(w.view.viewport(),Qt.MouseButton.LeftButton,pos=point(widget,b));app.processEvents()

    c=activate('T09','delay');click(c.theories.buttons[2]);assert c.session.attempt_count==0
    for lang in ('en','zh-Hant'):
        w.preferences.language=lang;w._translate();app.processEvents();w.view.grab().save(str(out/('T09-'+lang+'.png')))
    c._restore_edit(c.case.reference);c._prepare('compare')
    wait(lambda:bool(errors) or w.page=='review');assert not errors,errors
    assert c.session.first_pass and c.session.first_pass.total==100

    c=activate('W07');case=c.case
    initial=MelodyPattern((GridNote(0,1),GridNote(6,1)))
    c._update(Draft(initial,case.initial));app.processEvents()
    roll=c.piano.roll;roll.selection=1;roll.selected.emit();c.piano._reveal_selection();app.processEvents()
    rect=roll.note_rect(c.session.current.pattern.notes[1]);desired=roll.note_rect(GridNote(6,3))
    a=QPointF(rect.right()-2,rect.center().y());b=QPointF(desired.right()-2,rect.center().y())
    drag(roll,a,b);assert c.session.current.pattern.notes[1].length==3
    click(c.submit_button);assert c.session.unlocked==1 and not c.session.solved
    for index,moves in ((0,(3,3,1)),(1,(3,1))):
        for rows in moves:
            roll.selection=index;roll.selected.emit();c.piano._reveal_selection();app.processEvents()
            rect=roll.note_rect(c.session.current.pattern.notes[index])
            drag(roll,rect.center(),rect.center()+QPointF(0,-rows*roll.ROW))
    assert c.session.current.pattern==case.pattern,c.session.current.pattern
    for lang in ('en','zh-Hant'):
        w.preferences.language=lang;w._translate();app.processEvents();w.view.grab().save(str(out/('W07-'+lang+'.png')))
    click(c.submit_button);app.processEvents();assert w.page=='review'
    w._leave_review();c._prepare('ab')
    wait(lambda:bool(errors) or c.player.state=='playing');assert not errors,errors
    wait(lambda:c.player.state=='stopped' and c._armed is None)

    c=activate('W08');case=c.case
    wrong=MelodyPattern(tuple(GridNote(n,1) for n in (0,4,8,12)))
    c._update(Draft(wrong,case.initial));click(c.submit_button);assert c.session.attempts==1 and not c.session.solved
    c._hint()
    for lang in ('en','zh-Hant'):
        w.preferences.language=lang;w._translate();app.processEvents();w.view.grab().save(str(out/('W08-'+lang+'.png')))
    roll=c.piano.roll;rect=roll.note_rect(c.session.current.pattern.notes[2])
    QTest.mouseClick(w.view.viewport(),Qt.MouseButton.RightButton,pos=point(roll,rect.center()));app.processEvents()
    assert c.session.current.pattern==case.pattern
    click(c.submit_button);app.processEvents();assert w.page=='review'
    assert set(w.evidence_store.entries)=={'T09:advanced','W07:advanced','W08:advanced'}
    w.open_cabinet();panel=w.cabinet_panel
    panel.selector.setCurrentIndex(panel.selector.findData('W07:advanced'));panel.tabs.setCurrentIndex(2);app.processEvents()
    w.view.grab().save(str(out/'collected-notes-zh-Hant.png'))
    panel.source_renderer.failed.connect(lambda r,e:errors.append(e));panel.tone_renderer.failed.connect(lambda r,e:errors.append(e))
    panel.export_final();wait(lambda:bool(errors) or panel.status.text().startswith(('Exported: ','已匯出：')));assert not errors,errors
    exported=next((Path(folder)/'evidence-exports').glob('*.wav'));x,rate=sf.read(exported)
    assert rate==44100 and len(x)>0
    report={'real_knock_submit':True,'ungraded_theory_click':True,'doorbell_pointer_length_and_pitch':True,
            'doorbell_two_stage_clear':True,'silent_beat_rejects_extra':True,'pointer_removes_extra_note':True,
            'actual_ab_completed':True,'three_collected_answers':True,'collected_melody_export':True,
            'sample_rate':rate,'volume':0,'errors':errors,'game_root':str(GAME),'python_executable':sys.executable,
            'sclang':str(find_executable('sclang.exe')),'scsynth':str(find_executable('scsynth.exe'))}
    w.close();app.processEvents()
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)
