"""Tutorial preferences and first-clear reviews live apart from game saves."""

import json
from pathlib import Path

from ..audio.models import bounded
from .debrief import Debrief
from .storage import SessionStore,atomic_json_write


def fresh_tutorial():
    return {'step':0,'completed':False,'dismissed':False,'release':.85,'h2':0.,
            'bird_pitch':74.,'bird_sweep':4.,'bird_length':.4}


def validate_tutorial(data):
    if not isinstance(data,dict) or set(data)!=set(fresh_tutorial()):
        raise ValueError('Invalid tutorial progress')
    if type(data['step']) is not int or not 0<=data['step']<=4 or any(type(data[k]) is not bool for k in ('completed','dismissed')):
        raise ValueError('Invalid tutorial step')
    for key,low,high in (('release',.02,1.2),('h2',0,1),('bird_pitch',60,100),('bird_sweep',-12,12),('bird_length',.08,.5)):
        bounded(key,data[key],low,high)


class JourneyStore:
    def __init__(self,path):
        self.path=Path(path)
        self.tutorial=fresh_tutorial()
        self.reviews={}
        self.timings={}
        self.warning=''
        self.blocked=False
        if self.path.exists():
            try:
                if self.path.stat().st_size>2_000_000:
                    raise ValueError('Journey file is too large')
                data=json.loads(self.path.read_text('utf-8'))
                if not isinstance(data,dict) or set(data) not in ({'schema_version','tutorial','reviews'},{'schema_version','tutorial','reviews','timings'}) or type(data['schema_version']) is not int or data['schema_version']!=1:
                    raise ValueError('Unsupported player journey')
                validate_tutorial(data['tutorial'])
                if not isinstance(data['reviews'],dict) or len(data['reviews'])>15:
                    raise ValueError('Invalid review archive')
                records={k:Debrief.from_dict(v) for k,v in data['reviews'].items()}
                if any(k!=r.case_id for k,r in records.items()):
                    raise ValueError('Mismatched review archive')
                self.tutorial=data['tutorial']
                self.reviews=records
                timings=data.get('timings',{})
                if not isinstance(timings,dict) or len(timings)>15:raise ValueError('Invalid case timing')
                for key,value in timings.items():
                    if not isinstance(value,dict) or set(value)!={'seconds','complete'} or type(value['complete']) is not bool:
                        raise ValueError('Invalid case timing')
                    bounded('case time',value['seconds'],0,365*86400)
                self.timings=timings
            except (OSError,ValueError,TypeError,KeyError):
                try:
                    self.tutorial=fresh_tutorial();self.reviews={};self.timings={}
                    SessionStore(self.path).preserve_invalid()
                    self.warning='backup'
                except OSError:
                    self.warning='save_error';self.blocked=True

    def save(self):
        if self.blocked:
            return False
        try:
            validate_tutorial(self.tutorial)
            atomic_json_write(self.path,{'schema_version':1,'tutorial':self.tutorial,
                'reviews':{k:v.to_dict() for k,v in self.reviews.items()},'timings':self.timings})
            return True
        except (OSError,ValueError,TypeError):
            self.warning='save_error'
            return False

    def remember(self,record):
        if record.case_id not in self.reviews:
            self.reviews[record.case_id]=record
            self.save()
        return self.reviews[record.case_id]

    @property
    def should_offer_tutorial(self):
        return not (self.tutorial['completed'] or self.tutorial['dismissed'])
