"""An isolated hands-on lesson; it never submits or changes a game case."""

from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QDoubleSpinBox,QFrame,QGridLayout,QGroupBox,QHBoxLayout,
    QLabel,QProgressBar,QPushButton,QScrollArea,QVBoxLayout,QWidget)

from ..audio.models import SoundSettings,SynthPatch
from ..audio.playback import AudioPlayer,PlaybackItem
from ..audio.preview import PreviewRenderer
from ..audio.sequence import NoteEvent,NoteSequence
from ..audio.source_preview import SourcePreviewRenderer
from ..audio.sound_sources import SourcePatch
from ..game.player_journey import fresh_tutorial
from .hardware import HardwareFader,PlaybackDeck,RackFace,RotaryKnob
from .hover_help import set_help
from .sound_categories import ChirpCurve,StatusLabel


STEPS = (
    ('Listen first','先聽聽看',
     'Click the Your sound tape. Listening and editing never count as submissions.',
     '點擊「你的聲音」錄音機。試聽與調整都不計提交次數。'),
    ('Make a clean ending','讓收尾俐落',
     'Lower Release to 0.25 seconds or less, then audition your edit. A shorter Release removes a lingering tail.',
     '把 Release 降到 0.25 秒以下，再試聽修改。Release 越短，尾音越俐落。'),
    ('Add a brighter edge','加入明亮的邊緣',
     'Raise the H2 fader to at least 0.30, then audition it. Upper harmonics change colour while the fundamental stays fixed.',
     '把 H2 推桿提高到至少 0.30，再試聽。高次諧波能改變音色，基頻仍然固定。'),
    ('Shape a bird-like chirp','塑造鳥鳴般的哨音',
     'Drag the right dot up and left: aim for an ending pitch of MIDI 80 or higher and a length of 0.25 seconds or less. Then listen.',
     '把右端點向上、向左拖：讓結束音高至少為 MIDI 80，長度不超過 0.25 秒，再試聽。'),
    ('Submit a practice answer','提交一次練習',
     'Return to your tone. Keep Release at 0.25 or less and H2 at 0.30 or more, then press Practice submission. This exercise has no effect on case progress.',
     '回到剛才的音色。保持 Release 不超過 0.25、H2 至少 0.30，再按「提交練習」。此練習不影響案件進度。'),
)


class TutorialPanel(QFrame):
    finished=Signal(bool)

    def __init__(self,journey,*,language='en',volume=.35,tone_renderer=None,source_renderer=None,player=None):
        super().__init__()
        self.setObjectName('panel')
        self.journey=journey
        self.language=language
        self._closed=False
        self._revision=-1
        self._backend=None
        self._armed=()
        self._edit_revision=0
        self._heard_revision=-1
        self._practice_passed=False
        self.player=player or AudioPlayer(self)
        self.tone_renderer=tone_renderer or PreviewRenderer(self)
        self.source_renderer=source_renderer or SourcePreviewRenderer(self)
        for backend in (self.tone_renderer,self.source_renderer):
            backend.ready.connect(lambda revision,data,b=backend:self._ready(b,revision,data))
            backend.failed.connect(lambda revision,error,b=backend:self._failed(b,revision,error))
        self.player.error.connect(lambda message:self.status.setText(message))
        self.player.state_changed.connect(self._player_state)
        self.player.set_volume(volume)
        self._build()
        self.start()

    @property
    def state(self):return self.journey.tutorial

    @property
    def zh(self):return self.language=='zh-Hant'

    def text(self,en,zh):return zh if self.zh else en

    def _build(self):
        layout=QVBoxLayout(self)
        layout.setContentsMargins(22,16,22,16)
        self.heading,self.intro=QLabel(),QLabel()
        self.heading.setStyleSheet('font-size: 25px; color: #efd69b;')
        self.intro.setWordWrap(True)
        layout.addWidget(self.heading);layout.addWidget(self.intro)
        columns=QHBoxLayout()
        left=QVBoxLayout()
        notes=QWidget();notes_layout=QVBoxLayout(notes);notes_layout.setContentsMargins(0,0,0,0)
        self.steps_label,self.instruction,self.goal=QLabel(),QLabel(),QLabel()
        for label in (self.steps_label,self.instruction,self.goal):
            label.setWordWrap(True);notes_layout.addWidget(label)
        self.instruction.setStyleSheet('font-size: 17px; color: #f4dfad;')
        notes_layout.addStretch()
        self.note_scroll=QScrollArea();self.note_scroll.setWidgetResizable(True);self.note_scroll.setFrameShape(QFrame.Shape.NoFrame);self.note_scroll.setWidget(notes)
        left.addWidget(self.note_scroll,1)
        self.play_contrast,self.play_current,self.stop_button,self.play_ab=[QPushButton() for _ in range(4)]
        self.play_current.clicked.connect(lambda:self.play(False))
        self.play_contrast.clicked.connect(lambda:self.play(False,contrast=True))
        self.play_ab.clicked.connect(lambda:self.play(True))
        self.stop_button.clicked.connect(self.stop)
        self.deck=PlaybackDeck(self.play_contrast,self.play_current,self.stop_button,self.play_ab,compact=True,
            reference_titles=('Before edit','修改前'))
        self.player.state_changed.connect(self.deck.set_state)
        left.addWidget(self.deck)
        left_widget=QWidget();left_widget.setLayout(left);left_widget.setMaximumWidth(390)
        columns.addWidget(left_widget,4)
        self.rack=RackFace()
        grid=QGridLayout(self.rack)
        self.release_label,self.h2_label=QLabel(),QLabel()
        self.release=QDoubleSpinBox();self.release.setRange(.02,1.2);self.release.setDecimals(2);self.release.setSingleStep(.01);self.release.setSuffix(' s')
        self.release.setObjectName('tutorial_release')
        self.release_knob=RotaryKnob();self.release_knob.setRange(2,120)
        self.h2=QDoubleSpinBox();self.h2.setRange(0,1);self.h2.setDecimals(2);self.h2.setSingleStep(.01)
        self.h2.setObjectName('tutorial_h2')
        self.h2_fader=HardwareFader(Qt.Orientation.Vertical);self.h2_fader.setRange(0,100);self.h2_fader.setMinimumHeight(160);self.h2_fader.setFixedWidth(55)
        self.release_knob.valueChanged.connect(lambda n:self.release.setValue(n/100))
        self.h2_fader.valueChanged.connect(lambda n:self.h2.setValue(n/100))
        for column,(label,control,spin) in enumerate(((self.release_label,self.release_knob,self.release),(self.h2_label,self.h2_fader,self.h2))):
            grid.addWidget(label,0,column,alignment=Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(control,1,column,alignment=Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(spin,2,column)
        self.release.valueChanged.connect(self._tone_changed)
        self.h2.valueChanged.connect(self._tone_changed)
        self.curve_box=QGroupBox()
        curve_layout=QVBoxLayout(self.curve_box)
        self.curve=ChirpCurve();self.curve.setMinimumHeight(195);self.curve.setMaximumHeight(260)
        self.curve.edited.connect(self._curve_changed)
        curve_layout.addWidget(self.curve,1)
        row=QHBoxLayout()
        self.end_label,self.length_label=QLabel(),QLabel()
        self.end_pitch=QDoubleSpinBox();self.end_pitch.setRange(54,106);self.end_pitch.setDecimals(1);self.end_pitch.setSuffix(' MIDI')
        self.length=QDoubleSpinBox();self.length.setRange(.08,.5);self.length.setDecimals(3);self.length.setSingleStep(.005);self.length.setSuffix(' s')
        self.end_pitch.valueChanged.connect(self._curve_numbers)
        self.length.valueChanged.connect(self._curve_numbers)
        for widget in (self.end_label,self.end_pitch,self.length_label,self.length):row.addWidget(widget)
        curve_layout.addLayout(row)
        columns.addWidget(self.rack,6);columns.addWidget(self.curve_box,6)
        layout.addLayout(columns,1)
        self.practice=QPushButton();self.practice.setObjectName('tutorial_practice_submit');self.practice.clicked.connect(self._submit)
        layout.addWidget(self.practice)
        navigation=QHBoxLayout()
        self.back_button,self.skip_button,self.next_button=QPushButton(),QPushButton(),QPushButton()
        self.back_button.clicked.connect(self.back)
        self.skip_button.clicked.connect(self.skip)
        self.next_button.clicked.connect(self.next)
        navigation.addWidget(self.back_button);navigation.addStretch();navigation.addWidget(self.skip_button);navigation.addWidget(self.next_button)
        layout.addLayout(navigation)
        self.busy=QProgressBar();self.busy.setRange(0,0);self.busy.setFixedHeight(3);self.busy.hide();layout.addWidget(self.busy)
        self.status=StatusLabel();layout.addWidget(self.status)

    def start(self,*,replay=False):
        self.stop()
        if replay and self.state['completed']:
            completed=self.state['completed']
            self.journey.tutorial=fresh_tutorial();self.state['completed']=completed
        self._practice_passed=False
        self._edit_revision+=1;self._heard_revision=-1
        for control,value in ((self.release,self.state['release']),(self.h2,self.state['h2'])):
            control.blockSignals(True);control.setValue(value);control.blockSignals(False)
        self._sync()
        self.translate(self.language)

    def _sync(self):
        for control,value in ((self.release_knob,round(self.state['release']*100)),(self.h2_fader,round(self.state['h2']*100))):
            control.blockSignals(True);control.setValue(value);control.blockSignals(False)
        self.curve.values={'pitch':self.state['bird_pitch'],'sweep':self.state['bird_sweep'],'length':self.state['bird_length']}
        self.curve.update()
        for control,value in ((self.end_pitch,self.state['bird_pitch']+self.state['bird_sweep']/2),(self.length,self.state['bird_length'])):
            control.blockSignals(True);control.setValue(value);control.blockSignals(False)

    def _tone_changed(self):
        self.state.update(release=self.release.value(),h2=self.h2.value())
        self._edited()

    def _curve_changed(self,pitch,sweep,length):
        self.state.update(bird_pitch=round(pitch,1),bird_sweep=round(sweep,1),bird_length=round(length,3))
        self._edited()

    def _curve_numbers(self):
        start=self.state['bird_pitch']-self.state['bird_sweep']/2
        end=min(start+12,200-start,max(start-12,120-start,self.end_pitch.value()))
        self._curve_changed((start+end)/2,end-start,self.length.value())

    def _edited(self):
        self.stop();self._edit_revision+=1;self._practice_passed=False
        self._sync();self._refresh();self.journey.save()

    def _requirements_met(self):
        s=self.state
        if s['step']==1:return s['release']<=.25
        if s['step']==2:return s['h2']>=.3
        if s['step']==3:return s['bird_pitch']+s['bird_sweep']/2>=80 and s['bird_length']<=.25
        if s['step']==4:return self._practice_passed
        return True

    def _refresh(self):
        step=self.state['step']
        self.steps_label.setText('\n'.join(('> ' if i==step else '+ ' if i<step else '  ')+f'{i+1}. '+s[self.zh] for i,s in enumerate(STEPS)))
        self.instruction.setText(STEPS[step][2+self.zh])
        self.rack.setVisible(step!=3);self.curve_box.setVisible(step==3)
        self.release_label.setText('Release · '+self.text('ending','收尾'))
        self.h2_label.setText('H2 · '+self.text('colour','音色'))
        for widget in (self.release,self.release_knob):widget.setEnabled(step in (1,4))
        for widget in (self.h2,self.h2_fader):widget.setEnabled(step in (2,4))
        self.practice.setVisible(step==4)
        heard=self._heard_revision==self._edit_revision
        ready=self._requirements_met() and (heard or step==4)
        self.next_button.setEnabled(ready)
        self.next_button.setText(self.text('Choose a case','選擇案件') if step==4 else self.text('Next step','下一步'))
        self.back_button.setEnabled(step>0)
        self.play_contrast.setEnabled(step in (1,2,3));self.play_ab.setEnabled(step in (1,2,3))
        self.goal.setText(self.text('Ready. Continue when you are comfortable.','已完成這一步，可以繼續。') if ready else
                         self.text('Play the tone once to continue.','先播放一次練習音，再繼續。') if step==0 else
                         self.text('Submit the practice tone to check both requirements.','提交練習音色，檢查兩項要求。') if step==4 else
                         self.text('Adjust the highlighted control, then audition the updated sound.','調整目前開放的控制，再試聽修改後的聲音。'))
        self.goal.setStyleSheet('color: '+('#acd0a7' if ready else '#d1c4a3')+';')

    def translate(self,language):
        self.language=language
        self.heading.setText(self.text('Training desk · sound basics','練習工作桌 · 聲音入門'))
        self.intro.setText(self.text('Five short exercises. Your cases, clues and submission counts are kept separate. You can skip and replay this lesson.','五個短練習，與案件、提示及提交記錄完全分開；可以略過，也能重新練習。'))
        self.curve_box.setTitle(self.text('Pitch and duration','音高與長度'));self.curve.language=language;self.curve.update()
        self.end_label.setText(self.text('Ending pitch','結束音高'));self.length_label.setText(self.text('Length','長度'))
        for button,en,zh,key in (
            (self.play_current,'Play my sound','試聽我的聲音','play_current'),
            (self.play_contrast,'Play contrast','播放對比示例','tutorial_contrast'),
            (self.play_ab,'Before → now','修改前 → 現在','tutorial_contrast'),
            (self.stop_button,'Stop · Esc','停止 · Esc','stop'),
            (self.practice,'Practice submission','提交練習','tutorial_submit'),
            (self.back_button,'Previous step','上一步','tutorial_back'),
            (self.skip_button,'Skip tutorial','略過教程','tutorial_skip')):
            button.setText(self.text(en,zh));set_help(button,key,language)
        set_help(self.next_button,'tutorial_next',language)
        for widget in (self.release,self.release_knob):
            widget.setToolTip(self.text('Release controls how long a note fades after it ends.','Release 決定音符結束後的淡出時間。'))
        for widget in (self.h2,self.h2_fader):
            widget.setToolTip(self.text('H2 adds a component at twice the fundamental frequency.','H2 加入基頻兩倍頻率的成分，改變音色。'))
        self.curve.setToolTip(self.text('Drag the endpoints vertically; drag the right endpoint horizontally to change length.','上下拖曳端點改音高；左右拖右端點改長度。'))
        self.end_pitch.setToolTip(self.curve.toolTip());self.length.setToolTip(self.curve.toolTip())
        self.deck.translate(language)
        self.status.setText('')
        self._refresh()

    def _patch(self,contrast=False):
        if self.state['step']==3:
            return SourcePatch.make('bird',{'pitch':74 if contrast else self.state['bird_pitch'],
                'sweep':4 if contrast else self.state['bird_sweep'],'length':.4 if contrast else self.state['bird_length'],
                'spacing':.7,'brightness':.15})
        return SoundSettings(SynthPatch((1,0 if contrast else self.state['h2'],0,0,0,0,0,0),
            .02,.12,.65,.85 if contrast else self.state['release']))

    def play(self,pair=False,*,contrast=False):
        self.stop()
        patch=self._patch(contrast)
        labels=('before','now') if pair else ('before',) if contrast else ('now',)
        if isinstance(patch,SourcePatch):
            backend=self.source_renderer
            requests={key:self._patch(key=='before') for key in labels}
        else:
            backend=self.tone_renderer
            sequence=NoteSequence((NoteEvent(57,.07,.32,100),))
            requests={key:(self._patch(key=='before'),sequence) for key in labels}
        self._backend=backend;self._armed=labels;self.busy.show()
        self.status.setText(self.text('Preparing examples…','正在準備教學示例……'))
        try:self._revision=backend.prepare(requests)
        except (OSError,ValueError,RuntimeError) as error:self._failed(backend,self._revision,str(error))

    def _ready(self,backend,revision,data):
        if self._closed or backend is not self._backend or revision!=self._revision or not self._armed:return
        labels,self._armed=self._armed,()
        self.busy.hide()
        try:self.player.play([PlaybackItem(data[key].listening_path,key) for key in labels])
        except (OSError,ValueError,RuntimeError) as error:self.status.setText(str(error))

    def _failed(self,backend,revision,error):
        if backend is self._backend and revision==self._revision and not self._closed:
            self._armed=();self.busy.hide();self.status.setText(error)

    def _player_state(self,state,label):
        if self._closed:return
        if state in ('playing','loading'):
            name=self.text('Current edit','目前修改') if label=='now' else self.text('Contrast example','對比示例')
            self.status.setText(self.text('Playing: ','正在播放：')+name)
        elif state=='stopped' and not self._armed and self.status.text().startswith(('Playing','正在播放')):
            self.status.setText(self.text('Stopped.','已停止。'))
        if state=='playing' and label=='now':
            self._heard_revision=self._edit_revision;self._refresh()

    def _submit(self):
        if self.state['step']!=4:return
        self.stop()
        self._practice_passed=self.state['release']<=.25 and self.state['h2']>=.3
        score=50*int(self.state['release']<=.25)+50*int(self.state['h2']>=.3)
        self.status.setText(self.text(f'Practice {score}/100 · two construction checks; this is not a similarity percentage.',f'練習 {score}/100 · 兩項合成要求，不是相似度百分比。'))
        self._refresh()

    def next(self):
        if not self.next_button.isEnabled():return
        self.stop()
        if self.state['step']==4:
            self.state.update(completed=True,dismissed=False);self.journey.save();self.finished.emit(True)
        else:
            self.state['step']+=1;self._heard_revision=-1;self._edit_revision+=1
            self._refresh();self.journey.save()

    def back(self):
        if self.state['step']>0:
            self.stop();self.state['step']-=1;self._heard_revision=-1;self._edit_revision+=1
            self._refresh();self.journey.save()

    def skip(self):
        self.stop();self.state['dismissed']=True;self.journey.save();self.finished.emit(False)

    def set_volume(self,value):self.player.set_volume(value)

    def stop(self):
        self._armed=();self._backend=None
        self.tone_renderer.cancel();self.source_renderer.cancel();self.player.stop()
        if hasattr(self,'busy'):self.busy.hide()
        if hasattr(self,'status'):self.status.setText(self.text('Stopped.','已停止。'))

    def shutdown(self):
        if not self._closed:
            self.stop();self._closed=True;self.journey.save()
            self.player.close();self.tone_renderer.close();self.source_renderer.close()
