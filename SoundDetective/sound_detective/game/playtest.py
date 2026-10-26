"""Opt-in, local anonymous observation logs; no participant results are invented."""
import csv
import json
from pathlib import Path
import time
import uuid


class PlaytestLog:
    FIELDS=('participant','elapsed_seconds','case','difficulty','event','attempts','score','control')
    def __init__(self,directory,*,clock=time.monotonic):
        self.directory=Path(directory);self.clock=clock;self.started=None
        self.participant=uuid.uuid4().hex[:12];self.records=[]
        self.path=self.directory/f'playtest-{self.participant}.jsonl'

    def record(self,case,event,*,attempts=0,score=None,control=''):
        if event not in ('start','edit','hint','example','submit','loop','difficulty','stop','end'):raise ValueError('Unknown playtest event')
        now=self.clock()
        if self.started is None:self.started=now
        row=dict(zip(self.FIELDS,(self.participant,round(max(0,now-self.started),3),case.id,case.difficulty,event,attempts,score,control)))
        # Serialize before appending, so invalid floating-point values cannot
        # produce a partial event. Only controlled fields are recorded.
        payload=json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n'
        self.directory.mkdir(parents=True,exist_ok=True)
        with self.path.open('a',encoding='utf-8') as file:file.write(payload)
        self.records.append(row)

    def export_csv(self):
        if not self.records:raise ValueError('Start a playtest and record an event first')
        output=self.directory/f'playtest-{self.participant}.csv'
        with output.open('w',encoding='utf-8-sig',newline='') as file:
            writer=csv.DictWriter(file,fieldnames=self.FIELDS);writer.writeheader();writer.writerows(self.records)
        return output
