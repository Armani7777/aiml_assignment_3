"""Оркестратор: только планирует (разбирает запрос) и маршрутизирует сообщения AgentMessage.

Схема «оркестратор + общее состояние»: агенты читают/пишут `TaskState`, а между собой
общаются только через типизированные сообщения, проходящие через оркестратор.
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Callable

from core import config
from core.errors import LimitExceeded, RAError, StepLimit, TimeLimit
from core.journal import Journal
from core.llm import LLMClient
from core.models import AgentMessage, MsgType, RunRequest, TaskState

PIPELINE = ["analyst", "retriever", "selector", "synthesizer", "writer", "critic"]


def parse_query(req: RunRequest) -> RunRequest:
    """Планирование: извлекает из свободного запроса число статей, годы и фокус."""
    q = req.query or ""
    if m := re.search(r"(\d+)\s*(?:стат|работ|papers?)", q, re.I):
        req.n_papers = max(1, min(15, int(m.group(1))))
    if m := re.search(r"(20\d\d)\s*[-–—]\s*(20\d\d)", q):
        req.year_from, req.year_to = int(m.group(1)), int(m.group(2))
    elif m := re.search(r"(?:с|после|since|from)\s*(20\d\d)", q, re.I):
        req.year_from = int(m.group(1))
    cats = re.findall(r"\b([a-z]{2,8}\.[A-Z]{2})\b", q)
    if cats:
        req.categories = sorted(set(req.categories) | set(cats))
    if m := re.search(r"(?:фокус|focus)\s*[:—-]?\s*(.+)$", q, re.I):
        req.focus = m.group(1).strip()
    return req


class Context:
    """Контекст выполнения: состояние, журнал, LLM и лимиты (шаги, время)."""

    def __init__(self, state: TaskState, journal: Journal, llm: LLMClient | None,
                 on_event: Callable[[TaskState, AgentMessage | None], None] | None = None) -> None:
        self.state, self.journal, self.llm, self.on_event = state, journal, llm, on_event

    def tick(self) -> None:
        """Шаг выполнения; проверка лимитов шагов и времени."""
        st = self.state
        st.steps += 1
        st.elapsed = time.time() - st.started_at
        if st.steps > st.request.max_steps:
            raise StepLimit(f"Превышен лимит шагов ({st.request.max_steps}).",
                            "Увеличьте лимит шагов или уменьшите число статей.")
        if st.elapsed > st.request.max_seconds:
            raise TimeLimit(f"Превышен лимит времени ({st.request.max_seconds:.0f} с).",
                            "Выберите модель qwen2.5:3b или уменьшите число статей.")

    def call_tool(self, agent: str, name: str, fn, *args, **kw):
        """Вызов инструмента с журналированием, одним повтором и проверкой лимитов."""
        self.tick()
        for attempt in range(2):
            t0 = time.time()
            try:
                res = fn(*args, **kw)
                self.journal.log(agent, "tool", name, time.time() - t0, 0, "ok", attempt=attempt)
                return res
            except RAError:
                self.journal.log(agent, "tool", name, time.time() - t0, 0, "error", attempt=attempt)
                raise
            except Exception as e:  # noqa: BLE001
                self.journal.log(agent, "tool", name, time.time() - t0, 0, "retry" if attempt == 0 else "error",
                                 attempt=attempt, error=str(e)[:300])
                if attempt == 1:
                    raise


class Orchestrator:
    """Планирует задачу и маршрутизирует сообщения между шестью агентами."""

    def __init__(self, on_event: Callable[[TaskState, AgentMessage | None], None] | None = None) -> None:
        from agents import AGENTS

        self.agents = AGENTS
        self.on_event = on_event

    def send(self, ctx: Context, msg: AgentMessage) -> None:
        ctx.tick()
        ctx.state.messages.append(msg)
        ctx.journal.log("orchestrator", "message", msg.type.value, 0, 0, "ok",
                        sender=msg.sender, receiver=msg.receiver, summary=msg.summary)
        if self.on_event:
            self.on_event(ctx.state, msg)

    def dispatch(self, ctx: Context, receiver: str, payload: dict | None = None,
                 mtype: MsgType = MsgType.TASK, summary: str = "") -> AgentMessage:
        """Отправляет задание агенту и пересылает его ответ оркестратору."""
        msg = AgentMessage(sender="orchestrator", receiver=receiver, type=mtype, payload=payload or {},
                           summary=summary or f"Задание для «{self.agents[receiver].title}»")
        ctx.state.active_agent = receiver
        self.send(ctx, msg)
        reply = self.agents[receiver].handle(msg, ctx)
        self.send(ctx, reply)
        return reply

    def run(self, req: RunRequest, run_id: str | None = None) -> TaskState:
        """Полный прогон. Всегда сохраняет (возможно, частичное) состояние и журнал."""
        run_id = run_id or time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        req = parse_query(req)
        state = TaskState(run_id=run_id, request=req, status="running")
        state.plan = [f"Найти {req.n_papers} статей", f"Годы: {req.year_from or '—'}…{req.year_to or '—'}",
                      f"Категории: {', '.join(req.categories) or 'все'}", f"Фокус: {req.focus or 'нет'}",
                      f"Доработок не больше {req.max_revisions}"]
        run_dir = config.RUNS_DIR / run_id
        journal = Journal(run_dir / "journal.jsonl")
        ctx = Context(state, journal, None, self.on_event)
        try:
            ctx.llm = LLMClient(req.model, req.llm_mode, req.ollama_url or config.OLLAMA_URL)
            state.llm_mode_used = ctx.llm.mode
            journal.log("orchestrator", "plan", "parse_query", 0, 0, "ok", plan=state.plan, llm_mode=ctx.llm.mode)
            for name in PIPELINE[:5]:
                self.dispatch(ctx, name)
            while True:
                review = self.dispatch(ctx, "critic")
                if review.type == MsgType.RESULT or state.revisions >= req.max_revisions:
                    break
                state.revisions += 1
                self.dispatch(ctx, "writer", {"feedback": review.payload["violations"] + state.reviews[-1].comments},
                              MsgType.REVISE, f"Доработка №{state.revisions}: {len(review.payload['violations'])} нарушений")
            state.status = "done"
            self.send(ctx, AgentMessage(sender="orchestrator", receiver="user", type=MsgType.DONE,
                                        summary="Готово: черновик Related Work проверен"))
        except LimitExceeded as e:
            state.status = "limit"
            state.errors.append({"code": e.code, "message": e.message, "hint": e.hint})
        except RAError as e:
            state.status = "failed"
            state.errors.append({"code": e.code, "message": e.message, "hint": e.hint})
        except Exception as e:  # noqa: BLE001
            state.status = "failed"
            state.errors.append({"code": "internal", "message": f"Внутренняя ошибка: {e}",
                                 "hint": "Посмотрите журнал прогона на странице «Журнал»."})
        finally:
            state.active_agent = ""
            state.elapsed = time.time() - state.started_at
            journal.log("orchestrator", "finish", state.status, state.elapsed, 0,
                        "ok" if state.status == "done" else state.status)
            state.save(run_dir / "state.json")
            if self.on_event:
                self.on_event(state, None)
        return state
