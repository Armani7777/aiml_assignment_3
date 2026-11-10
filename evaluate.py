"""Оценка ResearchAssist: 15 сценариев × 3 прогона, нагрузка по агентам, сравнение с «одним агентом».

Запуск: `python evaluate.py [--llm offline|auto|ollama] [--repeats 3]`.
Результаты: results/*.csv, results/*.json, results/*.png.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from core import config  # noqa: E402
from core.journal import Journal, read_journal  # noqa: E402
from core.llm import LLMClient  # noqa: E402
from core.models import RunRequest, TaskState  # noqa: E402
from core.orchestrator import Context, Orchestrator  # noqa: E402
from tools import rules  # noqa: E402
from tools.documents import tokenize  # noqa: E402

IN = config.SCENARIO_DIR / "inputs"
R = config.RESULTS_DIR
AGENT_NAMES = ["analyst", "retriever", "selector", "synthesizer", "writer", "critic"]
COL = {"ma": "#4F46E5", "base": "#F59E0B", "teal": "#0EA5A4", "grey": "#9CA3AF"}


def _done(s: TaskState) -> bool:
    return s.status == "done" and len(s.selected) > 0 and bool(s.draft)


def _err(code: str):
    return lambda s: s.status in ("failed", "limit") and s.errors and s.errors[0]["code"] == code \
        and bool(s.errors[0].get("hint")) and (config.RUNS_DIR / s.run_id / "state.json").exists()


SCENARIOS: list[dict] = [
    dict(id="S01", group="содержательный", name="Типовой запуск (TXT)", req=dict(file_path=IN / "retrieval_paper.txt"),
         check=lambda s: _done(s) and len(s.selected) == s.request.n_papers),
    dict(id="S02", group="содержательный", name="Фокус на годах 2021–2023",
         req=dict(file_path=IN / "retrieval_paper.txt", query="2021-2023"),
         check=lambda s: _done(s) and all(2021 <= (p.year or 0) <= 2023 for p in s.selected)),
    dict(id="S03", group="содержательный", name="Фокус на категории cs.IR",
         req=dict(file_path=IN / "retrieval_paper.txt", categories=["cs.IR"]),
         check=lambda s: _done(s) and all("cs.IR" in p.categories for p in s.selected)),
    dict(id="S04", group="содержательный", name="Другое число статей (4)",
         req=dict(file_path=IN / "multiagent_topic.txt", query="найди 4 статьи"),
         check=lambda s: _done(s) and len(s.selected) == 4),
    dict(id="S05", group="содержательный", name="Вход DOCX (RAG)", req=dict(file_path=IN / "rag_paper.docx"),
         check=_done),
    dict(id="S06", group="содержательный", name="Вход PDF (GNN)", req=dict(file_path=IN / "gnn_paper.pdf"),
         check=_done),
    dict(id="S07", group="содержательный", name="Расплывчатый текст", req=dict(file_path=IN / "vague_text.txt"),
         check=lambda s: _done(s) or _err("not_scientific")(s)),
    dict(id="S08", group="ошибки входа", name="Нет научной задачи", req=dict(file_path=IN / "not_scientific.txt"),
         check=_err("not_scientific")),
    dict(id="S09", group="ошибки входа", name="Слишком короткий файл", req=dict(file_path=IN / "too_short.txt"),
         check=_err("too_short")),
    dict(id="S10", group="ошибки входа", name="Неверный формат (CSV)", req=dict(file_path=IN / "table.csv"),
         check=_err("unsupported_format")),
    dict(id="S11", group="ошибки входа", name="Нет файла", req=dict(file_path=IN / "missing.txt"),
         check=_err("file_missing")),
    dict(id="S12", group="ошибки окружения", name="Ollama выключена",
         req=dict(file_path=IN / "retrieval_paper.txt", llm_mode="ollama", ollama_url="http://127.0.0.1:9"),
         check=_err("ollama_unavailable")),
    dict(id="S13", group="защиты", name="Лимит шагов (10)", req=dict(file_path=IN / "retrieval_paper.txt", max_steps=10),
         check=lambda s: _err("step_limit")(s) and s.steps <= 11),
    dict(id="S14", group="защиты", name="Лимит времени (0,05 с)",
         req=dict(file_path=IN / "retrieval_paper.txt", max_seconds=0.05), check=_err("time_limit")),
    dict(id="S15", group="защиты", name="MAX_REVISIONS = 0",
         req=dict(file_path=IN / "retrieval_paper.txt", max_revisions=0),
         check=lambda s: s.status == "done" and s.revisions == 0 and len(s.drafts) == 1),
]
BASELINE_SCENARIOS = ["S01", "S05", "S06"]


# ------------------------------------------------------------------ базовая схема «один агент»
class BaselineOut(BaseModel):
    paragraphs: list[str]


def run_baseline(ma: TaskState, llm_mode: str) -> dict:
    """Один агент: та же модель, тот же документ и тот же список кандидатов; один запрос, без инструментов и критика."""
    st = TaskState(run_id=ma.run_id + "-baseline", request=ma.request.model_copy(update={"max_steps": 10**6,
                                                                                         "max_seconds": 10**6}))
    st.task = ma.task
    journal = Journal(config.RUNS_DIR / st.run_id / "journal.jsonl")
    llm = LLMClient(ma.request.model, "offline" if ma.llm_mode_used == "offline" else llm_mode)
    ctx = Context(st, journal, llm)
    cands = ma.candidates
    n = ma.request.n_papers
    t0 = time.time()

    def fb() -> dict:  # наивный «один проход»: первые n кандидатов по скору, без правил и отбора
        sents = [f"«{p.title}» [{i}] — {re.split(r'(?<=[.!?])\s+', p.abstract)[0][:200]}"
                 for i, p in enumerate(cands[:n], 1)]
        half = max(1, len(sents) // 2)
        return {"paragraphs": ["Близкие работы: " + " ".join(sents[:half]), "Также: " + " ".join(sents[half:])]}

    listing = "\n".join(f"[{i}] {p.title} ({p.year}): {p.abstract[:400]}" for i, p in enumerate(cands, 1))
    out = llm.json(ctx, "single_agent", "Напиши раздел Related Work (2–4 абзаца, русский) по задаче, выбрав ровно "
                   f"{n} статей из списка и ссылаясь на них номерами [n].",
                   f"Задача: {ma.task.problem}\n\nСписок кандидатов:\n{listing}", BaselineOut, fb)
    text = "\n\n".join(out.paragraphs)
    return {"text": text, "refs": {i: p for i, p in enumerate(cands, 1)}, "time": time.time() - t0, "llm_calls": st.llm_calls}


def text_metrics(text: str, refs: dict, n: int, themes: list, elapsed: float, llm_calls: int) -> dict:
    """Метрики качества текста, одинаковые для обеих схем."""
    cites = rules.extract_citations(text)
    halluc = sum(1 for c in cites if c not in refs) / max(len(cites), 1)
    pairs = rules.cited_sentences(text)
    supp = [max((rules.claim_support(s, refs[c].abstract) for c in cs if c in refs), default=0) >= 0.3 for s, cs in pairs]
    cited = [refs[c] for c in sorted(set(cites)) if c in refs]
    base_ids = Counter(rules.base_id(p.id) for p in cited)
    dups = sum(v - 1 for v in base_ids.values())
    for i, p in enumerate(cited):
        dups += any(rules.norm_title(p.title) == rules.norm_title(q.title) for q in cited[:i])
    cited_ids = {p.id for p in cited}
    cov = np.mean([any(i in cited_ids for i in t.paper_ids) for t in themes]) if themes else 0.0
    return {"hallucinated_refs": round(halluc, 3), "supported_claims": round(float(np.mean(supp)) if supp else 0.0, 3),
            "n_compliance": int(len(set(c for c in cites if c in refs)) == n), "duplicates": dups,
            "topic_coverage": round(float(cov), 3), "time_s": round(elapsed, 2), "llm_calls": llm_calls}


# ------------------------------------------------------------------ графики
def _style(ax, title):
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left", color="#1E2235")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="y", color="#E6E8F0", linewidth=0.8)
    ax.set_axisbelow(True)


def plots(load: pd.Series, critic: pd.DataFrame, comp: pd.DataFrame, runs: pd.DataFrame) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.bar(load.index, load.values * 100, color=COL["ma"])
    ax.axhline(40, color="#DC2626", linestyle="--", linewidth=1)
    ax.text(len(load) - 0.5, 41, "порог 40%", color="#DC2626", ha="right", fontsize=9)
    for i, v in enumerate(load.values):
        ax.text(i, v * 100 + 1, f"{v:.0%}", ha="center", fontsize=9)
    ax.set_ylabel("% вызовов LLM и инструментов")
    _style(ax, "Нагрузка по агентам")
    fig.tight_layout(); fig.savefig(R / "agent_load.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 3.8))
    x = np.arange(len(critic))
    for j, (c, color) in enumerate(zip(["support", "accuracy", "completeness"], [COL["ma"], COL["teal"], COL["base"]])):
        ax.bar(x + (j - 1) * 0.26, critic[c], 0.26, label={"support": "подтверждённость", "accuracy": "точность",
                                                         "completeness": "полнота"}[c], color=color)
    ax.set_xticks(x, critic.index); ax.set_ylim(0, 5.3); ax.set_ylabel("оценка 1–5")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    _style(ax, "Оценки проверяющего по критериям (финальная версия)")
    fig.tight_layout(); fig.savefig(R / "critic_scores.png", dpi=150); plt.close(fig)

    metrics = ["hallucinated_refs", "supported_claims", "n_compliance", "topic_coverage"]
    labels = ["выдуманные\nссылки", "подтверждённые\nутверждения", "соблюдение\nчисла статей", "покрытие\nтем"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), gridspec_kw={"width_ratios": [3, 2]})
    x = np.arange(len(metrics))
    ma, bs = comp[comp.system == "многоагентная"].iloc[0], comp[comp.system == "один агент"].iloc[0]
    axes[0].bar(x - 0.2, [ma[m] for m in metrics], 0.4, label="многоагентная", color=COL["ma"])
    axes[0].bar(x + 0.2, [bs[m] for m in metrics], 0.4, label="один агент", color=COL["base"])
    axes[0].set_xticks(x, labels); axes[0].set_ylim(0, 1.1); axes[0].legend(frameon=False)
    _style(axes[0], "Качество (доли, среднее по 3×3 запускам)")
    axes[1].bar(["дубли", "вызовы LLM"], [ma["duplicates"], ma["llm_calls"]], -0.4, align="edge", color=COL["ma"])
    axes[1].bar(["дубли", "вызовы LLM"], [bs["duplicates"], bs["llm_calls"]], 0.4, align="edge", color=COL["base"])
    _style(axes[1], "Дубли и стоимость")
    fig.tight_layout(); fig.savefig(R / "baseline_comparison.png", dpi=150); plt.close(fig)

    t = runs.groupby("scenario")["time_s"].mean()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.bar(t.index, t.values, color=[COL["ma"] if i <= "S07" else COL["grey"] for i in t.index])
    ax.set_ylabel("среднее время, с")
    _style(ax, "Время по сценариям (среднее по 3 прогонам)")
    fig.tight_layout(); fig.savefig(R / "time_by_scenario.png", dpi=150); plt.close(fig)


# ------------------------------------------------------------------ основной цикл
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", default="offline", choices=["offline", "auto", "ollama"])
    ap.add_argument("--model", default="qwen2.5:3b")
    ap.add_argument("--repeats", type=int, default=3)
    a = ap.parse_args()
    np.random.seed(config.SEED)
    R.mkdir(exist_ok=True)
    orch = Orchestrator()
    rows, states = [], {}
    for sc in SCENARIOS:
        for rep in range(a.repeats):
            req = dict(sc["req"])
            req["file_path"] = str(req["file_path"])
            req.setdefault("llm_mode", a.llm)
            run_id = f"eval-{sc['id']}-r{rep + 1}"
            s = orch.run(RunRequest(model=a.model, **req), run_id)
            ok = bool(sc["check"](s))
            final = s.reviews[-1].scores if s.reviews else {}
            rows.append({"scenario": sc["id"], "group": sc["group"], "name": sc["name"], "repeat": rep + 1,
                         "success": int(ok), "status": s.status, "error": s.errors[0]["code"] if s.errors else "",
                         "n_selected": len(s.selected), "steps": s.steps, "llm_calls": s.llm_calls,
                         "revisions": s.revisions, "time_s": round(s.elapsed, 2), "llm_mode": s.llm_mode_used,
                         "support": final.get("support"), "accuracy": final.get("accuracy"),
                         "completeness": final.get("completeness"), "run_id": run_id})
            states[(sc["id"], rep)] = s
            print(f"{sc['id']} r{rep + 1}: {'OK ' if ok else 'FAIL'} {s.status:7s} {s.elapsed:6.2f}s  {sc['name']}")
    runs = pd.DataFrame(rows)
    runs.to_csv(R / "runs.csv", index=False)

    table = runs.groupby(["scenario", "group", "name"], sort=False).agg(
        успешно=("success", "sum"), прогонов=("success", "size"), статус=("status", "first"), ошибка=("error", "first"),
        статей=("n_selected", "mean"), шагов=("steps", "mean"), вызовов_LLM=("llm_calls", "mean"),
        доработок=("revisions", "mean"), время_с=("time_s", "mean")).reset_index()
    table = table.rename(columns={"scenario": "id", "group": "группа", "name": "сценарий"}).round(2)
    table.to_csv(R / "scenarios_table.csv", index=False)

    # нагрузка по агентам (вызовы LLM + инструментов), по всем прогонам
    cnt = Counter()
    for rid in runs.run_id:
        for e in read_journal(config.RUNS_DIR / rid / "journal.jsonl"):
            if e["kind"] in ("llm", "tool") and e["status"] in ("ok", "fallback"):
                cnt[e["agent"]] += 1
    load = pd.Series({k: cnt.get(k, 0) for k in AGENT_NAMES}, dtype=float)
    load = load / load.sum()
    load.rename("share").to_frame().to_csv(R / "agent_load.csv")

    content = runs[(runs.group == "содержательный") & (runs.status == "done")]
    critic = content.groupby("scenario")[["support", "accuracy", "completeness"]].mean().round(2)
    critic.to_csv(R / "critic_scores.csv")

    # сравнение с одним агентом
    comp_rows = []
    for sid in BASELINE_SCENARIOS:
        for rep in range(a.repeats):
            s = states[(sid, rep)]
            if s.status != "done":
                continue
            ma_m = text_metrics(s.draft, {p.ref: p for p in s.selected}, s.request.n_papers, s.themes,
                                s.elapsed, s.llm_calls)
            b = run_baseline(s, a.llm)
            b_m = text_metrics(b["text"], b["refs"], s.request.n_papers, s.themes, b["time"], b["llm_calls"])
            comp_rows += [{"scenario": sid, "repeat": rep + 1, "system": "многоагентная", **ma_m},
                          {"scenario": sid, "repeat": rep + 1, "system": "один агент", **b_m}]
    comp_runs = pd.DataFrame(comp_rows)
    comp_runs.to_csv(R / "baseline_runs.csv", index=False)
    comp = comp_runs.drop(columns=["scenario", "repeat"]).groupby("system", sort=False).mean().round(3).reset_index()
    comp.to_csv(R / "baseline_comparison.csv", index=False)

    plots(load, critic, comp, runs)
    summary = {"llm_mode": ", ".join(sorted(set(runs.llm_mode) - {""})) or a.llm, "model": a.model,
               "n_runs": len(runs), "success_rate": round(runs.success.mean(), 3),
               "success_requirement_met": bool(runs.success.mean() >= 0.9),
               "max_agent_share": round(float(load.max()), 3), "load_requirement_met": bool(load.max() <= 0.4),
               "agent_load": load.round(3).to_dict(), "baseline": comp.to_dict(orient="records"),
               "seed": config.SEED, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    (R / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
