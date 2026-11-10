"""Понятные ошибки входа, окружения и лимитов."""
from __future__ import annotations


class RAError(Exception):
    """Базовая ошибка с подсказкой для пользователя."""

    code = "error"

    def __init__(self, message: str, hint: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class InputError(RAError):
    code = "input"


class UnsupportedFormat(InputError):
    code = "unsupported_format"


class FileMissing(InputError):
    code = "file_missing"


class TooShort(InputError):
    code = "too_short"


class NotScientific(InputError):
    code = "not_scientific"


class OllamaUnavailable(RAError):
    code = "ollama_unavailable"


class LimitExceeded(RAError):
    code = "limit"


class StepLimit(LimitExceeded):
    code = "step_limit"


class TimeLimit(LimitExceeded):
    code = "time_limit"
