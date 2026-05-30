from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class SeenStore:
    """Persiste los IDs de mensajes ya procesados para evitar duplicados."""

    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._ids: set[int] = set()
        if self._path.exists():
            try:
                self._ids = set(json.loads(self._path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                log.warning("seen.json ilegible; arrancando con set vacío")
                self._ids = set()

    def seen(self, message_id: int) -> bool:
        return message_id in self._ids

    def mark(self, message_id: int) -> None:
        self._ids.add(message_id)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(sorted(self._ids)), encoding="utf-8")
        tmp.replace(self._path)
