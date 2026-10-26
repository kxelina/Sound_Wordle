"""Recorded-music piano roll: fixed timing, draggable pitch, fractional cents."""

import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from ..audio.models import bounded
from .piano_roll import pitch_name


def displayed_note(pitch):
    nearest = round(pitch)
    cents = round((pitch-nearest)*100)
    return pitch_name(nearest) + (f" {cents:+d} ct" if cents else "")


class RecordedPitchRoll(QWidget):
    changed = Signal(object)
    selection_changed = Signal(int)
    editing_started = Signal()
    audition_requested = Signal()
    LEFT, TOP, RIGHT, BOTTOM = 54, 25, 10, 8

    def __init__(self, mapping, initial_cents, parent=None):
        super().__init__(parent)
        self.mapping, self.initial_cents = mapping, tuple(initial_cents)
        if len(self.initial_cents) != len(mapping.editable_notes):
            raise ValueError("Pitch map does not match the repair controls")
        self.corrections = (0,)*len(self.initial_cents)
        self.selection, self.editable, self.language = 0, True, "en"
        self._drag = None
        self._set_pitch_bounds()
        self.setMinimumSize(560, 160)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def _set_pitch_bounds(self):
        pitches = [self.pitch_for_note(n) for n in self.mapping.notes]
        self.low = max(0, math.floor(min(pitches))-2)
        self.high = min(127, math.ceil(max(pitches))+2)

    @property
    def row_height(self):
        return (self.height()-self.TOP-self.BOTTOM)/(self.high-self.low+1)

    def sizeHint(self):
        return QSize(760, 225)

    def pitch_for_note(self, note):
        if note.region_index is None:
            return float(note.midi)
        index = note.region_index
        correction = self._drag["value"] if self._drag and self._drag["index"] == index else self.corrections[index]
        return note.midi + (self.initial_cents[index]+correction)/100

    def note_rect(self, note):
        width = self.width()-self.LEFT-self.RIGHT
        x = self.LEFT + note.start_seconds/self.mapping.seconds*width
        end = self.LEFT + note.end_seconds/self.mapping.seconds*width
        center = self.TOP + (self.high-self.pitch_for_note(note)+.5)*self.row_height
        height = max(10., min(19., self.row_height-2))
        return QRectF(x+1, center-height/2, max(3., end-x-2), height)

    def rect_for_region(self, index):
        return self.note_rect(self.mapping.editable_notes[index])

    def set_corrections(self, corrections):
        corrections = tuple(corrections)
        if len(corrections) != len(self.initial_cents):
            raise ValueError("Wrong pitch-control count")
        for value in corrections:
            bounded("pitch correction", value, -600, 600)
            if value != round(value):
                raise ValueError("Pitch corrections use integer cents")
        self.cancel_drag()
        self.corrections = corrections
        self._set_pitch_bounds()
        self.update()

    def select_region(self, index):
        if type(index) is not int or not 0 <= index < len(self.corrections):
            raise ValueError("Invalid selected pitch region")
        if self.selection != index:
            self.cancel_drag()
            self.selection = index
            self.selection_changed.emit(index)
        self.update()

    def set_correction(self, index, cents):
        if not self.editable:
            return
        bounded("pitch correction", cents, -600, 600)
        cents = round(cents)
        if cents != self.corrections[index]:
            values = list(self.corrections)
            values[index] = cents
            self.corrections = tuple(values)
            self._set_pitch_bounds()
            self.changed.emit(self.corrections)
            self.update()

    def set_editable(self, editable):
        self.editable = bool(editable)
        if not self.editable:
            self.cancel_drag()
        self.setCursor(Qt.CursorShape.OpenHandCursor if editable else Qt.CursorShape.ArrowCursor)
        self.update()

    def cancel_drag(self):
        if self._drag is not None:
            self._drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor if self.editable else Qt.CursorShape.ArrowCursor)
            self.update()

    def _hit(self, position):
        # Editable note blocks take priority over their read-only context.
        return next((n.region_index for n in self.mapping.editable_notes
                     if self.note_rect(n).adjusted(0, -2, 0, 2).contains(position)), None)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#14231f"))
        font = p.font()
        font.setPixelSize(10)
        p.setFont(font)
        for pitch in range(self.low, self.high+1):
            y = self.TOP+(self.high-pitch)*self.row_height
            black = pitch % 12 in (1, 3, 6, 8, 10)
            p.fillRect(QRectF(0, y, self.width(), self.row_height), QColor("#1b2926" if black else "#29372f"))
            p.setPen(QColor("#c1c5af"))
            if self.row_height >= 10 or pitch % 3 == 0:
                p.drawText(QRectF(1, y-2, self.LEFT-4, max(12, self.row_height)), Qt.AlignmentFlag.AlignCenter, pitch_name(pitch))
            if pitch % 12 == 0:
                p.setPen(QPen(QColor("#596d56"), 1))
                p.drawLine(QPointF(self.LEFT, y), QPointF(self.width()-self.RIGHT, y))
        for second in range(math.ceil(self.mapping.seconds)+1):
            x = self.LEFT+second/self.mapping.seconds*(self.width()-self.LEFT-self.RIGHT)
            p.setPen(QPen(QColor("#776d4d" if second % 2 == 0 else "#3e4c40"), 1))
            p.drawLine(QPointF(x, self.TOP), QPointF(x, self.height()-self.BOTTOM))
            p.setPen(QColor("#d9cfad"))
            p.drawText(QRectF(x-15, 0, 30, self.TOP), Qt.AlignmentFlag.AlignCenter, f"{second}s")
        for note in self.mapping.notes:
            index = note.region_index
            rect = self.note_rect(note)
            selected = index is not None and index == self.selection
            p.setPen(QPen(QColor("#ffe2a3" if selected else "#a78b58" if index is not None else "#53635b"), 2 if selected else 1))
            p.setBrush(QColor("#a38848" if selected else "#4d7c67" if index is not None else "#344c41"))
            p.drawRoundedRect(rect, 2, 2)
            if index is not None and rect.height() >= 7:
                p.setPen(QColor("#fff1d0"))
                note_font = p.font()
                note_font.setPixelSize(10 if rect.height() >= 12 else 9)
                p.setFont(note_font)
                label = pitch_name(round(self.pitch_for_note(note)))
                if p.fontMetrics().horizontalAdvance(label) > rect.width()-2:
                    note_font.setPixelSize(8)
                    p.setFont(note_font)
                if p.fontMetrics().horizontalAdvance(label) > rect.width()-2:
                    label = label[:-1]  # The pitch axis retains octave context.
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        p.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.editable:
            return
        index = self._hit(event.position())
        if index is None:
            return
        self.setFocus()
        self.select_region(index)
        self._drag = {"index": index, "origin": event.position(), "row_height": self.row_height, "pitch": self.pitch_for_note(self.mapping.editable_notes[index]),
                      "value": self.corrections[index], "fine": bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)}
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.editing_started.emit()
        event.accept()

    def _drag_value(self, position):
        drag = self._drag
        if abs(position.y()-drag["origin"].y()) < 3:
            return self.corrections[drag["index"]]
        scale = .2 if drag["fine"] else 1.
        pitch = drag["pitch"] - (position.y()-drag["origin"].y())/drag["row_height"]*scale
        pitch = round(pitch*10)/10 if drag["fine"] else round(pitch)
        return self.mapping.correction_for_pitch(drag["index"], max(0, min(127, pitch)), self.initial_cents)

    def mouseMoveEvent(self, event):
        if self._drag is not None:
            self._drag["value"] = self._drag_value(event.position())
            self.update()
            event.accept()

    def mouseReleaseEvent(self, event):
        if self._drag is None or event.button() != Qt.MouseButton.LeftButton:
            return
        index, value = self._drag["index"], self._drag_value(event.position())
        self._drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.set_correction(index, value)
        self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        index = self._hit(event.position())
        if self.editable and event.button() == Qt.MouseButton.LeftButton and index is not None:
            self.cancel_drag()
            self.select_region(index)
            self.audition_requested.emit()
            event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.cancel_drag()
        elif self.editable and key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 100
            self.set_correction(self.selection, max(-600, min(600, self.corrections[self.selection] + (step if key == Qt.Key.Key_Up else -step))))
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            self.select_region(max(0, min(len(self.corrections)-1, self.selection + (1 if key == Qt.Key.Key_Right else -1))))
        elif self.editable and key in (Qt.Key.Key_Space, Qt.Key.Key_Return):
            self.audition_requested.emit()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        self.cancel_drag()
        super().focusOutEvent(event)

    def hideEvent(self, event):
        self.cancel_drag()
        super().hideEvent(event)


class RecordedPitchEditor(QWidget):
    changed = Signal(object)
    selection_changed = Signal(int)
    editing_started = Signal()
    audition_requested = Signal()

    def __init__(self, mapping, initial_cents, corrections):
        super().__init__()
        self.language, self.zoom = "en", 1.
        self.roll = RecordedPitchRoll(mapping, initial_cents)
        self.roll.set_corrections(corrections)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setMinimumHeight(160)
        self.scroll.setWidget(self.roll)
        layout.addWidget(self.scroll, 1)
        row = QHBoxLayout()
        row.setSpacing(4)
        self.selected_label = QLabel()
        self.selected_label.setMinimumWidth(60)
        self.selected_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        row.addWidget(self.selected_label, 1)
        self.fine = QDoubleSpinBox()
        self.fine.setRange(-6, 6)
        self.fine.setDecimals(2)
        self.fine.setSingleStep(.1)
        self.fine.setSuffix(" st")
        self.fine.setFixedWidth(86)
        self.fine.setKeyboardTracking(False)
        self.fine.valueChanged.connect(lambda value: self.roll.set_correction(self.roll.selection, round(value*100)))
        row.addWidget(self.fine)
        self.reset_button, self.fit_button = QPushButton(), QPushButton()
        self.zoom_out, self.zoom_in = QPushButton("−"), QPushButton("+")
        self.audition_button = QPushButton()
        self.reset_button.clicked.connect(lambda: self.roll.set_correction(self.roll.selection, 0))
        self.zoom_in.clicked.connect(lambda: self._zoom(min(4., self.zoom*1.5)))
        self.zoom_out.clicked.connect(lambda: self._zoom(max(1., self.zoom/1.5)))
        self.fit_button.clicked.connect(lambda: self._zoom(1.))
        self.audition_button.clicked.connect(self.audition_requested)
        for button in (self.reset_button, self.zoom_out, self.zoom_in, self.fit_button, self.audition_button):
            button.setStyleSheet("padding: 4px 7px; min-width: 18px;")
            row.addWidget(button)
        layout.addLayout(row)
        self.roll.changed.connect(self._changed)
        self.roll.selection_changed.connect(self._selected)
        self.roll.editing_started.connect(self.editing_started)
        self.roll.audition_requested.connect(self.audition_button.click)
        self.translate("en")
        self._selected(0)

    @property
    def corrections(self):
        return self.roll.corrections

    def set_corrections(self, corrections):
        self.roll.set_corrections(corrections)
        self._selected(self.roll.selection, reveal=False)

    def select_region(self, index):
        self.roll.select_region(index)
        self._selected(index)

    def set_editable(self, editable):
        self.roll.set_editable(editable)
        for widget in (self.fine, self.reset_button, self.audition_button):
            widget.setEnabled(editable)

    def _selected(self, index, reveal=True):
        self.fine.blockSignals(True)
        self.fine.setValue(self.corrections[index]/100)
        self.fine.blockSignals(False)
        note = self.roll.mapping.editable_notes[index]
        pitch = self.roll.pitch_for_note(note)
        hz = 440 * 2**((pitch-69)/12)
        self.selected_label.setText(f"{index+1} · ≈{displayed_note(pitch)} · {hz:.0f} Hz")
        self.selected_label.setAccessibleName(f"{index+1}: {displayed_note(pitch)}, {hz:.1f} Hz, {note.start_seconds:.2f}–{note.end_seconds:.2f} s")
        if reveal:
            rect = self.roll.rect_for_region(index)
            self.scroll.ensureVisible(round(rect.center().x()), round(rect.center().y()), 35, 25)
        self.selection_changed.emit(index)

    def _changed(self, corrections):
        self._selected(self.roll.selection, reveal=False)
        self.changed.emit(corrections)

    def _zoom(self, value):
        self.zoom = value
        self.roll.setMinimumSize(max(560, round(self.scroll.viewport().width()*value)), max(155, round(self.scroll.viewport().height()*value)))
        self._selected(self.roll.selection)

    def translate(self, language):
        from .hover_help import set_help
        self.language = self.roll.language = language
        zh = language == "zh-Hant"
        self.reset_button.setText("重設此音" if zh else "Reset note")
        self.fit_button.setText("全覽" if zh else "Fit")
        self.audition_button.setText("試聽選音" if zh else "Hear note")
        for widget, key in ((self.roll, "music_pitch_roll"), (self.fine, "music_pitch_fine"),
                            (self.selected_label, "music_pitch_estimate"), (self.reset_button, "music_pitch_reset"),
                            (self.zoom_in, "music_pitch_zoom_in"), (self.zoom_out, "music_pitch_zoom_out"),
                            (self.fit_button, "music_pitch_fit"), (self.audition_button, "music_monitor")):
            set_help(widget, key, language)
        self._selected(self.roll.selection, reveal=False)
