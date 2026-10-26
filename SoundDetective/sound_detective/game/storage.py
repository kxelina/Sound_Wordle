"""Atomic versioned local saves; preserve unreadable files before a new run."""

import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

from .session import SessionState


class SessionStore:
    def __init__(self, path):
        self.path = Path(path)

    def load(self, case):
        if not self.path.exists():
            return SessionState(case)
        if self.path.stat().st_size > 2_000_000:
            raise ValueError("Save exceeds the 2 MB limit")
        return SessionState.from_dict(case, json.loads(self.path.read_text(encoding="utf-8")))

    def preserve_invalid(self):
        backup = self.path.with_name(f"{self.path.stem}.invalid-{uuid.uuid4().hex[:8]}.json")
        shutil.copy2(self.path, backup)
        return backup

    def save(self, session):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError):
                data = None  # Invalid-save preservation is handled by the caller.
            if isinstance(data, dict) and data.get("schema_version") in (1, 2):
                # Preserve the exact valid old file before the first schema-3
                # save. A failed backup must leave the old progress untouched.
                backup = self.path.with_name(f"{self.path.stem}.before-progress-v2-{uuid.uuid4().hex[:8]}.json")
                shutil.copy2(self.path, backup)
            elif isinstance(data,dict) and session.case.id=='T09' and data.get('schema_version')==3:
                backup=self.path.with_name(f'{self.path.stem}.before-rolling-v4-{uuid.uuid4().hex[:8]}.json')
                shutil.copy2(self.path,backup)
        atomic_json_write(self.path, session.to_dict())


def atomic_json_write(path, data):
    path = Path(path)
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".progress-", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write(payload + "\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
