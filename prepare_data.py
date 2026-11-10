"""Подготовка данных: скачивание корпуса arXiv, индекс BM25, эмбеддинги MiniLM (.npy), SQLite.

Запуск: `python prepare_data.py [--hash]` (--hash — без нейросети, быстрые хеш-эмбеддинги).
"""
from __future__ import annotations

import argparse
import json
import pickle
import sqlite3
import sys
import time

import httpx
import numpy as np

from core import config
from tools.documents import tokenize


def download() -> list[dict]:
    """Скачивает jsonl-файлы корпуса (если их нет) и возвращает список статей."""
    config.DATA_DIR.mkdir(exist_ok=True)
    papers = []
    for name, url in config.CORPUS_URLS.items():
        path = config.DATA_DIR / name
        if not path.exists():
            print(f"Скачиваю {name} ...")
            with httpx.stream("GET", url, timeout=120, follow_redirects=True) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for chunk in r.iter_bytes():
                        f.write(chunk)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                p = json.loads(line)
                p["id"] = p.get("id") or p.get("arxiv_id")
                papers.append(p)
    seen, uniq = set(), []
    for p in papers:
        if p["id"] not in seen:
            seen.add(p["id"]); uniq.append(p)
    print(f"Статей в корпусе: {len(uniq)}")
    return uniq


def build(papers: list[dict], use_hash: bool) -> None:
    from rank_bm25 import BM25Okapi

    from tools.search import hash_embed

    d = config.INDEX_DIR
    d.mkdir(parents=True, exist_ok=True)
    texts = [f"{p['title']}. {p.get('abstract', '')}" for p in papers]
    t0 = time.time()
    with (d / "bm25.pkl").open("wb") as f:
        pickle.dump(BM25Okapi([tokenize(t) for t in texts]), f)
    print(f"BM25 готов за {time.time() - t0:.1f} с")
    kind = "hash"
    emb_path = d / "embeddings.npy"
    if not use_hash:
        try:
            from tools.search import minilm_embed

            t0 = time.time()
            emb = minilm_embed(texts)
            kind = "minilm"
            print(f"MiniLM-эмбеддинги за {time.time() - t0:.1f} с")
        except Exception as e:  # нет сети/библиотеки — запасной вариант
            print(f"MiniLM недоступен ({e}); использую хеш-эмбеддинги")
            emb = hash_embed(texts)
    else:
        emb = hash_embed(texts)
    np.save(emb_path, np.asarray(emb, dtype=np.float32))
    db = d / "papers.sqlite"
    db.unlink(missing_ok=True)
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE papers (id TEXT PRIMARY KEY, title TEXT, abstract TEXT, authors TEXT,"
                    " categories TEXT, primary_category TEXT, year INTEGER, publication_date TEXT)")
        con.execute("CREATE INDEX ix_year ON papers(year)")
        rows = []
        for p in papers:
            cats = p.get("categories", "")
            cats = " ".join(cats) if isinstance(cats, list) else str(cats)
            auth = p.get("authors", [])
            auth = auth if isinstance(auth, list) else [a.strip() for a in str(auth).split(",")]
            date = str(p.get("publication_date", ""))
            rows.append((p["id"], p["title"].strip(), p.get("abstract", "").strip(), json.dumps(auth, ensure_ascii=False),
                         cats, p.get("primary_category", cats.split()[0] if cats else ""),
                         int(date[:4]) if date[:4].isdigit() else None, date))
        con.executemany("INSERT INTO papers VALUES (?,?,?,?,?,?,?,?)", rows)
    (d / "meta.json").write_text(json.dumps({"ids": [p["id"] for p in papers], "embed_kind": kind,
                                             "n": len(papers)}), encoding="utf-8")
    print(f"Индекс сохранён в {d} (эмбеддинги: {kind})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash", action="store_true", help="быстрые хеш-эмбеддинги вместо MiniLM")
    a = ap.parse_args()
    build(download(), a.hash)
    sys.exit(0)
