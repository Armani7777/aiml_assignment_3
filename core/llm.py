"""Клиент локальной LLM (Ollama, format=json) с валидацией pydantic и повторами.

Режим `offline` — детерминированный эвристический заменитель LLM: каждый агент
передаёт `fallback`, который строит ответ той же схемы. Нужен, чтобы система и
тесты работали без Ollama; в журнале такие вызовы помечаются `mode=offline`.
"""
from __future__ import annotations

import json
import time
from typing import Callable, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from core import config
from core.errors import OllamaUnavailable

T = TypeVar("T", bound=BaseModel)


def ollama_available(url: str = config.OLLAMA_URL, model: str | None = None) -> bool:
    """Проверяет, что сервер Ollama отвечает (и, если задано, модель скачана)."""
    try:
        r = httpx.get(f"{url}/api/tags", timeout=2.0)
        r.raise_for_status()
        if model is None:
            return True
        names = {m["name"] for m in r.json().get("models", [])}
        return model in names or f"{model}:latest" in names
    except Exception:
        return False


class LLMClient:
    """Обёртка над Ollama /api/chat. Каждый вызов журналируется через `ctx`."""

    def __init__(self, model: str, mode: str = "auto", url: str = config.OLLAMA_URL) -> None:
        self.model = model
        self.url = url
        if mode == "auto":
            mode = "ollama" if ollama_available(url, model) else "offline"
        elif mode == "ollama" and not ollama_available(url):
            raise OllamaUnavailable(
                "Ollama не запущена или недоступна по адресу " + url,
                "Выполните `ollama serve` в терминале и `ollama pull " + model + "`, "
                "либо выберите режим «офлайн (эвристики)» в настройках.",
            )
        self.mode = mode

    def json(self, ctx, agent: str, system: str, user: str, schema: type[T],
             fallback: Callable[[], dict]) -> T:
        """Возвращает ответ, валидированный схемой `schema`. При невалидном JSON — повтор."""
        ctx.tick()
        if self.mode == "offline":
            t0 = time.time()
            obj = schema.model_validate(fallback())
            ctx.state.llm_calls += 1
            ctx.journal.log(agent, "llm", schema.__name__, time.time() - t0, 0, "ok", mode="offline")
            return obj
        last_err = ""
        for attempt in range(config.LLM_RETRIES + 1):
            t0 = time.time()
            try:
                r = httpx.post(
                    f"{self.url}/api/chat",
                    json={
                        "model": self.model,
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": config.TEMPERATURE, "seed": config.SEED},
                        "messages": [
                            {"role": "system", "content": system + "\nОтвечай только JSON по схеме: "
                             + json.dumps(schema.model_json_schema(), ensure_ascii=False)},
                            {"role": "user", "content": user},
                        ],
                    },
                    timeout=300.0,
                )
                r.raise_for_status()
                data = r.json()
                tokens = int(data.get("prompt_eval_count", 0)) + int(data.get("eval_count", 0))
                obj = schema.model_validate(json.loads(data["message"]["content"]))
                ctx.state.llm_calls += 1
                ctx.journal.log(agent, "llm", schema.__name__, time.time() - t0, tokens, "ok",
                                mode="ollama", attempt=attempt)
                return obj
            except (ValidationError, json.JSONDecodeError, KeyError) as e:
                last_err = f"невалидный JSON: {e}"[:300]
            except httpx.HTTPError as e:
                last_err = f"сбой HTTP: {e}"[:300]
            ctx.journal.log(agent, "llm", schema.__name__, time.time() - t0, 0, "retry",
                            mode="ollama", attempt=attempt, error=last_err)
        # все попытки исчерпаны — изолируем сбой: эвристический ответ
        ctx.journal.log(agent, "llm", schema.__name__, 0, 0, "fallback", error=last_err)
        return schema.model_validate(fallback())
