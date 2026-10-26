"""A diagnostic window that stays responsive while dependencies are checked."""

from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout
from ..diagnostics import collect_diagnostics, format_report, save_report
from .hover_help import set_help


class DiagnosticsDialog(QDialog):
    completed = Signal(object)

    def __init__(self, parent=None, *, language='en', report=None):
        super().__init__(parent)
        self.language, self.report, self._closed = language, report, False
        zh = language == 'zh-Hant'
        self.setWindowTitle('啟動診斷' if zh else 'Startup diagnostics')
        self.resize(760, 560)
        layout = QVBoxLayout(self)
        self.status = QLabel('正在檢查…' if zh else 'Checking…')
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.status)
        layout.addWidget(self.output, 1)
        row = QHBoxLayout()
        self.export_button = QPushButton('匯出報告' if zh else 'Export report')
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export)
        close = QPushButton('關閉' if zh else 'Close')
        close.clicked.connect(self.accept)
        set_help(self.export_button, 'diagnostic_export', language)
        set_help(close, 'diagnostic_close', language)
        row.addWidget(self.export_button)
        row.addStretch()
        row.addWidget(close)
        layout.addLayout(row)
        self.completed.connect(self._show_report)
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='diagnostics')
        if report is not None:
            self._show_report(report)
        else:
            future = self._executor.submit(collect_diagnostics)
            def done(task):
                try:
                    result = task.result()
                except Exception as error:
                    result = {'diagnostic_error': str(error)}
                if not self._closed:
                    self.completed.emit(result)
            future.add_done_callback(done)

    def _show_report(self, report):
        if self._closed:
            return
        self.report = report
        if 'diagnostic_error' in report:
            self.status.setText(report['diagnostic_error'])
            return
        zh = self.language == 'zh-Hant'
        warning = any(c['status'] == 'warning' for c in report['checks'])
        self.status.setText(('檢查通過' if zh else 'Checks passed') if report['ok'] and not warning else
                            ('請檢查下列項目' if zh else 'Review the items below'))
        self.output.setPlainText(format_report(report, self.language))
        self.export_button.setEnabled(True)

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, self.windowTitle(), 'SoundDetective-diagnostics.json', 'JSON (*.json)')
        if path:
            try:
                save_report(self.report, path)
            except OSError as error:
                self.status.setText(str(error))

    def done(self, result):
        self._closed = True
        self._executor.shutdown(wait=False, cancel_futures=True)
        super().done(result)
