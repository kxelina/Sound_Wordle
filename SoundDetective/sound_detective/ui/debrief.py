"""An in-scene case-closed page with independent, cancellable auditions."""

from PySide6.QtCore import QPointF,QRectF,Qt,Signal
from PySide6.QtGui import QColor,QPainter,QPainterPath,QPen
from PySide6.QtWidgets import (QFrame,QGridLayout,QHBoxLayout,QHeaderView,QLabel,
    QProgressBar,QPushButton,QScrollArea,QTableWidget,QTableWidgetItem,QTabWidget,
    QVBoxLayout,QWidget,QAbstractItemView)

from ..audio.models import SoundSettings
from ..audio.music_preview import MusicPreviewRenderer
from ..audio.playback import AudioPlayer,PlaybackItem
from ..audio.preview import PreviewRenderer
from ..audio.sequence import NoteSequence
from ..audio.source_preview import SourcePreviewRenderer
from ..audio.sound_sources import SourcePatch
from ..game.debrief import Debrief
from ..game.music_cases import MusicSettings
from .hover_help import set_help
from .sound_categories import StatusLabel


class ProgressTrace(QWidget):
    def __init__(self):
        super().__init__()
        self.points=();self.language='en';self.endpoints_only=False;self.setMinimumHeight(145)

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(),QColor('#18241f'))
        area=QRectF(42,18,max(1,self.width()-70),max(1,self.height()-58))
        for score in (0,25,50,75,100):
            y=area.bottom()-score/100*area.height()
            p.setPen(QPen(QColor('#3c4b42'),1));p.drawLine(QPointF(area.left(),y),QPointF(area.right(),y))
            p.setPen(QColor('#c4b997'));p.drawText(4,round(y)+5,str(score))
        if self.points:
            maximum=max(1,max(n for n,v in self.points))
            path=QPainterPath()
            for i,(number,score) in enumerate(self.points):
                point=QPointF(area.left()+number/maximum*area.width(),area.bottom()-score/100*area.height())
                path.moveTo(point) if i==0 else path.lineTo(point)
                p.setBrush(QColor('#e9ca86'));p.setPen(Qt.PenStyle.NoPen);p.drawEllipse(point,3,3)
            p.setPen(QPen(QColor('#e9ca86'),2));p.setBrush(Qt.BrushStyle.NoBrush);p.drawPath(path)
            p.setPen(QColor('#c4b997'));p.drawText(round(area.left()),round(area.bottom()+18),'0')
            p.drawText(QRectF(area.right()-45,area.bottom()+3,50,20),Qt.AlignmentFlag.AlignCenter,str(maximum))
        label='提交次數 · 初始控制估計值位於 0' if self.language=='zh-Hant' else 'Submission · starting-control estimate at 0'
        if self.endpoints_only:label='起點 → 結案 · 分項平均估計' if self.language=='zh-Hant' else 'Starting → cleared · mean component estimate'
        p.setPen(QColor('#d9caa7'));p.drawText(QRectF(42,self.height()-22,area.width(),20),Qt.AlignmentFlag.AlignCenter,label)


class DebriefPanel(QFrame):
    back_requested=Signal()
    cases_requested=Signal()

    def __init__(self,*,language='en',volume=.35,tone_renderer=None,source_renderer=None,music_renderer=None,player=None):
        super().__init__()
        self.setObjectName('panel');self.language=language;self.record=None;self.case=None;self._closed=False
        self._backend=None;self._revision=-1;self._armed=();self._music_jobs=[];self._music_previews={}
        self.player=player or AudioPlayer(self)
        self.tone_renderer=tone_renderer or PreviewRenderer(self)
        self.source_renderer=source_renderer or SourcePreviewRenderer(self)
        self.music_renderer=music_renderer or MusicPreviewRenderer(self)
        for backend in (self.tone_renderer,self.source_renderer,self.music_renderer):
            backend.ready.connect(lambda revision,data,b=backend:self._ready(b,revision,data))
            backend.failed.connect(lambda revision,error,b=backend:self._failed(b,revision,error))
        self.player.error.connect(lambda message:self.status.setText(message))
        self.player.state_changed.connect(self._player_state)
        self.player.set_volume(volume)
        self._build();self.translate(language)

    @property
    def zh(self):return self.language=='zh-Hant'
    def text(self,en,zh):return zh if self.zh else en

    def _build(self):
        layout=QVBoxLayout(self);layout.setContentsMargins(22,14,22,14);layout.setSpacing(7)
        self.heading,self.statistics=QLabel(),QLabel()
        self.heading.setStyleSheet('font-size: 25px; color: #ecd197;')
        self.statistics.setWordWrap(True)
        layout.addWidget(self.heading);layout.addWidget(self.statistics)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        summary=QWidget();summary_layout=QVBoxLayout(summary)
        from .investigation_feedback import SubmissionFeedback
        self.submission_feedback=SubmissionFeedback();self.submission_payload=None
        summary_layout.addWidget(self.submission_feedback)
        self.changes,self.note=QLabel(),QLabel()
        self.changes.setWordWrap(True);self.note.setWordWrap(True)
        summary_layout.addWidget(self.changes);summary_layout.addWidget(self.note)
        self.trace=ProgressTrace();summary_layout.addWidget(self.trace,1)
        self.components=QTableWidget(0,4);self.components.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.components.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.components.verticalHeader().hide()
        self.parameters=QTableWidget(0,3);self.parameters.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.parameters.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.parameters.verticalHeader().hide()
        self.tabs.addTab(summary,'');self.tabs.addTab(self.components,'');self.tabs.addTab(self.parameters,'')
        row=QHBoxLayout();self.audio_buttons={}
        for role in ('initial','final','target'):
            button=QPushButton();button.setObjectName('debrief_'+role)
            button.clicked.connect(lambda checked=False,key=role:self.play((key,)))
            self.audio_buttons[role]=button;row.addWidget(button)
        layout.addLayout(row)
        row=QHBoxLayout()
        self.compare_button,self.stop_button,self.back_button,self.cases_button=QPushButton(),QPushButton(),QPushButton(),QPushButton()
        self.compare_button.clicked.connect(lambda:self.play(tuple(k for k in ('initial','final','target') if self.record and self.record.clips[k])))
        self.stop_button.clicked.connect(self.stop)
        self.back_button.clicked.connect(self.back_requested)
        self.cases_button.clicked.connect(self.cases_requested)
        for button in (self.compare_button,self.stop_button,self.back_button,self.cases_button):row.addWidget(button)
        layout.addLayout(row)
        self.busy=QProgressBar();self.busy.setRange(0,0);self.busy.setFixedHeight(3);self.busy.hide();layout.addWidget(self.busy)
        self.status=StatusLabel();layout.addWidget(self.status)

    def show_submission(self,payload):
        self.submission_payload=payload
        if payload:
            current,previous,options=payload
            # The first-clear summary remains tied to the clearing submission;
            # component captions use the review's own bilingual definitions.
            labels={key:self.record.label(key,self.zh) for key in current.components} if self.record else {}
            self.submission_feedback.show_scores(current,previous,**dict(options,language=self.language,labels=labels))
        else:self.submission_feedback.show_scores()

    def load(self,record,case):
        self.stop()
        if not isinstance(record,Debrief) or record.case_id!=case.id:raise ValueError('Review belongs to another case')
        self.record,self.case=record,case
        self.submission_payload=None
        self.translate(self.language)

    def translate(self,language):
        self.language=language
        self.show_submission(self.submission_payload)
        for i,title in enumerate(self.text(('Case closed','Component progress','Reference controls'),('結案復盤','分項進度','參考設定'))):self.tabs.setTabText(i,title)
        for role,title in zip(('initial','final','target'),self.text(('Play starting sound','Play cleared answer','Play target'),('播放起點聲音','播放通關答案','播放目標'))):
            button=self.audio_buttons[role];button.setText(title);set_help(button,'debrief_'+role,language)
        for button,en,zh,key in (
            (self.compare_button,'Starting → answer → target','起點 → 答案 → 目標','debrief_compare'),
            (self.stop_button,'Stop · Esc','停止 · Esc','stop'),
            (self.back_button,'Back to investigation','返回調查','debrief_back'),
            (self.cases_button,'Choose another case','選擇其他案件','debrief_cases')):
            button.setText(self.text(en,zh));set_help(button,key,language)
        if self.record is None:
            self.heading.setText(self.text('Case review','案件復盤'));return
        r=self.record
        self.heading.setText(self.text('CASE CLOSED  ·  ','案件已結案  ·  ')+r.case_id+' · '+r.title[language])
        seconds=self.text('Time not recorded','未記錄用時') if r.seconds is None else self.text(f'Investigation time {r.seconds:.0f} s',f'調查用時 {r.seconds:.0f} 秒')
        count=f'{r.attempts} recorded submission'+('' if r.attempts==1 else 's')
        self.statistics.setText(self.text(count,f'已記錄 {r.attempts} 次提交')+' · '+seconds+' · '+r.hints[self.zh])
        improvements=sorted((k for k in r.before if r.after[k] is not None),key=lambda k:r.after[k]-r.before[k],reverse=True)[:3]
        self.changes.setText('\n'.join(f'{r.label(key,self.zh)}: {r.before[key]:.1f} → {r.after[key]:.1f}  ·  {r.explanation(key,self.zh)}' for key in improvements))
        self.note.setText(r.note[self.zh]+'\n'+self.text('These are construction-progress values, not percentages of listening similarity. First-clear reviews stay separate from practice edits.','這些數值是合成／修復進度，不是聽覺相似度百分比。首次結案復盤與之後的練習修改分開保留。'))
        self.trace.language=language
        self.trace.points=((0,sum(r.before.values())/len(r.before)),)+r.history
        self.trace.endpoints_only=not bool(r.history)
        if not r.history and all(value is not None for value in r.after.values()):
            self.trace.points+=((max(1,r.attempts),sum(r.after.values())/len(r.after)),)
        self.trace.update()
        self.components.setHorizontalHeaderLabels(self.text(('Part','Starting estimate','Cleared answer','Change'),('分項','起點估計','通關答案','變化')))
        self.components.setRowCount(len(r.before))
        for row,key in enumerate(r.before):
            final=r.after[key]
            for column,value in enumerate((r.label(key,self.zh),f'{r.before[key]:.1f}','—' if final is None else f'{final:.1f}','—' if final is None else f'{final-r.before[key]:+.1f}')):
                self.components.setItem(row,column,QTableWidgetItem(value))
        for role,button in self.audio_buttons.items():button.setEnabled(r.clips[role] is not None)
        self.compare_button.setEnabled(any(r.clips.values()))
        self._show_parameters()
        self.status.setText(self.text('Replay and compare the sounds. Reopening this page never adds a submission.','可以重播和比較聲音，重開此頁不會增加提交次數。'))

    def _show_parameters(self):
        r=self.record
        rows=[]
        if r.kind=='source':
            from ..audio.sound_sources import CONTROLS
            target=SourcePatch.from_dict(r.clips['target']['patch'])
            final=SourcePatch.from_dict(r.clips['final']['patch']) if r.clips['final'] else None
            for spec in CONTROLS[target.recipe]:
                rows.append((spec.labels[self.zh],dict(target.values)[spec.key],dict(final.values)[spec.key] if final else '—'))
        elif r.kind=='melody' and self.case.id!='W02':
            target=NoteSequence.from_dict(r.clips['target']['sequence']).events
            final=NoteSequence.from_dict(r.clips['final']['sequence']).events if r.clips['final'] else ()
            def pitch_name(pitch):return ('C','C#','D','D#','E','F','F#','G','G#','A','A#','B')[pitch%12]+str(pitch//12-1)
            for i,note in enumerate(target):
                actual=final[i] if i<len(final) else None
                label=self.text(f'Note {i+1}',f'第 {i+1} 音')
                rows.extend(((label+self.text(' · onset (s)',' · 起點（秒）'),note.start_seconds,actual.start_seconds if actual else '—'),
                    (label+self.text(' · duration (s)',' · 長度（秒）'),note.duration_seconds,actual.duration_seconds if actual else '—')))
                if 1 in self.case.stages:rows.append((label+self.text(' · pitch',' · 音高'),pitch_name(note.pitch),pitch_name(actual.pitch) if actual else '—'))
        elif r.kind in ('tone','melody'):
            from ..game.parameters import PARAMETERS
            target=SoundSettings.from_dict(r.clips['target']['settings'])
            final=SoundSettings.from_dict(r.clips['final']['settings']) if r.clips['final'] else None
            for key in self.case.editable_parameters:
                spec=PARAMETERS[key]
                rows.append((spec.labels[self.zh] if hasattr(spec,'labels') else key,spec.get(target),spec.get(final) if final else '—'))
        else:
            rows=[(self.text('Stages','修復順序'),'Filter → Delay → Reverb → Pitch',self.text('Completed','已完成'))]
        self.parameters.setHorizontalHeaderLabels(self.text(('Control','Reference','Cleared answer'),('控制項','參照','通關答案')))
        self.parameters.setRowCount(len(rows))
        def display(value):
            if type(value) is bool:return self.text('On','開啟') if value else self.text('Off','關閉')
            if isinstance(value,str) and value in ('lowpass','highpass'):
                return self.text('Low-pass','低通') if value=='lowpass' else self.text('High-pass','高通')
            return f'{value:g}' if isinstance(value,float) else str(value)
        for i,row in enumerate(rows):
            for j,value in enumerate(row):self.parameters.setItem(i,j,QTableWidgetItem(display(value)))

    def play(self,roles):
        if self.record is None or self._closed:return
        roles=tuple(key for key in roles if key in self.record.clips and self.record.clips[key])
        if not roles:return
        self.stop();self._armed=roles;self.busy.show()
        self.status.setText(self.text('Preparing review audio…','正在準備復盤聲音……'))
        try:
            if self.record.kind=='music':
                self._backend=self.music_renderer
                self._music_jobs=list(roles);self._music_previews={};self._next_music()
            elif self.record.kind=='source':
                self._backend=self.source_renderer
                self._revision=self.source_renderer.prepare({key:SourcePatch.from_dict(self.record.clips[key]['patch']) for key in roles})
            else:
                self._backend=self.tone_renderer
                from ..audio.audio_output import audition_options
                self._revision=self.tone_renderer.prepare({key:(SoundSettings.from_dict(self.record.clips[key]['settings']),NoteSequence.from_dict(self.record.clips[key]['sequence'])) for key in roles},**audition_options(self.record.case_id))
        except (OSError,ValueError,RuntimeError) as error:self._failed(self._backend,self._revision,str(error))

    def _next_music(self):
        self._music_role=self._music_jobs.pop(0)
        settings=MusicSettings.from_dict(self.record.clips[self._music_role]['settings'],self.case)
        self._revision=self.music_renderer.prepare(self.case,settings)

    def _ready(self,backend,revision,data):
        if self._closed or backend is not self._backend or revision!=self._revision or not self._armed:return
        if backend is self.music_renderer:
            self._music_previews[self._music_role]=data
            if self._music_jobs:
                try:self._next_music()
                except (OSError,ValueError,RuntimeError) as error:self._failed(backend,self._revision,str(error))
                return
            data=self._music_previews
        roles,self._armed=self._armed,()
        self.busy.hide()
        try:
            names=dict(zip(('initial','final','target'),self.text(('Starting sound','Cleared answer','Target'),('起點聲音','通關答案','目標'))))
            self.player.play([PlaybackItem(data[key].listening_path,names[key]) for key in roles])
        except (OSError,ValueError,RuntimeError,KeyError) as error:self.status.setText(str(error))

    def _failed(self,backend,revision,error):
        if backend is self._backend and revision==self._revision and not self._closed:
            self._armed=();self.busy.hide();self.status.setText(error)

    def _player_state(self,state,label):
        if self._closed:return
        if state in ('playing','loading'):self.status.setText(self.text('Playing: ','正在播放：')+label)
        elif state=='stopped' and not self._armed and self.status.text().startswith(('Playing','正在播放')):self.status.setText(self.text('Stopped.','已停止。'))

    def set_volume(self,value):self.player.set_volume(value)

    def stop(self):
        self._armed=();self._backend=None;self._music_jobs=[];self._music_previews={}
        for renderer in (self.tone_renderer,self.source_renderer,self.music_renderer):renderer.cancel()
        self.player.stop()
        if hasattr(self,'busy'):self.busy.hide()

    def shutdown(self):
        if not self._closed:
            self.stop();self._closed=True;self.player.close()
            for renderer in (self.tone_renderer,self.source_renderer,self.music_renderer):renderer.close()
