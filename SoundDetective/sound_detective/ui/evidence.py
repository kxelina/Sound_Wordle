"""Read-only collection reusing the verified debrief audio pipeline."""
from pathlib import Path
import shutil
import uuid
from PySide6.QtWidgets import QComboBox,QPushButton
from .debrief import DebriefPanel
from .hover_help import set_help


class EvidencePanel(DebriefPanel):
    def __init__(self,store,cases,**options):
        self.store,self.cases=store,{c.id:c for c in cases}
        self._export=False
        super().__init__(**options)
        self.selector=QComboBox();self.selector.setMinimumHeight(34)
        self.layout().insertWidget(1,self.selector)
        self.selector.currentIndexChanged.connect(self._select)
        self.export_button=QPushButton()
        self.export_button.clicked.connect(self.export_final)
        self.layout().insertWidget(self.layout().count()-2,self.export_button)
        self.cases_button.hide()
        self.refresh()

    def refresh(self):
        previous=self.selector.currentData()
        self.selector.blockSignals(True);self.selector.clear()
        for key,(variant,record) in self.store.entries.items():
            if record.case_id in self.cases:self.selector.addItem(record.case_id+' · '+record.title[self.language],key)
        index=self.selector.findData(previous)
        self.selector.setCurrentIndex(max(0,index));self.selector.blockSignals(False)
        self._select();self.translate(self.language)

    def _select(self,*unused):
        key=self.selector.currentData()
        if key in self.store.entries:
            record=self.store.entries[key][1]
            self.load(record,self.cases[record.case_id])
        else:
            self.stop();self.record=None
            self.statistics.setText(self.text('Clear a synthetic sound case to collect its first saved answer.','完成合成聲音案件後，首次通關作品會收入收藏。'))
            self.changes.clear();self.note.clear();self.parameters.setRowCount(0);self.components.setRowCount(0)
            self.trace.points=();self.trace.update()
            for button in self.audio_buttons.values():button.setEnabled(False)
            self.compare_button.setEnabled(False)
        self.export_button.setEnabled(self.record is not None)

    def translate(self,language):
        super().translate(language)
        self.heading.setText(self.text('EVIDENCE CABINET','聲音證物收藏櫃'))
        self.back_button.setText(self.text('Back to workspace','返回工作區'))
        if hasattr(self,'export_button'):
            self.export_button.setText(self.text('Export collected answer · WAV','匯出收藏作品 · WAV'))
            set_help(self.export_button,'evidence_export',language);set_help(self.selector,'evidence_select',language)
            self.selector.blockSignals(True)
            for i in range(self.selector.count()):
                record=self.store.entries[self.selector.itemData(i)][1]
                self.selector.setItemText(i,record.case_id+' · '+record.title[language])
            self.selector.blockSignals(False)
            if self.store.warning:self.status.setText(self.text('Collection read/save warning; case progress is stored separately.','收藏讀取／儲存發生問題，正式案件進度另行保存。'))

    def export_final(self):
        if not self.record:return
        self.play(('final',));self._export=bool(self._armed)

    def _ready(self,backend,revision,data):
        if not self._export:return super()._ready(backend,revision,data)
        if self._closed or backend is not self._backend or revision!=self._revision or not self._armed:return
        self._export=False;self._armed=();self.busy.hide()
        temporary=None
        try:
            directory=self.store.path.parent/'evidence-exports';directory.mkdir(parents=True,exist_ok=True)
            output=directory/f'{self.record.case_id}-{uuid.uuid4().hex[:12]}.wav'
            temporary=output.with_suffix('.tmp')
            shutil.copyfile(data['final'].listening_path,temporary);temporary.replace(output)
            self.status.setText(self.text('Exported: ','已匯出：')+str(output))
        except (OSError,KeyError) as error:
            if temporary is not None:temporary.unlink(missing_ok=True)
            self.status.setText(str(error))

    def stop(self):
        self._export=False
        super().stop()
