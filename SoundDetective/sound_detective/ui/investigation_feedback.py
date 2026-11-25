"""Small submission summaries and non-interactive, value-neutral hint rings."""
from html import escape

from PySide6.QtCore import QEvent,QObject,Qt,Signal
from PySide6.QtGui import QColor,QPainter,QPen
from PySide6.QtWidgets import QLabel,QWidget
from ..game.submission_feedback import ScoreSnapshot,describe_submission
from ..game.parameters import PARAMETERS


class WordleGuessFeedback(QLabel):
    COLORS = {
        "correct": ("#347a50", "Correct", "正確"),
        "close": ("#a87824", "Close", "接近"),
        "wrong": ("#58635e", "Needs work", "需調整"),
        "locked": ("#424a46", "Locked", "未開放"),
    }

    def __init__(self):
        super().__init__()
        self.setObjectName("wordle_guess_feedback")
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setWordWrap(True)
        self.statuses = ()
        self.hide()

    def show_guesses(self, guesses, language="en"):
        self.statuses = tuple((label, status) for label, status in guesses)
        if not self.statuses:
            self.clear()
            self.hide()
            self.setAccessibleDescription("")
            return
        zh = language == "zh-Hant"
        tiles = []
        descriptions = []
        for label, status in self.statuses:
            color, english, chinese = self.COLORS[status]
            text = chinese if zh else english
            tiles.append(
                f'<span style="display:inline-block;background-color:{color};'
                f'color:#fff;padding:3px 7px;margin:2px;border-radius:4px;">'
                f'{escape(str(label))} · {text}</span>'
            )
            descriptions.append(f"{label}: {text}")
        self.setText(" ".join(tiles))
        self.setAccessibleDescription("; ".join(descriptions))
        self.show()


class SubmissionFeedback(QLabel):
    def __init__(self):
        super().__init__()
        self.setObjectName('submission_feedback')
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setStyleSheet('font-size: 12px; color: #bdcbb5;')
        self.hide()
        self.payload=None
        self._reserved_lines=1

    def reserve_lines(self,count):
        self._reserved_lines=count
        self.setMinimumHeight(count*self.fontMetrics().lineSpacing()+4)

    def setText(self,text):
        super().setText(text)
        lines=max(self._reserved_lines,text.count('\n')+1) if text else 0
        self.setMinimumHeight(min(62,lines*self.fontMetrics().lineSpacing()+4) if lines else 0)

    def show_scores(self,current=None,previous=None,**options):
        self.payload=(current,previous,options) if current else None
        text=describe_submission(current,previous,**options) if current else ''
        self.setText(text);self.setToolTip(text);self.setVisible(bool(text))


class HintRing(QWidget):
    def __init__(self,target):
        super().__init__(target)
        self.setObjectName('hint_ring')
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.region=None
        target.installEventFilter(self)
        self.setGeometry(target.rect());self.raise_();self.show()

    def eventFilter(self,target,event):
        if event.type() in (QEvent.Type.Resize,QEvent.Type.Show,QEvent.Type.LayoutRequest):
            self.setGeometry(target.rect());self.raise_();self.update()
        return False

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect=self.region() if self.region else self.rect()
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor('#edcf83'),2))
        painter.drawRoundedRect(rect.adjusted(2,2,-2,-2),4,4)


class Guidance(QObject):
    changed=Signal(str)

    def __init__(self,owner):
        super().__init__(owner)
        self.device='';self.keys=();self._rings={}

    def show_targets(self,editor=None,keys=(),device='',extra=()):
        controls=getattr(editor,'controls',{})
        self.keys=tuple(key for key in keys if key in controls and controls[key].isEnabled())
        targets=[]
        for key in self.keys:
            for mapping in ('controls','sliders','knobs'):
                widget=getattr(editor,mapping,{}).get(key)
                if widget is not None:targets.append((widget,None))
        tabs=getattr(editor,'tabs',None)
        if tabs is not None and self.keys:
            group=PARAMETERS[self.keys[0]].group if self.keys[0] in PARAMETERS else None
            groups=getattr(editor,'_tab_groups',())
            if group in groups:
                index=groups.index(group);bar=tabs.tabBar()
                targets.append((bar,lambda b=bar,i=index:b.tabRect(i)))
        targets.extend((widget,None) for widget in extra if widget is not None and widget.isEnabled())
        wanted={widget for widget,_ in targets}
        for widget,ring in tuple(self._rings.items()):
            try:
                ring.setVisible(widget in wanted);widget.setProperty('hintTarget',widget in wanted)
            except RuntimeError:self._rings.pop(widget,None)
        for widget,region in targets:
            if widget not in self._rings:self._rings[widget]=HintRing(widget)
            ring=self._rings[widget];ring.region=region
            widget.setProperty('hintTarget',True);ring.show();ring.raise_();ring.update()
        value=device if targets else ''
        if self.device!=value:self.device=value;self.changed.emit(value)


def guidance(owner):
    if not hasattr(owner,'guidance'):owner.guidance=Guidance(owner)
    return owner.guidance


def progress_control(code):
    if not code.startswith('progress_') or code=='progress_close':return None
    key=code[len('progress_'):].rsplit('_',1)[0]
    return key if key in PARAMETERS else None


def device_for(key):
    group=PARAMETERS[key].group
    return group if group in ('delay','reverb') else 'synth'


def tone_guidance(owner,codes):
    keys=tuple(filter(None,(progress_control(code) for code in codes)))
    if not keys:
        structural={'filter_missing':'filter_enabled','filter_extra':'filter_enabled','filter_family':'filter_mode',
            'delay_missing':'delay_enabled','delay_dry':'delay_mix','delay_extra':'delay_enabled',
            'reverb_missing':'reverb_enabled','reverb_dry':'reverb_mix','reverb_extra':'reverb_enabled'}
        keys=tuple(structural[code] for code in codes if code in structural)
    guidance(owner).show_targets(owner.editor,keys,device_for(keys[0]) if keys else '')
