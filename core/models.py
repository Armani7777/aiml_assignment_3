"""Типизированные сообщения между агентами и общее состояние задачи (pydantic)."""
from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class MsgType(str, Enum):
    """Типы сообщений, которыми обмениваются агенты через оркестратор."""

    TASK = "task"
    RESULT = "result"
    REVISE = "revise"
    ERROR = "error"
    DONE = "done"


class AgentMessage(BaseModel):
    """Сообщение `AgentMessage {sender, receiver, type, payload}`."""

    sender: str
    receiver: str
    type: MsgType
    payload: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    ts: float = Field(default_factory=time.time)


class RunRequest(BaseModel):
    """Параметры запуска (то, что задаёт пользователь)."""

    file_path: str | None = None
    topic_text: str | None = None
    query: str = ""
    n_papers: int = 6
    year_from: int | None = None
    year_to: int | None = None
    categories: list[str] = Field(default_factory=list)
    focus: str = ""
    model: str = "qwen2.5:7b"
    llm_mode: str = "auto"  # auto | ollama | offline
    ollama_url: str | None = None
    max_revisions: int = 1
    max_steps: int = 150
    max_seconds: float = 1200.0


class ResearchTask(BaseModel):
    """Результат аналитика документа."""

    problem: str = ""
    keywords: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    domain: str = ""
    is_scientific: bool = True
    n_chunks: int = 0
    n_chars: int = 0


class Paper(BaseModel):
    """Статья корпуса с оценками и решением отборщика."""

    id: str
    title: str
    abstract: str = ""
    authors: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    primary_category: str = ""
    year: int | None = None
    bm25: float = 0.0
    dense: float = 0.0
    score: float = 0.0
    same_task: bool | None = None
    reason: str = ""
    flags: list[str] = Field(default_factory=list)
    selected: bool = False
    ref: int | None = None

    @property
    def url(self) -> str:
        return f"https://arxiv.org/abs/{self.id}"


class Theme(BaseModel):
    name: str
    description: str = ""
    paper_ids: list[str] = Field(default_factory=list)


class Review(BaseModel):
    """Отчёт проверяющего по одной версии черновика."""

    version: int
    rule_violations: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    comments: list[str] = Field(default_factory=list)
    passed: bool = False


class TaskState(BaseModel):
    """Единое общее состояние задачи; сохраняется в JSON."""

    run_id: str
    request: RunRequest
    status: str = "created"  # created | running | done | failed | limit
    plan: list[str] = Field(default_factory=list)
    active_agent: str = ""
    task: ResearchTask | None = None
    candidates: list[Paper] = Field(default_factory=list)
    themes: list[Theme] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    drafts: list[str] = Field(default_factory=list)
    reviews: list[Review] = Field(default_factory=list)
    revisions: int = 0
    messages: list[AgentMessage] = Field(default_factory=list)
    errors: list[dict[str, str]] = Field(default_factory=list)
    steps: int = 0
    llm_calls: int = 0
    llm_mode_used: str = ""
    started_at: float = Field(default_factory=time.time)
    elapsed: float = 0.0

    @property
    def selected(self) -> list[Paper]:
        return sorted([p for p in self.candidates if p.selected], key=lambda p: p.ref or 0)

    @property
    def draft(self) -> str:
        return self.drafts[-1] if self.drafts else ""

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "TaskState":
        return cls.model_validate(json.loads(path.read_text(encoding="utf-8")))
