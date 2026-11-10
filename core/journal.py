"""Журнал (аудиторский след): каждый вызов LLM и инструмента — строка JSONL."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class Journal:
    """Пишет события в `runs/<run_id>/journal.jsonl`."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")

    def log(self, agent: str, kind: str, name: str, duration: float = 0.0,
            tokens: int = 0, status: str = "ok", **detail: Any) -> dict[str, Any]:
        """Добавляет запись: время, агент, тип (llm/tool/message), длительность, токены, статус."""
        rec = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "agent": agent,
            "kind": kind,
            "name": name,
            "duration_s": round(duration, 3),
            "tokens": tokens,
            "status": status,
            **detail,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        return rec


def read_journal(path: Path) -> list[dict[str, Any]]:
    """Читает журнал прогона."""
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
