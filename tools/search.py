"""Инструменты поисковика: гибридный поиск BM25 + MiniLM и фильтр метаданных SQLite.

Скор считает код: z-нормировка каждой части и `score = w·z(dense) + (1−w)·z(bm25)`, w=0.8.
"""
from __future__ import annotations

import json
import pickle
import sqlite3
from functools import lru_cache
from pathlib import Path

import numpy as np

from core import config
from tools.documents import tokenize

HASH_DIM = 384


def hash_embed(texts: list[str]) -> np.ndarray:
    """Запасные «эмбеддинги» (хеширование токенов), если sentence-transformers недоступен."""
    import zlib

    out = np.zeros((len(texts), HASH_DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        for tok in tokenize(t):
            out[i, zlib.crc32(tok.encode()) % HASH_DIM] += 1.0
    out /= np.linalg.norm(out, axis=1, keepdims=True) + 1e-9
    return out


@lru_cache(maxsize=1)
def _encoder():
    """all-MiniLM-L6-v2 через fastembed (ONNX, CPU, без torch)."""
    try:
        from fastembed import TextEmbedding

        return TextEmbedding(config.EMBED_MODEL, cache_dir=str(config.DATA_DIR / "models"), threads=8)
    except Exception:
        return None


def minilm_embed(texts: list[str]) -> np.ndarray:
    """Нормированные эмбеддинги MiniLM (бросает RuntimeError, если модель недоступна)."""
    enc = _encoder()
    if enc is None:
        raise RuntimeError("fastembed / MiniLM недоступен")
    X = np.asarray(list(enc.embed(texts, batch_size=64)), dtype=np.float32)
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


def embed(texts: list[str], kind: str | None = None) -> np.ndarray:
    """Эмбеддинги MiniLM или хеш-эмбеддинги — в зависимости от того, чем построен индекс."""
    kind = kind or Index.load().embed_kind
    if kind == "minilm":
        return minilm_embed(texts)
    return hash_embed(texts)


def zscore(x: np.ndarray) -> np.ndarray:
    sd = x.std()
    return (x - x.mean()) / sd if sd > 1e-9 else np.zeros_like(x)


class Index:
    """Загруженный индекс: BM25, матрица эмбеддингов, путь к SQLite."""

    _cached: "Index | None" = None

    def __init__(self, ids: list[str], bm25, emb: np.ndarray, embed_kind: str, db: Path) -> None:
        self.ids, self.bm25, self.emb, self.embed_kind, self.db = ids, bm25, emb, embed_kind, db

    @classmethod
    def load(cls, index_dir: Path = config.INDEX_DIR) -> "Index":
        if cls._cached is None:
            meta = json.loads((index_dir / "meta.json").read_text(encoding="utf-8"))
            with (index_dir / "bm25.pkl").open("rb") as f:
                bm25 = pickle.load(f)
            cls._cached = cls(meta["ids"], bm25, np.load(index_dir / "embeddings.npy"),
                              meta["embed_kind"], index_dir / "papers.sqlite")
        return cls._cached


def metadata_filter(year_from: int | None, year_to: int | None, categories: list[str],
                    db: Path | None = None) -> set[str]:
    """Возвращает id статей, прошедших фильтр по годам и категориям (SQLite)."""
    db = db or Index.load().db
    q, args = "SELECT id, categories || ' ' || primary_category FROM papers WHERE 1=1", []
    if year_from:
        q += " AND year >= ?"; args.append(year_from)
    if year_to:
        q += " AND year <= ?"; args.append(year_to)
    with sqlite3.connect(db) as con:
        rows = con.execute(q, args).fetchall()
    cats = [c.lower() for c in categories]
    return {i for i, c in rows if not cats or any(x in c.lower().split() for x in cats)}


def hybrid_search(query: str, k: int = config.CANDIDATES_K, allowed: set[str] | None = None,
                  w: float = config.DENSE_WEIGHT) -> list[dict]:
    """Гибридный поиск: возвращает top-k словарей с метаданными и тремя скорами."""
    idx = Index.load()
    bm = np.asarray(idx.bm25.get_scores(tokenize(query)), dtype=np.float32)
    qv = embed([query], idx.embed_kind)[0]
    dn = idx.emb @ qv
    score = w * zscore(dn) + (1 - w) * zscore(bm)
    if allowed is not None:
        mask = np.array([i in allowed for i in idx.ids])
        score = np.where(mask, score, -np.inf)
    order = [int(i) for i in np.argsort(-score)[:k] if np.isfinite(score[i])]
    ids = [idx.ids[i] for i in order]
    with sqlite3.connect(idx.db) as con:
        con.row_factory = sqlite3.Row
        rows = {r["id"]: dict(r) for r in con.execute(
            f"SELECT * FROM papers WHERE id IN ({','.join('?' * len(ids))})", ids)} if ids else {}
    out = []
    for i in order:
        r = rows[idx.ids[i]]
        out.append({
            "id": r["id"], "title": r["title"], "abstract": r["abstract"],
            "authors": json.loads(r["authors"]),
            "categories": list(dict.fromkeys([r["primary_category"]] + r["categories"].split())),
            "primary_category": r["primary_category"], "year": r["year"],
            "bm25": round(float(bm[i]), 3), "dense": round(float(dn[i]), 3), "score": round(float(score[i]), 3),
        })
    return out
