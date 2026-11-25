"""Present the tested case controllers as individual studio machines."""

import numpy as np
import soundfile as sf
from PySide6.QtCore import QPointF, QRectF, Qt,QTimer,Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QLabel, QWidget, QPushButton, QGroupBox, QHBoxLayout,QVBoxLayout,QScrollArea,QFrame,QLayout

from .case_one import CaseWindow
from .hardware import PlaybackDeck,InlineChoices


class AudioTraces(QWidget):
    """Plots measured WAVs, available only after a current qualifying submission."""

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(220)
        self.traces = None
        self.message = ""
        self.language = "en"
        self._paths = None

    def clear(self, message):
        self.traces, self._paths, self.message = None, None, message
        self.update()

    def load(self, previews):
        paths = tuple(str(previews[key].raw_path) for key in ("a", "b"))
        if paths == self._paths:
            return
        traces = []
        for path in paths:
            data, rate = sf.read(path, always_2d=True)
            mono = data.mean(axis=1)
            if len(mono) < 2048 or not np.isfinite(mono).all():
                raise ValueError("Invalid analysis audio")
            frames = np.lib.stride_tricks.sliding_window_view(mono, 2048)[::256]
            spectrum = np.abs(np.fft.rfft(frames * np.hanning(2048))).mean(axis=0)
            spectrum = np.maximum(-60, 20 * np.log10(np.maximum(spectrum / max(spectrum.max(), 1e-12), 1e-3)))
            frequency = np.fft.rfftfreq(2048, 1 / rate)
            keep = frequency <= 6000
            hop, width = max(1, round(rate * .005)), max(1, round(rate * .02))
            energy = np.mean(data * data, axis=1)
            integral = np.r_[0, np.cumsum(np.pad(energy, (width // 2, width - width // 2)))]
            start = np.arange(0, len(data), hop)
            envelope = np.sqrt(np.maximum(0, (integral[start + width] - integral[start]) / width))
            envelope /= max(envelope.max(), 1e-12)
            traces.append((frequency[keep] / 6000, (spectrum[keep] + 60) / 60,
                           start / rate, envelope))
        self.traces, self._paths, self.message = traces, paths, ""
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#181f1d"))
        p.setPen(QColor("#e6d9b9"))
        if self.traces is None:
            p.drawText(self.rect().adjusted(18, 12, -18, -12), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)
            return
        zh = self.language == "zh-Hant"
        p.setPen(QColor("#e2bf7b"))
        p.drawText(12, 19, "參照" if zh else "Reference")
        p.setPen(QColor("#72beb2"))
        p.drawText(self.width() // 2, 19, "目前答案" if zh else "Reconstruction")
        total_time = max(trace[2][-1] for trace in self.traces)
        for number, title in enumerate(("頻譜 · 0–6000 Hz" if zh else "Spectrum · 0–6000 Hz",
                                         f"RMS 包絡 · 0–{total_time:.1f} s" if zh else f"RMS envelope · 0–{total_time:.1f} s")):
            r = QRectF(18, 45 + number * ((self.height() - 50) / 2), self.width() - 36, (self.height() - 100) / 2)
            p.setPen(QColor("#b5bbaf"))
            p.drawText(QPointF(r.left(), r.top() - 7), title)
            p.setPen(QPen(QColor("#35433d"), 1))
            for fraction in (0, .25, .5, .75, 1):
                p.drawLine(QPointF(r.left(), r.bottom() - fraction * r.height()), QPointF(r.right(), r.bottom() - fraction * r.height()))
            for index, trace in enumerate(self.traces):
                x, y = trace[:2] if number == 0 else (trace[2] / total_time, trace[3])
                path = QPainterPath()
                for i, (xx, yy) in enumerate(zip(x, y)):
                    point = QPointF(r.left() + xx * r.width(), r.bottom() - yy * r.height())
                    path.moveTo(point) if i == 0 else path.lineTo(point)
                p.setPen(QPen(QColor("#e2bf7b" if index == 0 else "#72beb2"), 1.6))
                p.drawPath(path)


class ToneDevicePanel(CaseWindow):
    device_requested=Signal(str)
    def __init__(self, **kwargs):
        self.device_kind = "synth"
        self._plot_sources = None
        super().__init__(**kwargs)
        self.editor.use_hardware_controls()
        self.target_info.setMinimumHeight(6*self.target_info.fontMetrics().lineSpacing())
        self.score.setMinimumHeight(3*self.score.fontMetrics().lineSpacing())
        self.submission_feedback.reserve_lines(2)
        self.deck = PlaybackDeck(self.play_a, self.play_b, self.stop_button, self.play_ab,compact=True)
        self.target_group.layout().addWidget(self.deck)
        self.player.state_changed.connect(self.deck.set_state)
        self.plot = AudioTraces()
        self.current_group.layout().insertWidget(0, self.plot, 1)
        self.investigation_box=None
        self.theory_index=-1
        if self.case.investigation:
            self.investigation_box=QGroupBox()
            row=QVBoxLayout(self.investigation_box);row.setContentsMargins(8,6,8,6)
            self.question,self.theory_feedback=QLabel(),QLabel()
            self.question.setWordWrap(True);self.theory_feedback.setWordWrap(True)
            self.theories=InlineChoices(columns=3)
            for option in self.case.investigation['options']:self.theories.addItem('',None)
            self.theories.activated.connect(self._choose_theory)
            row.addWidget(self.question);row.addWidget(self.theories);row.addWidget(self.theory_feedback)
            self.current_group.layout().insertWidget(0,self.investigation_box)
        self.target_group.layout().insertWidget(0, self.subtitle)
        if self.case.id.startswith('T'):
            left=self.target_group.layout()
            while left.count():left.takeAt(0)
            notes=QWidget();note_layout=QVBoxLayout(notes);note_layout.setContentsMargins(0,0,0,0)
            note_layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            for widget in (self.subtitle,self.target_info,self.score,self.submission_feedback,self.clue,self.review,self.review_button):note_layout.addWidget(widget)
            note_layout.addStretch()
            self.note_scroll=QScrollArea();self.note_scroll.setWidgetResizable(True);self.note_scroll.setFrameShape(QFrame.Shape.NoFrame)
            self.note_scroll.setMinimumHeight(0);self.note_scroll.setWidget(notes)
            self.help_button=QPushButton();self.help_button.clicked.connect(self._help_and_focus)
            left.addWidget(self.note_scroll,1);left.addWidget(self.help_button);left.addWidget(self.deck)
        from .device_layout import compact_workspace
        compact_workspace(self,(self.compare_button,self.restart_button),(self.action_row,self.volume_row))
        if self.case.id.startswith('T'):
            self.target_group.setMaximumWidth(430)
        self.shortcut.setEnabled(False)
        self.centralWidget().layout().setContentsMargins(10,8,10,6)
        for widget in (self.title, self.progress, self.language, self.volume,
                       self.volume_label, self.volume_value, self.device, self.note):
            widget.hide()
        if self.case.id=='T09':
            volume_row=QHBoxLayout()
            volume_row.addWidget(self.volume_label)
            volume_row.addWidget(self.volume,1)
            volume_row.addWidget(self.volume_value)
            self.target_group.layout().addLayout(volume_row)
            for widget in (self.volume_label,self.volume,self.volume_value):
                widget.show()
        self.present_device("synth")
        self._translate()

    def _help_and_focus(self):
        if not self.session.visible_diagnostics:
            self.clue.setText(('請先提交；達到診斷門檻後會顯示引導。' if self._language=='zh-Hant' else
                'Submit first; guidance is available after the diagnosis threshold.'))
            self.note_scroll.ensureWidgetVisible(self.clue)
            return
        self._show_match()
        device=getattr(getattr(self,'guidance',None),'device','')
        if device:self.device_requested.emit(device)
        self.note_scroll.ensureWidgetVisible(self.clue)

    def _choose_theory(self,index):
        self.theory_index=index
        self._translate_theory()

    def _translate_theory(self):
        if not getattr(self,'investigation_box',None):return
        data=self.case.investigation;lang=self._language
        self.investigation_box.setTitle('聲音成因 · 不計分' if lang=='zh-Hant' else 'Investigate the cause · ungraded')
        self.question.setText(data['question'][lang])
        for button,option in zip(self.theories.buttons,data['options']):
            button.setText(option['label'][lang])
            button.setToolTip('探索聲音成因，不改參數、不增加提交，也不影響分數。' if lang=='zh-Hant' else 'Explore a cause without changing controls, attempts or score.')
        text=data['options'][self.theory_index]['feedback'][lang] if self.theory_index>=0 else ''
        if self.session.first_pass:text=data['completion'][lang]
        self.theory_feedback.setText(text)
        self.investigation_box.updateGeometry()

    def _translate(self):
        super()._translate()
        self.subtitle.setText(self.subtitle.text().replace("match score", "reconstruction progress").replace("匹配分數", "還原進度"))
        if self.case.id=='T09':
            self.volume_label.setText('Knock playback volume' if self._language=='en' else '敲擊聲播放音量')
            self.volume.setToolTip(
                'Changes T09 audio only; Master Volume still controls interface sounds.'
                if self._language=='en' else
                '只調整 T09 音訊；主音量仍控制介面音效。')
        if hasattr(self, "deck"):
            self.deck.translate(self._language)
        self._translate_theory()
        if hasattr(self,'help_button'):
            from .device_layout import help_caption
            help_caption(self.help_button,self._language)
            self.help_button.setToolTip((f'本次提交達 {self.case.hint_threshold:g} 分後顯示診斷，並前往相應設備；不修改答案。' if self._language=='zh-Hant' else
                f'Show this submitted answer’s diagnosis at {self.case.hint_threshold:g}+ and open its device; no settings change.'))

    def present_device(self, device):
        self.device_kind = device
        groups = {"synth": {"harmonics", "envelope", "filter"}, "delay": {"delay"}, "reverb": {"reverb"}}.get(device, set())
        available = self.editor.show_groups(groups)
        self.editor.setVisible(bool(groups) and available)
        self.history.setVisible(device == "analyzer")
        self.plot.setVisible(device == "analyzer")
        if getattr(self,'investigation_box',None):self.investigation_box.setVisible(device in ('synth','delay','tape'))
        self.locked.setVisible(device in ("tape", "synth", "delay", "reverb"))
        if groups and not available:
            self.locked.setText("此案件尚未開放這台設備的控制項。" if self._language == "zh-Hant" else "This machine's controls are locked for this case.")
        elif device == "tape":
            self.locked.setText("點擊左邊兩台錄音機，分別聆聽參照與目前答案。" if self._language == "zh-Hant" else "Click the two tapes on the left to hear the reference and your answer.")
        self._update_plot()

    def _ready(self, revision, previews):
        if revision == self._revision and set(previews) == {"a", "b"}:
            self._plot_sources = previews
        super()._ready(revision, previews)

    def _show_match(self):
        super()._show_match()
        self._fit_notes()
        self._translate_theory()
        if hasattr(self, "plot"):
            self._update_plot()

    def _fit_notes(self):
        if not hasattr(self,'note_scroll'):
            return
        notes=self.note_scroll.widget()
        layout=notes.layout()
        for label in (self.subtitle,self.target_info,self.score,self.submission_feedback,self.clue,self.review):
            width=max(1,label.width())
            height=label.heightForWidth(width) if label.hasHeightForWidth() else label.sizeHint().height()
            label.setMinimumHeight(max(label.minimumHeight(),height))
        layout.invalidate()
        layout.activate()
        notes.setMinimumHeight(layout.sizeHint().height())

    def _matched(self,revision,result):
        before=self.session.attempt_count
        super()._matched(revision,result)
        if self.session.attempt_count!=before and hasattr(self,'note_scroll'):
            QTimer.singleShot(0,lambda:self.note_scroll.ensureWidgetVisible(self.score) if not self._closed else None)

    def _update_plot(self):
        if not hasattr(self, "plot"):
            return
        self.plot.language = self._language
        if (self.device_kind == "analyzer" and self._submission_token is None and self.session.current_is_submitted
                and self.session.last and self.session.last.total >= self.case.hint_threshold and self._plot_sources):
            try:
                self.plot.load(self._plot_sources)
                return
            except (OSError, ValueError, RuntimeError, AttributeError):
                pass
        self.plot.clear("本次提交達 75 分後，可查看這次比較的音訊圖表；重新開啟案件後請再提交。" if self._language == "zh-Hant" else
                        "Submit 75+ to inspect this comparison's audio traces. Submit again after reopening a case.")
