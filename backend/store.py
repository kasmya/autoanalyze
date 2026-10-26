"""In-memory dataset store for the prototype.

No database is needed for a single-user prototype: uploaded dataframes are
kept in memory, keyed by an upload id, and expire after a period of
inactivity. This is explicitly not meant to scale past a demo/single user.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

import pandas as pd

EXPIRY_SECONDS = 60 * 60  # 1 hour


@dataclass
class _Entry:
    df: pd.DataFrame
    filename: str
    created_at: float = field(default_factory=time.time)


class DatasetStore:
    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._entries.items() if now - v.created_at > EXPIRY_SECONDS]
        for k in expired:
            del self._entries[k]

    def put(self, df: pd.DataFrame, filename: str) -> str:
        self._evict_expired()
        upload_id = uuid.uuid4().hex
        self._entries[upload_id] = _Entry(df=df, filename=filename)
        return upload_id

    def get(self, upload_id: str) -> pd.DataFrame:
        self._evict_expired()
        entry = self._entries.get(upload_id)
        if entry is None:
            raise KeyError(upload_id)
        return entry.df

    def get_filename(self, upload_id: str) -> str:
        entry = self._entries.get(upload_id)
        if entry is None:
            raise KeyError(upload_id)
        return entry.filename


store = DatasetStore()
