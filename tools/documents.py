"""Инструменты аналитика документа: чтение TXT/DOCX/PDF и нарезка на фрагменты."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from core import config
from core.errors import FileMissing, TooShort, UnsupportedFormat

SUPPORTED = {".txt", ".md", ".docx", ".pdf"}

STOP = set("""a an the of and or for to in on with by from as at is are was were be been this that these
those we our us it its into via using use used based than which such can may also not their they
over under between both more most other new study paper approach method methods results show
propose proposed work task problem data model models и в во на с по для из к что как это мы не
о об от до при а но или же ли то""".split())


def read_document(path: str | Path) -> str:
    """Читает файл и возвращает текст. Бросает понятные ошибки входа."""
    p = Path(path)
    if not p.exists():
        raise FileMissing(f"Файл «{p.name}» не найден.", "Проверьте путь или загрузите файл заново.")
    ext = p.suffix.lower()
    if ext not in SUPPORTED:
        raise UnsupportedFormat(
            f"Формат «{ext or 'без расширения'}» не поддерживается.",
            "Загрузите статью в формате TXT, DOCX или PDF.",
        )
    if ext in {".txt", ".md"}:
        text = p.read_text(encoding="utf-8", errors="ignore")
    elif ext == ".docx":
        import docx

        text = "\n".join(par.text for par in docx.Document(str(p)).paragraphs)
    else:
        from pypdf import PdfReader

        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    text = re.sub(r"[ \t]+", " ", text).strip()
    if len(text) < config.MIN_DOC_CHARS:
        raise TooShort(
            f"Текст слишком короткий ({len(text)} символов, нужно от {config.MIN_DOC_CHARS}).",
            "Добавьте аннотацию или 1–2 абзаца с описанием задачи исследования.",
        )
    return text


def chunk_text(text: str, size: int = config.CHUNK_SIZE) -> list[str]:
    """Режет текст на фрагменты ~`size` символов по границам абзацев/предложений."""
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    chunks, cur = [], ""
    for s in parts:
        if len(cur) + len(s) + 1 > size and cur:
            chunks.append(cur.strip())
            cur = ""
        cur += s + " "
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def tokenize(text: str) -> list[str]:
    """Простая токенизация для BM25 и эвристик."""
    return [t for t in re.findall(r"[a-zа-яё][a-zа-яё0-9\-]+", text.lower()) if t not in STOP and len(t) > 2]


def top_terms(text: str, k: int = 8) -> list[str]:
    """Частотные термины и биграммы (эвристика выделения ключевых слов)."""
    toks = tokenize(text)
    bi = Counter(f"{a} {b}" for a, b in zip(toks, toks[1:]))
    uni = Counter(toks)
    terms = [b for b, c in bi.most_common(k) if c > 1][: k // 2]
    for w, _ in uni.most_common(k * 2):
        if len(terms) >= k:
            break
        if not any(w in t for t in terms):
            terms.append(w)
    return terms
