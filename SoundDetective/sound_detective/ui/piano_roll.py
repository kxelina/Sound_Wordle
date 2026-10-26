"""Small one-bar piano roll: add, move, resize, delete, and exact-value editing."""

from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QSize, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QValidator
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QLayout, QScrollArea)

from ..game.melody import GridNote, MelodyPattern, STEPS, LOW_PITCH, HIGH_PITCH


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
        for pitch in range(LOW_PITCH, HIGH_PITCH + 1):
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
        candidates = [pitch_name(p).upper().replace("♯", "#") for p in range(LOW_PITCH, HIGH_PITCH + 1)]
        candidates.extend(str(p) for p in range(LOW_PITCH, HIGH_PITCH + 1))
        state = QValidator.State.Intermediate if any(value.startswith(prefix) for value in candidates) else QValidator.State.Invalid
        return state, text, position


class PianoRoll(QWidget):
    changed = Signal(object)
    selected = Signal()
    rejected = Signal()
    editing_started = Signal()
    preview_changed = Signal(object)
    LEFT, TOP, BOTTOM = 45, 24, 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pattern, self.selection = MelodyPattern(), -1
        self.pitch_locked = True
        self.hint_notes, self.rhythm_hints = (), ()
        self._drag = None
        self.setMinimumSize(560, 292)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Piano roll / 鋼琴卷簾")

    @property
    def cell_width(self):
        return (self.width() - self.LEFT - 8) / STEPS

    @property
    def ROW(self):
        # The scene proxy has a fixed desktop viewport. Draw within the actual
        # allocated height, including when a longer translated clue wraps.
        return (self.height() - self.TOP - self.BOTTOM) / 13

    def sizeHint(self):
        return QSize(700, 292)

    def note_rect(self, note):
        return QRectF(self.LEFT + note.start * self.cell_width + 1,
                      self.TOP + (HIGH_PITCH - note.pitch) * self.ROW + 2,
                      note.length * self.cell_width - 2, self.ROW - 4)

    def point_for(self, start, pitch):
        return QPointF(self.LEFT + (start + .4) * self.cell_width,
                       self.TOP + (HIGH_PITCH - pitch + .5) * self.ROW)

    def set_pattern(self, pattern):
        self.cancel_drag()
        self.pattern = pattern
        self.selection = min(self.selection, len(pattern.notes) - 1)
        self._drag = None
        self.update()
        self.selected.emit()

    def cancel_drag(self):
        if self._drag is not None:
            self._drag = None
            self._drag_position = None
            self.unsetCursor()
            self.preview_changed.emit(None)
            self.update()

    def _hit(self, position):
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
            MelodyPattern(tuple(notes))
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
            pattern = MelodyPattern(tuple(notes))
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
        note = GridNote(start, min(length, STEPS - start), pitch)
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
        for pitch in range(LOW_PITCH, HIGH_PITCH + 1):
            y = self.TOP + (HIGH_PITCH - pitch) * self.ROW
            black = pitch % 12 in (1, 3, 6, 8, 10)
            painter.fillRect(QRectF(0, y, self.width(), self.ROW), QColor("#1c2927" if black else "#29352e"))
            painter.setPen(QColor("#bec3ac"))
            painter.drawText(QRectF(1, y, 40, self.ROW), Qt.AlignmentFlag.AlignCenter, pitch_name(pitch))
        for step in range(STEPS + 1):
            x = self.LEFT + step * self.cell_width
            painter.setPen(QPen(QColor("#9b875b" if step % 4 == 0 else "#3c4a3d"), 1))
            painter.drawLine(QPointF(x, self.TOP), QPointF(x, self.TOP + self.ROW * 13))
            if step < STEPS:
                painter.setPen(QColor("#d8cfac"))
                painter.drawText(QRectF(x, 0, self.cell_width, self.TOP), Qt.AlignmentFlag.AlignCenter,
                                 str(step // 4 + 1) if step % 4 == 0 else "·")
        painter.setPen(QPen(QColor("#ddb86d"), 2, Qt.PenStyle.DashLine))
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
            self._drag_position = event.position()
            self.setCursor(Qt.CursorShape.SizeHorCursor if handle != 'move' else Qt.CursorShape.ClosedHandCursor)
            self.editing_started.emit()
            self.preview_changed.emit(note)
        elif self.LEFT <= event.position().x() < self.width() - 8 and self.TOP <= event.position().y() < self.TOP + self.ROW * 13:
            start = min(STEPS - 1, int((event.position().x() - self.LEFT) / self.cell_width))
            pitch = HIGH_PITCH - int((event.position().y() - self.TOP) / self.ROW)
            self.add(start, pitch)
        event.accept()

    def _drag_note(self, position):
        origin, note, handle = self._drag
        dx = round((position.x() - origin.x()) / self.cell_width)
        dy = round((position.y() - origin.y()) / self.ROW)
        others = [n for i, n in enumerate(self.pattern.notes) if i != self.selection]
        if handle == 'right':
            stop = min((n.start for n in others if n.start >= note.start+note.length), default=STEPS)
            return GridNote(note.start, max(1, min(stop - note.start, note.length + dx)), note.pitch)
        if handle == 'left':
            first = max((n.start+n.length for n in others if n.start+n.length <= note.start), default=0)
            start = max(first, min(note.start+note.length-1, note.start+dx))
            return GridNote(start, note.start+note.length-start, note.pitch)
        pitch = note.pitch if self.pitch_locked else max(LOW_PITCH, min(HIGH_PITCH, note.pitch - dy))
        return GridNote(max(0, min(STEPS - note.length, note.start + dx)), note.length, pitch)

    def mouseMoveEvent(self, event):
        if self._drag is not None:
            self._drag_position = event.position()
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
            start = max(0, min(STEPS - note.length, note.start + (key == Qt.Key.Key_Right) - (key == Qt.Key.Key_Left)))
            pitch = note.pitch if self.pitch_locked else max(LOW_PITCH, min(HIGH_PITCH,
                note.pitch + (key == Qt.Key.Key_Up) - (key == Qt.Key.Key_Down)))
            self.replace_selected(GridNote(start, note.length, pitch))
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
        for step in range(STEPS):
            x = self.roll.LEFT + step*self.roll.cell_width - self.scroll.horizontalScrollBar().value()
            p.drawText(QRectF(x, 0, self.roll.cell_width, 24), Qt.AlignmentFlag.AlignCenter,
                       str(step//4+1) if step % 4 == 0 else '·')


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
        self.instructions.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.instructions)
        self.readout = QLabel()
        self.readout.setStyleSheet('font-size: 13px; color: #ead29a;')
        layout.addWidget(self.readout)
        self.roll = PianoRoll()
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
        self.roll.editing_started.connect(self.editing_started.emit)
        row = QHBoxLayout()
        self.pitch = PitchBox()
        self.start, self.length = QSpinBox(), QSpinBox()
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
        self._instructions()
        QTimer.singleShot(0, self._reveal_selection)

    def _reveal_selection(self):
        from shiboken6 import isValid
        if not isValid(self.roll) or not self.isVisible():
            return
        note = self.roll.pattern.notes[self.roll.selection] if self.roll.selection >= 0 else GridNote(0, 1, LOW_PITCH)
        self._reveal_note(note)

    def _reveal_note(self, note):
        rect = self.roll.note_rect(note)
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
        self.readout.setText((f'{pitch_name(note.pitch)} · 長度 {note.length/4:g} 拍' if self.language == 'zh-Hant' else
                              f'{pitch_name(note.pitch)} · Length {note.length/4:g} beats') if note else
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
            note = GridNote(self.start.value(), self.length.value(), self.pitch.value())
        except ValueError:
            self._rejected()
            self._selected()
            return
        if not self.roll.replace_selected(note):
            self._selected()

    def _add(self):
        occupied = {s for n in self.roll.pattern.notes for s in range(n.start, n.start + n.length)}
        start = next((s for s in range(STEPS) if s not in occupied), None)
        if start is not None:
            self.roll.add(start, self.pitch.value())
        else:
            self._rejected()

    def _changed(self, pattern):
        self.message.clear()
        self.changed.emit(pattern)

    def _rejected(self):
        self.message.setText("音符不能重疊或超出小節。" if self.language == "zh-Hant" else "Notes cannot overlap or extend beyond this bar.")

    def translate(self, language):
        from .hover_help import set_help
        self.language = language
        self.ruler.language = language
        self.ruler.update()
        zh = language == "zh-Hant"
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

    def _instructions(self):
        zh = self.language == 'zh-Hant'
        if self.roll.pitch_locked:
            text = ('拖曳音塊移動位置；拉左右邊緣改長短。節奏通關後開放上下調音高。' if zh else
                    'Drag notes to move them; pull either edge to resize. Pitch unlocks after rhythm.')
        else:
            text = ('上下拖音塊調音高；左右拖動移位置；拉左右邊緣改長短。每拍 4 格。' if zh else
                    'Drag up/down for pitch, left/right for time; pull either edge for length. 4 cells per beat.')
        self.instructions.setText(text)
