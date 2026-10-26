"""A local collection of validated synthetic first-clear sounds, without files."""
import json
from pathlib import Path
from .debrief import Debrief
from .source_learning import DIFFICULTIES
from .storage import SessionStore,atomic_json_write


class EvidenceStore:
    def __init__(self,path):
        self.path=Path(path);self.entries={};self.warning='';self.blocked=False
        if self.path.exists():
            try:
                if self.path.stat().st_size>8_000_000:raise ValueError('Collection too large')
                data=json.loads(self.path.read_text('utf-8'))
                if set(data)!={'schema_version','entries'} or data['schema_version']!=1 or not isinstance(data['entries'],dict) or len(data['entries'])>40:raise ValueError('Invalid collection')
                for key,value in data['entries'].items():
                    if set(value)!={'variant','review'}:raise ValueError('Invalid collected sound')
                    record=Debrief.from_dict(value['review']);variant=value['variant']
                    self._validate(record,variant)
                    if key!=record.case_id+':'+variant:raise ValueError('Wrong collected sound identifier')
                    self.entries[key]=(variant,record)
            except (OSError,ValueError,TypeError,KeyError):
                self.entries={}
                try:SessionStore(self.path).preserve_invalid();self.warning='backup'
                except OSError:self.blocked=True;self.warning='blocked'

    @staticmethod
    def _validate(record,variant):
        if record.kind=='music' or record.clips['final'] is None:raise ValueError('Only completed synthetic sounds can be collected')
        if variant not in DIFFICULTIES or record.kind!='source' and variant!='advanced':raise ValueError('Invalid evidence difficulty')

    def remember(self,record,variant='advanced'):
        self._validate(record,variant)
        key=record.case_id+':'+variant
        if key in self.entries:return True
        if self.blocked:return False
        next_entries={**self.entries,key:(variant,record)}
        try:
            atomic_json_write(self.path,{'schema_version':1,'entries':{k:{'variant':v,'review':r.to_dict()} for k,(v,r) in next_entries.items()}})
        except (OSError,ValueError):self.warning='blocked';return False
        self.entries=next_entries;return True
