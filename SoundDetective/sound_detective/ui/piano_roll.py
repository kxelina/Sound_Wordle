"""Shared challenge/composition piano roll with mode-specific pitch/time bounds."""

from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QValidator
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QLayout, QScrollArea,QSizePolicy)

from ..game.melody import GridNote, MelodyPattern, STEPS, LOW_PITCH, HIGH_PITCH
from ..game.composition import CompositionNote,CompositionPattern,LOW,HIGH


def pitch_name(pitch):
    return f"{('C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B')[pitch % 12]}{pitch // 12 - 1}"


class PitchBox(QSpinBox):
    """Type a note name or MIDI value; no popup inside the graphics proxy."""

    def __init__(self):
        super().__init__()
        self.setRange(LOW_PITCH, HIGH_PITCH)
        self.setKeyboardTracking(False)

    def textFromValue(self, value):
        return pitch_name(value)

    def _parsed(self, text):
        text = text.strip().upper().replace("♯", "#")
        for pitch in range(self.minimum(), self.maximum() + 1):
            if text in (pitch_name(pitch).upper().replace("♯", "#"), str(pitch)):
                return pitch
        return None

    def valueFromText(self, text):
        parsed = self._parsed(text)
        return self.value() if parsed is None else parsed

    def validate(self, text, position):
        if self._parsed(text) is not None:
            return QValidator.State.Acceptable, text, position
        prefix = text.strip().upper().replace("♯", "#")
        candidates = [pitch_name(p).upper().replace("♯", "#") for p in range(self.minimum(), self.maximum() + 1)]
        candidates.extend(str(p) for p in range(self.minimum(), self.maximum() + 1))
        state = QValidator.State.Intermediate if any(value.startswith(prefix) for value in candidates) else QValidator.State.Invalid
        return state, text, position


class PianoRoll(QWidget):
    changed = Signal(object)
    selected = Signal()
    rejected = Signal()
    editing_started = Signal()
    preview_changed = Signal(object)
    view_changed=Signal(int)
    LEFT, TOP, BOTTOM = 45, 24, 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pattern, self.selection = MelodyPattern(), -1
        self.pitch_locked = True
        self.hint_notes, self.rhythm_hints = (), ()
        self._drag = None
        self.view_start=0
        self._drag_view_start=0;self._edge_direction=0
        self._pan_timer=QTimer(self);self._pan_timer.setInterval(240);self._pan_timer.timeout.connect(self._edge_pan)
        self.setMinimumSize(560, 292)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Piano roll / 鋼琴卷簾")

    @property
    def cell_width(self):
        return (self.width() - self.LEFT - 8) / self.display_steps

    @property
    def free(self):return isinstance(self.pattern,CompositionPattern)
    @property
    def steps(self):return self.pattern.steps if self.free else STEPS
    @property
    def display_steps(self):return min(self.steps-self.view_start,self.pattern.steps_per_bar*2) if self.free else STEPS
    @property
    def low_pitch(self):return LOW if self.free else LOW_PITCH
    @property
    def high_pitch(self):return HIGH if self.free else HIGH_PITCH
    @property
    def rows(self):return self.high_pitch-self.low_pitch+1
    def new_note(self,start,length,pitch):return (CompositionNote if self.free else GridNote)(start,length,pitch)
    def _make_pattern(self,notes):return self.pattern.with_notes(notes) if self.free else MelodyPattern(tuple(notes))

    @property
    def ROW(self):
        # The scene proxy has a fixed desktop viewport. Draw within the actual
        # allocated height, including when a longer translated clue wraps.
        return 22 if self.free else (self.height() - self.TOP - self.BOTTOM) / 13

    def sizeHint(self):
        return QSize(700, 292)

    def note_rect(self, note):
        return QRectF(self.LEFT + (note.start-self.view_start) * self.cell_width + 1,
                      self.TOP + (self.high_pitch - note.pitch) * self.ROW + 2,
                      note.length * self.cell_width - 2, self.ROW - 4)

    def point_for(self, start, pitch):
        return QPointF(self.LEFT + (start-self.view_start + .4) * self.cell_width,
                       self.TOP + (self.high_pitch - pitch + .5) * self.ROW)

    def set_pattern(self, pattern):
        self.cancel_drag()
        self.pattern = pattern
        self.view_start=min(self.view_start,max(0,self.steps-1)) if self.free else 0
        if self.free:self.view_start=self.view_start//self.pattern.steps_per_bar*self.pattern.steps_per_bar
        self.setMinimumHeight(self.rows*22+self.TOP+self.BOTTOM if self.free else 292)
        self.selection = min(self.selection, len(pattern.notes) - 1)
        self._drag = None
        self.update()
        self.selected.emit()

    def cancel_drag(self):
        self._pan_timer.stop()
        if self._drag is not None:
            self._drag = None
            self._drag_position = None
            self.unsetCursor()
            self.preview_changed.emit(None)
            self.update()

    def _hit(self, position):
        if position.x()<self.LEFT:return -1
        return next((i for i, note in enumerate(self.pattern.notes)
                     if self.note_rect(note).adjusted(-1, -2, 1, 2).contains(position)), -1)

    def _handle(self, note, position):
        rect = self.note_rect(note)
        width = min(9, rect.width()/3)
        if position.x() <= rect.left()+width:
            return 'left'
        if position.x() >= rect.right()-width:
            return 'right'
        return 'move'

    def _valid_candidate(self, note):
        notes = list(self.pattern.notes)
        notes[self.selection] = note
        try:
            self._make_pattern(notes)
            return True
        except ValueError:
            return False

    def replace_selected(self, note):
        notes = list(self.pattern.notes)
        if self.selection < 0:
            return False
        notes[self.selection] = note
        return self.commit(notes, note)

    def commit(self, notes, selected=None):
        try:
            pattern = self._make_pattern(notes)
        except ValueError:
            self.rejected.emit()
            return False
        self.pattern = pattern
        self.selection = pattern.notes.index(selected) if selected in pattern.notes else -1
        self.changed.emit(pattern)
        self.selected.emit()
        self.update()
        return True

    def add(self, start, pitch, length=1):
        if self.pitch_locked:
            pitch = LOW_PITCH
        note = self.new_note(start, min(length, self.steps - start), pitch)
        return self.commit((*self.pattern.notes, note), note)

    def delete(self):
        if self.selection >= 0:
            self.commit(tuple(n for i, n in enumerate(self.pattern.notes) if i != self.selection))

    def paintEvent(self, event):
        painter = QPainter(self)
        font = painter.font()
        font.setPixelSize(max(9, min(12, int(self.ROW) - 1)))
        painter.setFont(font)
        painter.fillRect(self.rect(), QColor("#14231f"))
        for pitch in range(self.low_pitch, self.high_pitch + 1):
            y = self.TOP + (self.high_pitch - pitch) * self.ROW
            black = pitch % 12 in (1, 3, 6, 8, 10)
            painter.fillRect(QRectF(0, y, self.width(), self.ROW), QColor("#1c2927" if black else "#29352e"))
            painter.setPen(QColor("#bec3ac"))
            painter.drawText(QRectF(1, y, 40, self.ROW), Qt.AlignmentFlag.AlignCenter, pitch_name(pitch))
        beat_cells=16//self.pattern.denominator if self.free else 4
        for step in range(self.display_steps + 1):
            x = self.LEFT + step * self.cell_width
            painter.setPen(QPen(QColor("#9b875b" if step % beat_cells == 0 else "#3c4a3d"), 1))
            painter.drawLine(QPointF(x, self.TOP), QPointF(x, self.TOP + self.ROW * self.rows))
            if step < self.display_steps:
                painter.setPen(QColor("#d8cfac"))
                painter.drawText(QRectF(x, 0, self.cell_width, self.TOP), Qt.AlignmentFlag.AlignCenter,
                                 str(step // beat_cells + 1) if step % beat_cells == 0 else "·")
        painter.setPen(QPen(QColor("#ddb86d"), 2, Qt.PenStyle.DashLine))
        painter.setClipRect(self.LEFT,self.TOP,self.width()-self.LEFT,self.height()-self.TOP)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for start, length in self.rhythm_hints:
            painter.drawRect(QRectF(self.LEFT + start * self.cell_width + 2, self.TOP + self.ROW * 13 - 5,
                                   length * self.cell_width - 4, 4))
        for note in self.hint_notes:
            painter.drawRoundedRect(self.note_rect(note), 2, 2)
        candidate = self._drag_note(self._drag_position) if self._drag is not None else None
        for index, original in enumerate(self.pattern.notes):
            note = candidate if candidate is not None and index == self.selection else original
            rect = self.note_rect(note)
            invalid = candidate is not None and index == self.selection and not self._valid_candidate(candidate)
            painter.setPen(QPen(QColor("#fff0b5" if index == self.selection else "#ad9159"), 2 if index == self.selection else 1))
            painter.setBrush(QColor('#a25042' if invalid else "#9c7e42" if index == self.selection else "#4f7865"))
            painter.drawRoundedRect(rect, 2, 2)
            handle = min(8, rect.width()/3)
            painter.fillRect(QRectF(rect.left()+1, rect.top()+1, handle, rect.height()-2), QColor(240, 211, 152, 70))
            painter.fillRect(QRectF(rect.right()-handle-1, rect.top()+1, handle, rect.height()-2), QColor(240, 211, 152, 70))
            painter.setPen(QColor("#f7f0d7"))
            painter.drawText(rect.adjusted(handle, 0, -handle, 0), Qt.AlignmentFlag.AlignCenter, pitch_name(note.pitch))
            for x in (rect.left()+handle/2+1, rect.right()-handle/2-1):
                painter.drawLine(QPointF(x, rect.top()+3), QPointF(x, rect.bottom()-3))

    def mousePressEvent(self, event):
        self.cancel_drag()
        self.setFocus()
        hit = self._hit(event.position())
        self.selection = hit
        self.selected.emit()
        self.update()
        if event.button() == Qt.MouseButton.RightButton:
            self.delete()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if hit >= 0:
            note = self.pattern.notes[hit]
            handle = self._handle(note, event.position())
            self._drag = (event.position(), note, handle)
            self._drag_view_start=self.view_start
            self._drag_position = event.position()
            self.setCursor(Qt.CursorShape.SizeHorCursor if handle != 'move' else Qt.CursorShape.ClosedHandCursor)
            self.editing_started.emit()
            self.preview_changed.emit(note)
        elif self.LEFT <= event.position().x() < self.width() - 8 and self.TOP <= event.position().y() < self.TOP + self.ROW * self.rows:
            start = min(self.steps - 1, self.view_start+int((event.position().x() - self.LEFT) / self.cell_width))
            pitch = self.high_pitch - int((event.position().y() - self.TOP) / self.ROW)
            self.add(start, pitch)
        event.accept()

    def _drag_note(self, position):
        origin, note, handle = self._drag
        dx = round((position.x() - origin.x()) / self.cell_width)+(self.view_start-self._drag_view_start if self.free else 0)
        dy = round((position.y() - origin.y()) / self.ROW)
        others = [n for i, n in enumerate(self.pattern.notes) if i != self.selection and (not self.free or n.pitch==note.pitch)]
        if handle == 'right':
            stop = min((n.start for n in others if n.start >= note.start+note.length), default=self.steps)
            return self.new_note(note.start, max(1, min(stop - note.start, note.length + dx)), note.pitch)
        if handle == 'left':
            first = max((n.start+n.length for n in others if n.start+n.length <= note.start), default=0)
            start = max(first, min(note.start+note.length-1, note.start+dx))
            return self.new_note(start, note.start+note.length-start, note.pitch)
        pitch = note.pitch if self.pitch_locked else max(self.low_pitch, min(self.high_pitch, note.pitch - dy))
        return self.new_note(max(0, min(self.steps - note.length, note.start + dx)), note.length, pitch)

    def mouseMoveEvent(self, event):
        if self._drag is not None:
            self._drag_position = event.position()
            self._edge_direction=(1 if event.position().x()>self.width()-16 else -1 if event.position().x()<self.LEFT+16 else 0) if self.free else 0
            if self._edge_direction:self._pan_timer.start()
            else:self._pan_timer.stop()
            self.preview_changed.emit(self._drag_note(event.position()))
            self.update()
        else:
            hit = self._hit(event.position())
            handle = self._handle(self.pattern.notes[hit], event.position()) if hit >= 0 else None
            if handle:
                self.setCursor(Qt.CursorShape.OpenHandCursor if handle == 'move' else Qt.CursorShape.SizeHorCursor)
            else:
                self.unsetCursor()

    def mouseReleaseEvent(self, event):
        if self._drag is None or event.button() != Qt.MouseButton.LeftButton:
            return
        note = self._drag[1]
        actual = self._drag_note(event.position())
        self.cancel_drag()
        if actual != note:
            self.replace_selected(actual)
        self.selected.emit()
        self.update()
        event.accept()

    def _edge_pan(self):
        if not self.free or self._drag is None:self._pan_timer.stop();return
        width=self.pattern.steps_per_bar
        new=max(0,min((self.pattern.bars-1)*width,self.view_start+self._edge_direction*width))
        if new==self.view_start:self._pan_timer.stop();return
        self.view_start=new;self.view_changed.emit(new//width+1)
        self.preview_changed.emit(self._drag_note(self._drag_position));self.update()

    def focusOutEvent(self, event):
        self.cancel_drag()
        super().focusOutEvent(event)

    def hideEvent(self, event):
        self.cancel_drag()
        super().hideEvent(event)

    def leaveEvent(self, event):
        if self._drag is None:
            self.unsetCursor()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.cancel_drag()
            event.accept()
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.cancel_drag()
            self.delete()
        elif self.selection >= 0 and key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.cancel_drag()
            note = self.pattern.notes[self.selection]
            start = max(0, min(self.steps - note.length, note.start + (key == Qt.Key.Key_Right) - (key == Qt.Key.Key_Left)))
            pitch = note.pitch if self.pitch_locked else max(self.low_pitch, min(self.high_pitch,
                note.pitch + (key == Qt.Key.Key_Up) - (key == Qt.Key.Key_Down)))
            self.replace_selected(self.new_note(start, note.length, pitch))
        else:
            super().keyPressEvent(event)


class PianoRollRuler(QWidget):
    """Keep beat positions visible while the pitch rows scroll vertically."""

    def __init__(self, roll, scroll):
        super().__init__()
        self.roll, self.scroll, self.language = roll, scroll, 'en'
        self.setFixedHeight(24)
        self.scroll.horizontalScrollBar().valueChanged.connect(self.update)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor('#14231f'))
        p.setPen(QColor('#d8cfac'))
        font = p.font()
        font.setPixelSize(11)
        p.setFont(font)
        p.drawText(QRectF(0, 0, self.roll.LEFT, 24), Qt.AlignmentFlag.AlignCenter,
                   '音高' if self.language == 'zh-Hant' else 'Pitch')
        p.setClipRect(self.roll.LEFT, 0, self.scroll.viewport().width()-self.roll.LEFT, 24)
        beat=16//self.roll.pattern.denominator if self.roll.free else 4
        for step in range(self.roll.display_steps):
            x = self.roll.LEFT + step*self.roll.cell_width - self.scroll.horizontalScrollBar().value()
            absolute=self.roll.view_start+step
            text=(f'{absolute//self.roll.pattern.steps_per_bar+1}.{absolute%self.roll.pattern.steps_per_bar//beat+1}' if self.roll.free else str(step//4+1)) if step%beat==0 else '·'
            p.drawText(QRectF(x, 0, self.roll.cell_width, 24), Qt.AlignmentFlag.AlignCenter,
                       text)


class PianoRollEditor(QWidget):
    changed = Signal(object)
    editing_started = Signal()

    def __init__(self):
        super().__init__()
        self.language = "en"
        layout = QVBoxLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.instructions = QLabel()
        # Wrapping gives the outer scroll area's layout a height-for-width
        # minimum based on the full canvas, hiding low notes and the inspector.
        self.instructions.setWordWrap(False)
        self.instructions.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.instructions.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.instructions)
        self.readout = QLabel()
        self.readout.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.readout.setStyleSheet('font-size: 13px; color: #ead29a;')
        layout.addWidget(self.readout)
        self.roll = PianoRoll()
        self.pages=QWidget();page_row=QHBoxLayout(self.pages);page_row.setContentsMargins(0,0,0,0)
        self.page_label=QLabel();self.previous_page=QPushButton('‹');self.next_page=QPushButton('›');self.page=QSpinBox();self.page.setRange(1,1);self.page.setFixedWidth(75)
        page_row.addWidget(self.page_label);page_row.addWidget(self.previous_page);page_row.addWidget(self.page);page_row.addWidget(self.next_page);page_row.addStretch()
        self.previous_page.clicked.connect(lambda:self.page.setValue(self.page.value()-1))
        self.next_page.clicked.connect(lambda:self.page.setValue(self.page.value()+1))
        self.page.valueChanged.connect(self._page_changed);layout.addWidget(self.pages);self.pages.hide()
        self.roll.TOP = 0
        self.viewport = QScrollArea()
        self.viewport.setWidgetResizable(True)
        self.viewport.setFrameShape(QScrollArea.Shape.NoFrame)
        self.viewport.setMinimumHeight(155)
        self.viewport.setWidget(self.roll)
        self.ruler = PianoRollRuler(self.roll, self.viewport)
        layout.addWidget(self.ruler)
        layout.addWidget(self.viewport, 1)
        self.roll.preview_changed.connect(self._preview)
        self.roll.view_changed.connect(self._sync_page)
        self.roll.editing_started.connect(self.editing_started.emit)
        row = QHBoxLayout()
        self.pitch = PitchBox()
        self.start, self.length = QSpinBox(), QSpinBox()
        self.start.setKeyboardTracking(False);self.length.setKeyboardTracking(False)
        self.start.setRange(0, 15)
        self.length.setRange(1, 16)
        self.start.setFixedWidth(65)
        self.length.setFixedWidth(65)
        self.pitch.setFixedWidth(85)
        self.labels = [QLabel() for _ in range(3)]
        for label, control in zip(self.labels, (self.pitch, self.start, self.length)):
            row.addWidget(label)
            row.addWidget(control)
        self.add_button, self.delete_button = QPushButton(), QPushButton()
        self.add_button.clicked.connect(self._add)
        self.delete_button.clicked.connect(self.roll.delete)
        row.addStretch()
        row.addWidget(self.add_button)
        row.addWidget(self.delete_button)
        layout.addLayout(row)
        self.message = QLabel()
        self.message.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.message.setStyleSheet("font-size: 12px; color: #deb46d;")
        layout.addWidget(self.message)
        layout.addStretch()
        self.roll.selected.connect(self._selected)
        self.roll.changed.connect(self._changed)
        self.roll.rejected.connect(self._rejected)
        self.pitch.valueChanged.connect(self._numeric)
        self.start.valueChanged.connect(self._numeric)
        self.length.valueChanged.connect(self._numeric)
        self.translate("en")
        self._selected()

    def set_pattern(self, pattern, *, pitch_locked=False, rhythm_hints=(), hint_notes=()):
        self.roll.pitch_locked = pitch_locked
        self.roll.rhythm_hints, self.roll.hint_notes = rhythm_hints, hint_notes
        self.roll.set_pattern(pattern)
        free=self.roll.free
        self.pages.setVisible(free)
        self.page.blockSignals(True);self.page.setMaximum(pattern.bars if free else 1)
        self.page.setValue(self.roll.view_start//pattern.steps_per_bar+1 if free else 1);self.page.blockSignals(False)
        for control in (self.pitch,self.start,self.length):control.blockSignals(True)
        self.pitch.setRange(self.roll.low_pitch,self.roll.high_pitch)
        self.start.setMaximum(self.roll.steps-1);self.length.setMaximum(self.roll.steps)
        for control in (self.pitch,self.start,self.length):control.blockSignals(False)
        self.ruler.update();self._selected()
        self._instructions()
        QTimer.singleShot(0, self._reveal_selection)

    def _reveal_selection(self):
        from shiboken6 import isValid
        if not isValid(self.roll) or not self.isVisible():
            return
        note = self.roll.pattern.notes[self.roll.selection] if self.roll.selection >= 0 else self.roll.new_note(self.roll.view_start,1,60)
        self._reveal_note(note)

    def _page_changed(self,value):
        if not self.roll.free:return
        self.roll.cancel_drag();self.roll.view_start=(value-1)*self.roll.pattern.steps_per_bar
        self.roll.update();self.ruler.update()

    def _sync_page(self,value):
        self.page.blockSignals(True);self.page.setValue(value);self.page.blockSignals(False);self.ruler.update()

    def _reveal_note(self, note):
        if self.roll.free and (note.start+note.length<=self.roll.view_start or note.start>=self.roll.view_start+self.roll.display_steps):
            self.page.setValue(note.start//self.roll.pattern.steps_per_bar+1)
        rect = self.roll.note_rect(note)
        bounds=rect
        for other in self.roll.pattern.notes:bounds=bounds.united(self.roll.note_rect(other))
        viewport=self.viewport.viewport()
        if bounds.height()+16<=viewport.height() and bounds.width()+16<=viewport.width():
            self.viewport.ensureVisible(round(bounds.center().x()),round(bounds.center().y()),round(bounds.width()/2+8),round(bounds.height()/2+8))
            return
        self.viewport.ensureVisible(round(rect.center().x()), round(rect.center().y()), 25, 30)

    def _preview(self, note):
        self.message.clear()
        if note is None:
            self._selected()
            return
        self._readout(note)
        if self.roll._drag is not None and note != self.roll._drag[1]:
            self._reveal_note(note)
        if not self.roll._valid_candidate(note):
            self._rejected()

    def _readout(self, note):
        beat_cells=16//self.roll.pattern.denominator if self.roll.free else 4
        self.readout.setText((f'{pitch_name(note.pitch)} · 長度 {note.length/beat_cells:g} 拍' if self.language == 'zh-Hant' else
                              f'{pitch_name(note.pitch)} · Length {note.length/beat_cells:g} beats') if note else
                            ('點擊空格加入音符，再直接拖曳調整。' if self.language == 'zh-Hant' else
                             'Click an empty cell to add a note, then drag it to edit.'))

    def _selected(self):
        note = self.roll.pattern.notes[self.roll.selection] if self.roll.selection >= 0 else None
        self._readout(note)
        for control in (self.pitch, self.start, self.length):
            control.setEnabled(note is not None)
            control.blockSignals(True)
        if note:
            self.pitch.setValue(note.pitch)
            self.start.setValue(note.start)
            self.length.setValue(note.length)
        self.pitch.setEnabled(note is not None and not self.roll.pitch_locked)
        for control in (self.pitch, self.start, self.length):
            control.blockSignals(False)
        self.delete_button.setEnabled(note is not None)

    def _numeric(self, *_):
        if self.roll.selection < 0:
            return
        try:
            note = self.roll.new_note(self.start.value(), self.length.value(), self.pitch.value())
        except ValueError:
            self._rejected()
            self._selected()
            return
        if not self.roll.replace_selected(note):
            self._selected()

    def _add(self):
        pitch=self.pitch.value()
        start = next((s for s in range(self.roll.view_start,self.roll.view_start+self.roll.display_steps)
            if not any(n.start<=s<n.start+n.length and (not self.roll.free or n.pitch==pitch) for n in self.roll.pattern.notes)),None)
        if start is not None:
            self.roll.add(start, self.pitch.value())
        else:
            self._rejected()

    def _changed(self, pattern):
        self.message.clear()
        self.changed.emit(pattern)

    def _rejected(self):
        self.message.setText(('同音高不能重疊；請先增加小節再延長。' if self.roll.free else '音符不能重疊或超出小節。') if self.language=='zh-Hant' else
            ('Same-pitch notes cannot overlap. Add bars before extending the timeline.' if self.roll.free else 'Notes cannot overlap or extend beyond this bar.'))

    def translate(self, language):
        from .hover_help import set_help
        self.language = language
        self.ruler.language = language
        self.ruler.update()
        zh = language == "zh-Hant"
        self.page_label.setText('起始小節' if zh else 'View from bar')
        for control in (self.page,self.previous_page,self.next_page):control.setToolTip('選擇要編輯的小節；只改視角，不移動音符。' if zh else 'Choose the bars to edit. This changes the view without moving notes.')
        self._instructions()
        for label, text in zip(self.labels, ("音高", "起格", "格數") if zh else ("Pitch", "Start", "Length")):
            label.setText(text)
        self.add_button.setText("加音" if zh else "Add")
        self.delete_button.setText("刪除" if zh else "Delete")
        for widget, key in ((self.add_button, "note_add"), (self.delete_button, "note_delete"),
                            (self.pitch, "note_pitch"), (self.start, "note_start"),
                            (self.length, "note_length"), (self.roll, "piano_roll")):
            set_help(widget, key, language)
        set_help(self.viewport.verticalScrollBar(), 'piano_pitch_scroll', language)
        set_help(self.viewport.horizontalScrollBar(), 'piano_time_scroll', language)
        self._selected()
        self._instructions()

    def _instructions(self):
        zh = self.language == 'zh-Hant'
        if self.roll.pitch_locked:
            text = ('拖曳音塊移動位置；拉左右邊緣改長短。節奏通關後開放上下調音高。' if zh else
                    'Drag notes to move them; pull either edge to resize. Pitch unlocks after rhythm.')
        else:
            text = ('C2–C6；捲動選音高，切換小節；拖音塊、拉邊緣改長短，一格為十六分音符。' if zh else
                    'C2–C6 · scroll for pitch, choose a bar; drag notes and resize their edges. One cell = 1/16 note.') if self.roll.free else ('上下拖音塊調音高；左右拖動移位置；拉左右邊緣改長短。每拍 4 格。' if zh else
                    'Drag up/down for pitch, left/right for time; pull either edge for length. 4 cells per beat.')
        self.instructions.setText(text)
        self.instructions.setToolTip(text)
        if self.roll.free:
            self.roll.setToolTip(text)
            self.pitch.setToolTip('輸入 C2–C6 或 MIDI 36–84，也可上下拖音塊。' if zh else 'Type C2–C6 or MIDI 36–84, or drag a note up/down.')
            self.start.setToolTip('音符在整段作品中的起格，以十六分音符為單位。' if zh else 'Note start in sixteenth-note cells across the whole piece.')
            self.length.setToolTip('音符長度，以十六分音符為單位；可以跨小節。' if zh else 'Note length in sixteenth-note cells; notes can cross bar lines.')
