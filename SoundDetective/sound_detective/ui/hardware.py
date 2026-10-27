"""Painted studio controls; the values still belong to the existing case editor."""

import math

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QAbstractButton, QButtonGroup, QCheckBox, QDial, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QVBoxLayout, QWidget,
)
from .hover_help import set_help


class InlineChoices(QWidget):
    """Exclusive choices kept inside the scene, without a native popup window."""

    currentIndexChanged = Signal(int)
    activated = Signal(int)

    def __init__(self, parent=None, *, columns=2):
        super().__init__(parent)
        self.columns = columns
        self.buttons, self._data = [], []
        self._index = -1
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self.setStyleSheet("""
            QPushButton:checked { background: #6b5837; color: #fff0c4; border: 2px solid #dabe83; }
            QPushButton:disabled { color: #908b7b; border: 1px solid #605c4d; background: #403e32; }
        """)

    def addItem(self, text, data=None):
        self.insertItem(self.count(), text, data)

    def insertItem(self, index, text, data=None):
        button = QPushButton(text)
        button.setCheckable(True)
        button.setMinimumHeight(40)
        self._group.addButton(button)
        self.buttons.insert(index, button)
        self._data.insert(index, data)
        if self._index >= index:
            self._index += 1
        button.clicked.connect(lambda: self._activate(self.buttons.index(button)))
        for i, item in enumerate(self.buttons):
            self._layout.addWidget(item, i // self.columns, i % self.columns)

    def _activate(self, index):
        self.setCurrentIndex(index)
        self.activated.emit(index)

    def clear(self):
        for button in self.buttons:
            self._group.removeButton(button)
            self._layout.removeWidget(button)
            button.hide()
            button.deleteLater()
        self.buttons, self._data, self._index = [], [], -1

    def count(self):
        return len(self.buttons)

    def itemData(self, index):
        return self._data[index] if 0 <= index < self.count() else None

    def currentIndex(self):
        return self._index

    def currentData(self):
        return self.itemData(self._index)

    def findData(self, value):
        return next((index for index, data in enumerate(self._data) if data == value), -1)

    def setCurrentIndex(self, index):
        if not 0 <= index < self.count():
            return
        changed = self._index != index
        self._index = index
        self.buttons[index].setChecked(True)
        if changed:
            self.currentIndexChanged.emit(index)

    def setItemEnabled(self, index, enabled):
        self.buttons[index].setEnabled(enabled)


class RackFace(QWidget):
    """Subtle brushed metal faceplate, drawn at the actual widget resolution."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        gradient.setColorAt(0, QColor("#71614a"))
        gradient.setColorAt(.08, QColor("#504632"))
        gradient.setColorAt(.55, QColor("#3e392d"))
        gradient.setColorAt(1, QColor("#292b26"))
        painter.setPen(QPen(QColor("#ad9060"), 1))
        painter.setBrush(gradient)
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(QPen(QColor(231, 213, 168, 13), .6))
        for y in range(6, self.height() - 5, 4):
            painter.drawLine(8, y, self.width() - 8, y)
        for x in (10, self.width() - 10):
            for y in (10, self.height() - 10):
                painter.setBrush(QColor("#282922"))
                painter.setPen(QPen(QColor("#8e7957"), 1))
                painter.drawEllipse(QPointF(x, y), 3, 3)
                painter.drawLine(QPointF(x-1.5, y+1.5), QPointF(x+1.5, y-1.5))


class PowerToggle(QCheckBox):
    """Illuminated latching switch with a full-button mouse hit region."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(88, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.language = "en"

    def hitButton(self, point):
        return self.rect().contains(point)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(1 if self.isEnabled() else .35)
        p.setBrush(QColor("#242c23"))
        p.setPen(QPen(QColor("#d6b679" if self.hasFocus() else "#897957"), 1))
        p.drawRoundedRect(QRectF(1, 1, 86, 32), 4, 4)
        lamp = QRadialGradient(QPointF(19, 15), 13)
        lamp.setColorAt(0, QColor("#ffe6a2" if self.isChecked() else "#857349"))
        lamp.setColorAt(.6, QColor("#d59836" if self.isChecked() else "#4e4732"))
        lamp.setColorAt(1, QColor("#352f23"))
        p.setBrush(lamp)
        p.setPen(QPen(QColor("#b19b69"), 1))
        p.drawEllipse(QPointF(22, 17), 11, 11)
        p.setPen(QColor("#efdbad"))
        label = ("開" if self.isChecked() else "關") if self.language == "zh-Hant" else ("ON" if self.isChecked() else "OFF")
        p.drawText(QRectF(39, 0, 42, 34), Qt.AlignmentFlag.AlignCenter, label)


class HardwareFader(QSlider):
    """Vertical fader with direct track/handle dragging and inherited key input."""

    def _position(self):
        fraction = (self.value() - self.minimum()) / max(1, self.maximum() - self.minimum())
        return 16 + (1 - fraction) * max(1, self.height() - 32)

    def paintEvent(self, event):
        if self.orientation() != Qt.Orientation.Vertical:
            return super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(1 if self.isEnabled() else .35)
        x, y = self.width() / 2, self._position()
        for tick in range(11):
            ty = 16 + tick * (self.height() - 32) / 10
            p.setPen(QPen(QColor("#af9970"), 1))
            p.drawLine(QPointF(x-19, ty), QPointF(x-11, ty))
            p.drawLine(QPointF(x+11, ty), QPointF(x+19, ty))
        p.setPen(QPen(QColor("#151914"), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(x, 16), QPointF(x, self.height()-16))
        p.setPen(QPen(QColor("#8d7a53"), 1))
        p.drawLine(QPointF(x+3, 16), QPointF(x+3, self.height()-16))
        handle = QRectF(x-16, y-11, 32, 22)
        fill = QLinearGradient(handle.topLeft(), handle.bottomLeft())
        for at, color in ((0, "#a6a38d"), (.18, "#d4ccaf"), (.48, "#565b50"), (1, "#242c26")):
            fill.setColorAt(at, QColor(color))
        p.setPen(QPen(QColor("#111a14"), 1))
        p.setBrush(fill)
        p.drawRoundedRect(handle, 2, 2)
        p.setPen(QPen(QColor("#eed08a"), 2))
        p.drawLine(QPointF(x-11, y), QPointF(x+11, y))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#f0cf85"), 1, Qt.PenStyle.DotLine))
            p.drawRoundedRect(handle.adjusted(-3, -3, 3, 3), 3, 3)

    def _drag(self, y):
        fraction = 1 - (y - 16) / max(1, self.height() - 32)
        self.setValue(round(self.minimum() + max(0, min(1, fraction)) * (self.maximum()-self.minimum())))
        self.update()

    def mousePressEvent(self, event):
        if self.orientation() != Qt.Orientation.Vertical:
            return super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.setSliderDown(True)
            self._drag(event.position().y())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.orientation() == Qt.Orientation.Vertical and self.isSliderDown():
            self._drag(event.position().y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.orientation() == Qt.Orientation.Vertical:
            self.setSliderDown(False)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class RotaryKnob(QDial):
    """Bounded 270-degree knob. Relative drag avoids jumping when first grabbed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWrapping(False)
        self.setFixedSize(96, 96)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.SizeVerCursor)
        self._anchor = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(1 if self.isEnabled() else .32)
        p.scale(self.width()/96, self.height()/96)
        center = QPointF(48, 48)
        fraction = (self.value()-self.minimum()) / max(1, self.maximum()-self.minimum())
        for i in range(11):
            angle = math.radians(135 + i * 27)
            p.setPen(QPen(QColor("#b49a69"), 1.2))
            p.drawLine(center + QPointF(math.cos(angle)*39, math.sin(angle)*39),
                       center + QPointF(math.cos(angle)*43, math.sin(angle)*43))
        p.setPen(QPen(QColor("#dab66f"), 2))
        p.drawArc(QRectF(11, 11, 74, 74), 225*16, round(-270*16*fraction))
        p.setPen(QPen(QColor("#171c17"), 3))
        rim = QLinearGradient(20, 15, 75, 80)
        rim.setColorAt(0, QColor("#b3a786")); rim.setColorAt(.5, QColor("#4d4e40")); rim.setColorAt(1, QColor("#948264"))
        p.setBrush(rim)
        p.drawEllipse(center, 31, 31)
        surface = QRadialGradient(QPointF(38, 33), 53)
        surface.setColorAt(0, QColor("#555b50")); surface.setColorAt(.5, QColor("#252d26")); surface.setColorAt(1, QColor("#101711"))
        p.setBrush(surface)
        p.setPen(QPen(QColor("#171c17"), 1))
        p.drawEllipse(center, 27, 27)
        angle = math.radians(135 + fraction*270)
        p.setPen(QPen(QColor("#f2dca4"), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(center + QPointF(math.cos(angle)*16, math.sin(angle)*16),
                   center + QPointF(math.cos(angle)*25, math.sin(angle)*25))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor("#f0cf85"), 1, Qt.PenStyle.DotLine))
            p.drawEllipse(center, 46, 46)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self._anchor = event.position(), self.value()
            self.setSliderDown(True)
            event.accept()

    def mouseMoveEvent(self, event):
        if self._anchor is None:
            return
        position, value = self._anchor
        delta = event.position() - position
        fine = .1 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
        units = (self.maximum()-self.minimum()) / 180
        self.setValue(round(value + (delta.x() - delta.y()) * units * fine))
        event.accept()

    def mouseReleaseEvent(self, event):
        self._anchor = None
        self.setSliderDown(False)
        event.accept()

    def focusOutEvent(self, event):
        self._anchor = None
        self.setSliderDown(False)
        super().focusOutEvent(event)


class TapeDisplay(QAbstractButton):
    """Click the cassette window to audition the current reconstruction."""

    def __init__(self, *, compact=False):
        super().__init__()
        self.compact = compact
        self.setMinimumHeight(70 if compact else 96)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.playing = False
        self.caption = "PLAY RECONSTRUCTION"

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(1 if self.isEnabled() else .4)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(QPen(QColor("#d0b171" if self.hasFocus() or self.underMouse() else "#7c765b"), 1))
        p.setBrush(QColor("#141f19"))
        p.drawRoundedRect(r, 5, 5)
        radius=min(22,max(12,r.width()*.17))
        for x in (r.width()*.27, r.width()*.73):
            center = QPointF(x, 27 if self.compact else 38)
            p.setBrush(QColor("#757b62")); p.setPen(QPen(QColor("#b1ae85"), 1))
            p.drawEllipse(center, radius, radius)
            p.setBrush(QColor("#1b2820")); p.drawEllipse(center, radius*.36, radius*.36)
            for i in range(6):
                angle = math.radians(i*60)
                p.drawLine(center+QPointF(math.cos(angle)*radius*.45, math.sin(angle)*radius*.45),
                           center+QPointF(math.cos(angle)*radius*.78, math.sin(angle)*radius*.78))
        p.setPen(QPen(QColor("#9e9f7d"), 2))
        tape_y = 46 if self.compact else 60
        p.drawLine(QPointF(r.width()*.27, tape_y), QPointF(r.width()*.73, tape_y))
        p.setBrush(QColor("#e0ae51" if self.playing else "#51482b"))
        p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(r.width()-15, 14), 4, 4)
        p.setPen(QColor("#e5d3a1"))
        text_top = 49 if self.compact else 66
        if self.caption=='▶':
            center=QPointF(self.width()/2,text_top+(self.height()-text_top-4)/2)
            triangle=QPainterPath(center+QPointF(-4,-5))
            triangle.lineTo(center+QPointF(5,0));triangle.lineTo(center+QPointF(-4,5));triangle.closeSubpath()
            p.fillPath(triangle,QColor('#e5d3a1'))
        else:
            p.drawText(QRectF(8, text_top, self.width()-16, self.height()-text_top-4), Qt.AlignmentFlag.AlignCenter, self.caption)


class PlaybackDeck(RackFace):
    """Two physical tape players; hidden commands retain the shared transport."""
    def __init__(self, reference, current, stop, ab=None, *, compact=False,
                 reference_mode='always',reference_titles=('Reference','參照聲音'),
                 current_titles=('Your sound','你的聲音')):
        super().__init__()
        self.setObjectName('playback_deck')
        self._reference,self._current=reference,current
        self.reference_mode=reference_mode
        self.reference_titles,self.current_titles=reference_titles,current_titles
        self.language='en';self._state='stopped';self._label=''
        layout=QVBoxLayout(self);layout.setContentsMargins(6,6,6,6);layout.setSpacing(4)
        self.legend=QLabel();self.legend.hide()
        players=QHBoxLayout();players.setSpacing(6)
        self.reference_frame,self.reference_title,self.reference_display=self._tape(reference,'reference_tape')
        self.current_frame,self.current_title,self.display=self._tape(current,'audition_tape')
        players.addWidget(self.reference_frame,1);players.addWidget(self.current_frame,1)
        layout.addLayout(players)
        self.stop=stop;layout.addWidget(stop)
        for button in (reference,current,ab):
            if button is not None:
                button.setParent(self);button.hide()
        reference.installEventFilter(self);current.installEventFilter(self)
        self.setStyleSheet('QPushButton {font-size:12px;padding:3px 6px;min-height:16px;}')
        self.setMinimumHeight(144)
        self.translate('en');self._sync()

    def _tape(self,command,name):
        face=RackFace();row=QVBoxLayout(face);row.setContentsMargins(6,7,6,5);row.setSpacing(2)
        title=QLabel();title.setWordWrap(True);title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet('font-size:12px;color:#e5d3a1;')
        display=TapeDisplay(compact=True);display.setObjectName(name)
        display.setProperty('uiClickForwarded',True);display.clicked.connect(command.click)
        row.addWidget(title);row.addWidget(display,1)
        return face,title,display

    def set_reference_mode(self,mode):
        if mode not in ('always','unlocked','never'):raise ValueError('Unknown tape layout')
        self.reference_mode=mode;self._sync()

    def _sync(self):
        self.display.setEnabled(self._current.isEnabled())
        self.reference_display.setEnabled(self._reference.isEnabled())
        self.reference_frame.setVisible(self.reference_mode=='always' or
            self.reference_mode=='unlocked' and self._reference.isEnabled())
        self._current.hide();self._reference.hide()

    def translate(self,language):
        self.language=language;zh=language=='zh-Hant'
        self.legend.setText('聲音試聽機' if zh else 'Audition tapes')
        for title,display,names,kind in (
            (self.reference_title,self.reference_display,self.reference_titles,'reference'),
            (self.current_title,self.display,self.current_titles,'current')):
            title.setText(names[zh]);display.caption='▶'
            display.setAccessibleName(names[zh])
            display.setToolTip(('點擊錄音機播放'+names[zh]+'；使用下方停止鍵結束。') if zh else
                ('Click this tape to play '+names[zh].lower()+'. Use Stop below to end playback.'))
            display.update()
        self._sync()

    def set_state(self,state,label):
        self._state,self._label=state,label
        active=state in ('playing','loading')
        is_reference=any(word in label.lower() for word in ('target','reference','evidence','before','contrast','目標','參照','證物','修改前','對比'))
        self.reference_display.playing=active and is_reference
        self.display.playing=active and not is_reference
        self.reference_display.update();self.display.update()

    def eventFilter(self,watched,event):
        if watched in (self._reference,self._current) and event.type()==QEvent.Type.EnabledChange:
            self._sync()
        return super().eventFilter(watched,event)
