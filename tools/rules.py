"""Правила в коде: пометки отборщика и проверки проверяющего (critic)."""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from core.models import Paper
from tools.documents import tokenize

CITE_RE = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")


def base_id(arxiv_id: str) -> str:
    """Отрезает версию: 2401.01234v2 → 2401.01234."""
    return re.sub(r"v\d+$", "", arxiv_id.strip())


def norm_title(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def flag_papers(papers: list[Paper], title_threshold: float = 0.9) -> list[Paper]:
    """Помечает дубли, версии, похожие заголовки и статьи тех же авторов (правила в коде)."""
    seen_ids: dict[str, str] = {}
    for i, p in enumerate(papers):
        b = base_id(p.id)
        if b in seen_ids:
            p.flags.append("дубль" if seen_ids[b] == p.id else "другая версия")
        else:
            seen_ids[b] = p.id
        for q in papers[:i]:
            if "дубль" in p.flags or "другая версия" in p.flags:
                break
            if SequenceMatcher(None, norm_title(p.title), norm_title(q.title)).ratio() >= title_threshold:
                p.flags.append("похожий заголовок")
                break
        for q in papers[:i]:
            if set(a.lower() for a in p.authors) & set(a.lower() for a in q.authors):
                p.flags.append("те же авторы")
                break
    return papers


def is_blocking(p: Paper) -> bool:
    """Дубли/версии/почти одинаковые заголовки исключаются; «те же авторы» — только пометка."""
    return any(f in p.flags for f in ("дубль", "другая версия", "похожий заголовок"))


def extract_citations(text: str) -> list[int]:
    """Все номера ссылок [n], [n, m], [n–m] из текста."""
    nums: list[int] = []
    for grp in CITE_RE.findall(text):
        for part in re.split(r"\s*,\s*", grp):
            if re.search(r"[–-]", part):
                a, b = [int(x) for x in re.split(r"\s*[–-]\s*", part)]
                nums.extend(range(a, b + 1))
            else:
                nums.append(int(part))
    return nums


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def check_draft(text: str, n_refs: int, min_par: int = 2, max_par: int = 4,
                min_len: int = 150, max_len: int = 1600) -> list[str]:
    """Правила проверяющего. Возвращает список нарушений (пустой — всё в порядке)."""
    v: list[str] = []
    cites = extract_citations(text)
    if not cites:
        v.append("В тексте нет ни одной ссылки [n].")
    bad = sorted({c for c in cites if c < 1 or c > n_refs})
    if bad:
        v.append(f"Выдуманные ссылки (нет в списке отобранных): {bad}.")
    pars = paragraphs(text)
    if not (min_par <= len(pars) <= max_par):
        v.append(f"Абзацев {len(pars)}, ожидается {min_par}–{max_par}.")
    for i, p in enumerate(pars, 1):
        if not (min_len <= len(p) <= max_len):
            v.append(f"Абзац {i}: длина {len(p)} символов вне нормы {min_len}–{max_len}.")
    norm = [re.sub(r"\W+", " ", s.lower()).strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s) > 30]
    if len(norm) != len(set(norm)):
        v.append("Есть повторяющиеся предложения (дубли).")
    if len(set(pars)) != len(pars):
        v.append("Есть повторяющиеся абзацы.")
    return v


def claim_support(sentence: str, abstract: str) -> float:
    """Доля содержательных слов утверждения, встречающихся в аннотации (0..1)."""
    s = set(tokenize(CITE_RE.sub("", sentence)))
    a = set(tokenize(abstract))
    return len(s & a) / len(s) if s else 0.0


def cited_sentences(text: str) -> list[tuple[str, list[int]]]:
    """Пары (предложение, номера ссылок) для предложений со ссылками."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+", text):
        c = extract_citations(s)
        if c:
            out.append((s, c))
    return out
