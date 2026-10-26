"""Bounded edit history. Progress, submissions and hints are never snapshots."""

from copy import deepcopy
from dataclasses import asdict, is_dataclass
import time


def _changes(before, after, path=()):
    if is_dataclass(before):
        before, after = asdict(before), asdict(after)
    if isinstance(before, dict) and isinstance(after, dict) and before.keys() == after.keys():
        return tuple(p for key in before for p in _changes(before[key], after[key], path + (key,)))
    if isinstance(before, (tuple, list)) and isinstance(after, (tuple, list)) and len(before) == len(after):
        return tuple(p for i, (a, b) in enumerate(zip(before, after)) for p in _changes(a, b, path + (i,)))
    return () if before == after else (path,)


class EditHistory:
    def __init__(self, initial, *, limit=100, clock=time.monotonic):
        self.limit, self.clock = limit, clock
        self.reset(initial)

    def reset(self, initial):
        self.states, self.index = [deepcopy(initial)], 0
        self.break_merge()

    def break_merge(self):
        self._key, self._time = None, float('-inf')
        self.gesture = False

    @property
    def current(self):
        return deepcopy(self.states[self.index])

    @property
    def can_undo(self):
        return self.index > 0

    @property
    def can_redo(self):
        return self.index + 1 < len(self.states)

    def record(self, state, *, merge=True):
        if state == self.states[self.index]:
            return False
        key, now = _changes(self.states[self.index], state), self.clock()
        coalesce = (merge and self.index > 0 and not self.can_redo and key == self._key
                    and (self.gesture or now - self._time < .65))
        del self.states[self.index + 1:]
        if coalesce:
            self.states[self.index] = deepcopy(state)
        else:
            self.states.append(deepcopy(state))
            self.index += 1
        if len(self.states) > self.limit + 1:
            self.states.pop(0)
            self.index -= 1
        self._key, self._time = key, now
        return True

    def undo(self):
        if self.can_undo:
            self.index -= 1
        self.break_merge()
        return self.current

    def redo(self):
        if self.can_redo:
            self.index += 1
        self.break_merge()
        return self.current
