"""pytest: инструменты (чтение, нарезка, z-нормировка) и правила проверяющего/отборщика."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.errors import FileMissing, TooShort, UnsupportedFormat  # noqa: E402
from core.models import Paper, RunRequest  # noqa: E402
from core.orchestrator import parse_query  # noqa: E402
from tools import rules  # noqa: E402
from tools.documents import chunk_text, read_document  # noqa: E402
from tools.search import hash_embed, zscore  # noqa: E402


def test_read_txt_and_errors(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("word " * 100, encoding="utf-8")
    assert len(read_document(p)) >= 200
    with pytest.raises(FileMissing):
        read_document(tmp_path / "none.txt")
    (tmp_path / "t.csv").write_text("a,b")
    with pytest.raises(UnsupportedFormat):
        read_document(tmp_path / "t.csv")
    (tmp_path / "s.txt").write_text("short")
    with pytest.raises(TooShort):
        read_document(tmp_path / "s.txt")


def test_chunking_respects_size():
    text = ("Sentence number one is here. " * 400)
    chunks = chunk_text(text, 2500)
    assert len(chunks) > 1 and all(len(c) <= 2600 for c in chunks)


def test_zscore_and_hash_embed():
    z = zscore(np.array([1.0, 2.0, 3.0]))
    assert abs(z.mean()) < 1e-6 and abs(z.std() - 1) < 1e-6
    e = hash_embed(["graph neural network", "graph neural network"])
    assert np.allclose(e[0] @ e[1], 1.0, atol=1e-5)


def test_citations_parsing():
    assert rules.extract_citations("a [1], b [2, 3] и [4–6].") == [1, 2, 3, 4, 5, 6]


GOOD = ("Первый абзац обзора описывает задачу и подходы к ней, опираясь на работу [1] и сравнение с другими "
        "методами, которые используются в литературе для решения той же задачи поиска похожих статей.\n\n"
        "Второй абзац рассматривает плотные модели [2] и их сочетание с лексическим поиском, а также отмечает, "
        "что гибридные методы показывают лучшее качество ранжирования на корпусах научных аннотаций.")


def test_check_draft_ok():
    assert rules.check_draft(GOOD, n_refs=2) == []


def test_check_draft_invented_and_paragraphs():
    v = rules.check_draft(GOOD.replace("[2]", "[7]"), n_refs=2)
    assert any("Выдуманные" in x for x in v)
    v = rules.check_draft("Один абзац [1] " * 20, n_refs=1)
    assert any("Абзацев" in x for x in v)
    v = rules.check_draft("Текст без ссылок. " * 20 + "\n\n" + "Ещё текст. " * 20, n_refs=1)
    assert any("нет ни одной ссылки" in x for x in v)


def test_check_draft_duplicates():
    par = "Это повторяющееся предложение об обзоре литературы со ссылкой на работу [1] и детали метода. " * 3
    v = rules.check_draft(par + "\n\n" + par, n_refs=1)
    assert any("повтор" in x.lower() for x in v)


def test_flag_papers():
    ps = [Paper(id="2401.00001v1", title="Hybrid retrieval of papers", authors=["A. Ivanov"]),
          Paper(id="2401.00001v2", title="Hybrid retrieval of papers v2", authors=["B. Petrov"]),
          Paper(id="2402.00002", title="Hybrid Retrieval of Papers!", authors=["C. Sidorov"]),
          Paper(id="2403.00003", title="Graph networks", authors=["a. ivanov"])]
    rules.flag_papers(ps)
    assert "другая версия" in ps[1].flags
    assert "похожий заголовок" in ps[2].flags
    assert "те же авторы" in ps[3].flags
    assert rules.is_blocking(ps[1]) and not rules.is_blocking(ps[3])


def test_claim_support():
    assert rules.claim_support("hybrid retrieval with bm25 [1]", "We use BM25 for hybrid retrieval.") == 1.0
    assert rules.claim_support("quantum chemistry [1]", "We use BM25.") == 0.0


def test_parse_query():
    r = parse_query(RunRequest(query="найди 8 статей 2021-2023 cs.CL фокус: dense retrieval"))
    assert (r.n_papers, r.year_from, r.year_to) == (8, 2021, 2023)
    assert r.categories == ["cs.CL"] and r.focus == "dense retrieval"
    r = parse_query(RunRequest(query="6 статей eess.SP physics.geo-ph"))
    assert r.categories == ["eess.SP", "physics.geo-ph"]
