"""Shared edit toolbar and shortcuts, including embedded scene widgets."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QWidget
from shiboken6 import isValid

from ..game.edit_history import EditHistory
from .hover_help import set_help


class EditHistoryBar(QWidget):
    def __init__(self, owner, initial, apply, *, enabled=lambda: True, layout=None):
        super().__init__(owner.centralWidget())
        self.owner, self.apply, self.allowed = owner, apply, enabled
        self.stack = EditHistory(initial)
        self.restoring = False
        self.root = owner.centralWidget()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.undo_button, self.redo_button = QPushButton(), QPushButton()
        self.undo_button.setObjectName('undo_edit')
        self.redo_button.setObjectName('redo_edit')
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        row.addWidget(self.undo_button)
        row.addWidget(self.redo_button)
        row.addStretch()
        (layout if layout is not None else self.root.layout()).addWidget(self)
        QApplication.instance().installEventFilter(self)
        self.translate(owner._language)

    def translate(self, language):
        zh = language == 'zh-Hant'
        self.undo_button.setText('復原 · Ctrl+Z' if zh else 'Undo · Ctrl+Z')
        self.redo_button.setText('重做 · Ctrl+Y' if zh else 'Redo · Ctrl+Y')
        set_help(self.undo_button, 'undo_edit', language)
        set_help(self.redo_button, 'redo_edit', language)
        self.refresh()

    def refresh(self):
        self.undo_button.setEnabled(self.allowed() and self.stack.can_undo)
        self.redo_button.setEnabled(self.allowed() and self.stack.can_redo)

    def record(self, state, *, merge=True):
        if not self.restoring:
            self.stack.record(state, merge=merge)
        self.refresh()

    def reset(self, state):
        self.stack.reset(state)
        self.refresh()

    def _move(self, forward):
        if not self.allowed() or not (self.stack.can_redo if forward else self.stack.can_undo):
            return
        self.restoring = True
        try:
            self.apply(self.stack.redo() if forward else self.stack.undo())
        finally:
            self.restoring = False
            self.refresh()

    def undo(self):
        self._move(False)

    def redo(self):
        self._move(True)

    def eventFilter(self, watched, event):
        if (not isValid(self.root) or getattr(self.owner, '_closed', False) or not isinstance(watched, QWidget)
                or not isValid(watched) or not (watched == self.root or self.root.isAncestorOf(watched))):
            return False
        kind = event.type()
        if kind == QEvent.Type.MouseButtonPress:
            self.stack.break_merge()
            self.stack.gesture = True
        elif kind == QEvent.Type.MouseButtonRelease:
            self.stack.gesture = False
        elif kind in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            modifiers = event.modifiers()
            if modifiers & Qt.KeyboardModifier.ControlModifier and not modifiers & Qt.KeyboardModifier.AltModifier:
                if event.key() in (Qt.Key.Key_Z, Qt.Key.Key_Y):
                    event.accept()
                    if kind == QEvent.Type.KeyPress:
                        redo = event.key() == Qt.Key.Key_Y or bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
                        self.redo() if redo else self.undo()
                    return True
        return False
