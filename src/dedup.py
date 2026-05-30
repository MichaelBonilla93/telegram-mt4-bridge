from __future__ import annotations

import json
from pathlib import Path


class SeenStore:
    """Persiste los IDs de mensajes ya procesados para evitar duplicados."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ids: set[int] = set()
        if self._path.exists():
            self._ids = set(json.loads(self._path.read_text(encoding="utf-8")))

    def seen(self, message_id: int) -> bool:
        return message_id in self._ids

    def mark(self, message_id: int) -> None:
        self._ids.add(message_id)
        self._path.write_text(json.dumps(sorted(self._ids)), encoding="utf-8")
