"""Реализация шести агентов. У каждого агента не больше двух инструментов.

Роли задаются инструкциями (zero-shot); каждый ответ LLM валидируется pydantic-схемой.
Для каждого вызова LLM есть детерминированная эвристика (`fallback`) — она используется
в офлайн-режиме и при исчерпании повторов (изоляция сбоев).
"""
from __future__ import annotations

import re
from collections import Counter

import numpy as np
from pydantic import BaseModel, Field

from core.errors import LimitExceeded, NotScientific
from core.models import AgentMessage, MsgType, Paper, Review, ResearchTask, Theme
from tools import rules
from tools.documents import chunk_text, read_document, tokenize, top_terms
from tools.search import embed, hybrid_search, metadata_filter

SCI_WORDS = set("""method model algorithm dataset experiment evaluation accuracy benchmark learning neural
network training retrieval classification analysis approach framework results propose metric optimization
inference language transformer graph detection метод модель алгоритм данных эксперимент оценка точность
обучение нейронн сеть исследован задача анализ подход результат метрик классификац поиск agent code
generation benchmark pass correctness evaluate measure""".split())
SCI_STEMS = {w[:5] for w in SCI_WORDS}


# ---------- схемы ответов LLM ----------
class TaskOut(BaseModel):
    is_scientific: bool
    problem: str
    keywords: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    domain: str = ""


class JudgeOut(BaseModel):
    same_task: bool
    reason: str


class ThemesOut(BaseModel):
    themes: list[Theme]
    gaps: list[str] = Field(default_factory=list)


class DraftOut(BaseModel):
    paragraphs: list[str]


class ScoreOut(BaseModel):
    support: float = Field(ge=1, le=5)
    accuracy: float = Field(ge=1, le=5)
    completeness: float = Field(ge=1, le=5)
    comments: list[str] = Field(default_factory=list)


class Agent:
    """Базовый агент: имя, роль, список инструментов (≤ 2) и обработчик сообщения."""

    name = "agent"
    title = "Агент"
    tools: tuple[str, ...] = ()

    def tool(self, ctx, name: str, fn, *args, **kw):
        """Вызов инструмента с журналированием и проверкой лимитов."""
        assert name in self.tools, f"{self.name}: инструмент {name} не разрешён"
        return ctx.call_tool(self.name, name, fn, *args, **kw)

    def reply(self, payload: dict, summary: str, mtype: MsgType = MsgType.RESULT) -> AgentMessage:
        return AgentMessage(sender=self.name, receiver="orchestrator", type=mtype, payload=payload, summary=summary)

    def handle(self, msg: AgentMessage, ctx) -> AgentMessage:  # pragma: no cover
        raise NotImplementedError


# ---------- 1. Аналитик документа ----------
class DocumentAnalyst(Agent):
    name, title = "analyst", "Аналитик документа"
    tools = ("read_document", "chunk_text")

    def handle(self, msg, ctx):
        req = ctx.state.request
        text = req.topic_text or self.tool(ctx, "read_document", read_document, req.file_path)
        if req.topic_text and len(text.strip()) < 200:
            from core.errors import TooShort
            raise TooShort(f"Описание темы слишком короткое ({len(text.strip())} символов, нужно от 200).",
                           "Опишите задачу, данные и методы хотя бы в 2–3 предложениях.")
        chunks = self.tool(ctx, "chunk_text", chunk_text, text)
        head = "\n\n".join(chunks[:2])[:5000]

        def fb() -> dict:
            toks = tokenize(text)
            sci = sum(1 for t in toks if t[:5] in SCI_STEMS)
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 40]
            prob = next((s for s in sents if re.search(r"propose|address|aim|we study|задач|цель|предлага", s, re.I)),
                        sents[0] if sents else text[:200])
            meth = [t for t in top_terms(text, 20) if any(t.startswith(w) for w in
                    ("bert", "transformer", "neural", "graph", "retriev", "embed", "bm25", "lstm", "cnn", "llm",
                     "contrastive", "reinforcement", "bayes", "regress", "cluster", "attention", "diffusion"))][:4]
            return {"is_scientific": sci / max(len(toks), 1) > 0.04 and sci >= 5, "problem": prob[:400],
                    "keywords": top_terms(text, 8), "methods": meth, "domain": ""}

        out = ctx.llm.json(ctx, self.name,
                           "Ты — аналитик научного документа. Определи, содержит ли текст научную исследовательскую "
                           "задачу. Сформулируй задачу одним предложением на английском, выдели 5–8 ключевых "
                           "понятий (англ.) и методы.", head, TaskOut, fb)
        if not out.is_scientific or not out.problem.strip():
            raise NotScientific("В документе не найдена научная исследовательская задача.",
                                "Загрузите статью или опишите: какую проблему решаете, на каких данных и какими методами.")
        task = ResearchTask(problem=out.problem, keywords=out.keywords[:8], methods=out.methods[:6],
                            domain=out.domain, n_chunks=len(chunks), n_chars=len(text))
        ctx.state.task = task
        return self.reply({"task": task.model_dump()}, f"Задача: {task.problem[:90]}…")


# ---------- 2. Поисковик ----------
class Retriever(Agent):
    name, title = "retriever", "Поисковик"
    tools = ("metadata_filter", "hybrid_search")

    def handle(self, msg, ctx):
        req, task = ctx.state.request, ctx.state.task
        allowed = None
        if req.year_from or req.year_to or req.categories:
            allowed = self.tool(ctx, "metadata_filter", metadata_filter, req.year_from, req.year_to, req.categories)
        query = " ".join([task.problem, " ".join(task.keywords), " ".join(task.methods), req.focus])
        k = max(20, req.n_papers * 4)
        hits = self.tool(ctx, "hybrid_search", hybrid_search, query, k, allowed)
        ctx.state.candidates = [Paper(**h) for h in hits]
        return self.reply({"n_candidates": len(hits), "filtered": None if allowed is None else len(allowed)},
                          f"Найдено кандидатов: {len(hits)}" + ("" if allowed is None else f" (фильтр: {len(allowed)})"))


# ---------- 3. Отборщик релевантности ----------
class RelevanceSelector(Agent):
    name, title = "selector", "Отборщик релевантности"
    tools = ("flag_papers",)

    def handle(self, msg, ctx):
        st = ctx.state
        task = st.task
        papers = self.tool(ctx, "flag_papers", rules.flag_papers, st.candidates)
        kw = set(tokenize(" ".join(task.keywords + [task.problem])))
        scores = np.array([p.score for p in papers]) if papers else np.zeros(0)
        thr = float(np.quantile(scores, 0.4)) if len(scores) else 0.0
        need = st.request.n_papers
        n_ok = 0
        for p in papers:
            if n_ok >= need:
                p.reason = p.reason or "Не рассматривалась: набрано нужное число статей."
                continue
            if rules.is_blocking(p):
                p.same_task, p.reason = False, "Исключена правилом: " + ", ".join(p.flags)
                continue

            def fb(p=p) -> dict:
                ov = len(kw & set(tokenize(p.title + " " + p.abstract))) / max(len(kw), 1)
                ok = p.score >= thr and ov >= 0.15
                return {"same_task": ok, "reason": f"Пересечение ключевых понятий {ov:.0%}, гибридный скор {p.score:.2f}"
                        + (" — решает близкую задачу." if ok else " — другая задача или область.")}

            try:  # изоляция ошибок на уровне одной статьи
                out = ctx.llm.json(ctx, self.name,
                                   "Ты — отборщик литературы. Реши, решает ли статья ТУ ЖЕ исследовательскую задачу "
                                   "(а не просто из той же области). Обоснование — одно предложение на русском.",
                                   f"Задача: {task.problem}\n\nСтатья: {p.title}\n{p.abstract[:1200]}", JudgeOut, fb)
                p.same_task, p.reason = out.same_task, out.reason
            except LimitExceeded:
                raise
            except Exception as e:  # noqa: BLE001
                p.same_task, p.reason = False, f"Ошибка оценки: {e}"
                st.errors.append({"agent": self.name, "paper": p.id, "error": str(e)})
            if p.same_task:
                n_ok += 1
                p.selected, p.ref = True, n_ok
        # если LLM отсеял слишком много — добираем лучшими по скору (помечаем)
        if n_ok < min(need, 3):
            for p in papers:
                if n_ok >= min(need, 3):
                    break
                if not p.selected and not rules.is_blocking(p):
                    n_ok += 1
                    p.selected, p.ref = True, n_ok
                    p.flags.append("добрано по скору")
        return self.reply({"selected": [p.id for p in st.selected]}, f"Отобрано {n_ok} из {len(papers)}")


# ---------- 4. Синтезатор ----------
class Synthesizer(Agent):
    name, title = "synthesizer", "Синтезатор"
    tools = ("compute_stats", "cluster_papers")

    @staticmethod
    def compute_stats(sel: list[Paper]) -> dict:
        return {"by_year": dict(sorted(Counter(str(p.year) for p in sel).items())),
                "by_category": dict(Counter(p.primary_category for p in sel).most_common())}

    @staticmethod
    def cluster_papers(sel: list[Paper], k: int) -> list[list[int]]:
        """Детерминированный k-means (seed=42) по эмбеддингам аннотаций."""
        if len(sel) <= k:
            return [[i] for i in range(len(sel))]
        X = embed([p.title + ". " + p.abstract for p in sel])
        rng = np.random.default_rng(42)
        C = X[rng.choice(len(X), k, replace=False)]
        for _ in range(20):
            lab = np.argmax(X @ C.T, axis=1)
            C = np.stack([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
        return [list(map(int, np.where(lab == j)[0])) for j in range(k) if (lab == j).any()]

    def handle(self, msg, ctx):
        st = ctx.state
        sel = st.selected
        k = 2 if len(sel) <= 5 else 3
        groups = self.tool(ctx, "cluster_papers", self.cluster_papers, sel, k)

        def fb() -> dict:
            themes = []
            for g in groups:
                txt = " ".join(sel[i].title for i in g)
                name = ", ".join(top_terms(txt, 3)) or "прочие подходы"
                themes.append({"name": name.capitalize(), "description": f"{len(g)} работ(ы) с общими понятиями: {name}.",
                               "paper_ids": [sel[i].id for i in g]})
            covered = set(tokenize(" ".join(p.title + " " + p.abstract for p in sel)))
            gaps = [f"Слабо представлено в найденных работах: «{t}»" for t in st.task.keywords if
                    not set(tokenize(t)) <= covered][:3] or ["Мало работ с открытой оценкой на общих бенчмарках."]
            return {"themes": themes, "gaps": gaps}

        listing = "\n".join(f"{p.id}: {p.title}" for p in sel)
        hint = "\n".join("Группа: " + ", ".join(sel[i].id for i in g) for g in groups)
        out = ctx.llm.json(ctx, self.name,
                           "Ты — синтезатор обзора. Назови подходы (темы) для групп статей (название на русском, "
                           "описание в 1 предложении, paper_ids — только из списка) и найди 2–3 пробела в исследованиях.",
                           f"Задача: {st.task.problem}\nСтатьи:\n{listing}\nПредварительные группы:\n{hint}", ThemesOut, fb)
        valid = {p.id for p in sel}
        st.themes = [Theme(name=t.name, description=t.description, paper_ids=[i for i in t.paper_ids if i in valid])
                     for t in out.themes if any(i in valid for i in t.paper_ids)] or [Theme(**t) for t in fb()["themes"]]
        st.gaps = out.gaps[:4]
        stats = self.tool(ctx, "compute_stats", self.compute_stats, sel)
        stats["by_theme"] = {t.name: len(t.paper_ids) for t in st.themes}
        st.stats = stats
        return self.reply({"themes": [t.name for t in st.themes], "gaps": st.gaps}, f"Тем: {len(st.themes)}, пробелов: {len(st.gaps)}")


# ---------- 5. Писатель ----------
class Writer(Agent):
    name, title = "writer", "Писатель"
    tools = ()

    def handle(self, msg, ctx):
        st = ctx.state
        sel = st.selected
        ref = {p.id: p.ref for p in sel}
        feedback = msg.payload.get("feedback", [])

        def fb() -> dict:
            def theme_par(t: Theme) -> str:
                ps = [p for p in sel if p.id in t.paper_ids]
                sents = []
                for p in ps:
                    first = re.split(r"(?<=[.!?])\s+", p.abstract.strip())[0][:220].rstrip(".")
                    sents.append(f"В работе «{p.title}» [{p.ref}] отмечается: {first}.")
                return f"Направление «{t.name}» представлено {len(ps)} работами. " + " ".join(sents)

            intro = (f"Задача «{st.task.problem.rstrip('.')[:300]}» активно исследуется; ключевые понятия области — "
                     + ", ".join(st.task.keywords[:5]) + ". Ниже рассмотрены основные подходы.")
            tps = [theme_par(t) for t in st.themes]
            pars = [intro] + tps[:2]
            if len(tps) > 2:
                pars[0] += " " + " ".join(tps[2:])
            gaps = "; ".join(g.rstrip('.') for g in st.gaps[:3]) or "нет единого протокола сравнения"
            pars.append(f"Вместе с тем остаются открытые вопросы: {gaps}. Эти пробелы мотивируют предлагаемое "
                        f"исследование и требуют сравнения с подходами из [{sel[0].ref if sel else 1}].")
            return {"paragraphs": pars[:4]}

        refs = "\n".join(f"[{p.ref}] {p.title} ({p.year}): {p.abstract[:500]}" for p in sel)
        themes = "\n".join(f"- {t.name}: " + ", ".join(f"[{ref[i]}]" for i in t.paper_ids if i in ref) for t in st.themes)
        fbk = ("\nЗамечания проверяющего, исправь их:\n- " + "\n- ".join(feedback)) if feedback else ""
        out = ctx.llm.json(ctx, self.name,
                           "Ты — писатель раздела Related Work. Напиши 2–4 абзаца на русском (каждый 300–1200 символов). "
                           "Ссылайся ТОЛЬКО номерами [n] из списка; не выдумывай фактов, которых нет в аннотациях.",
                           f"Задача: {st.task.problem}\nТемы:\n{themes}\nПробелы: {st.gaps}\nСписок:\n{refs}{fbk}",
                           DraftOut, fb)
        text = "\n\n".join(p.strip() for p in out.paragraphs if p.strip())
        st.drafts.append(text)
        return self.reply({"version": len(st.drafts)}, f"Черновик v{len(st.drafts)}: {len(out.paragraphs)} абз.")


# ---------- 6. Проверяющий ----------
class Critic(Agent):
    name, title = "critic", "Проверяющий"
    tools = ("check_draft", "claim_support")

    def handle(self, msg, ctx):
        st = ctx.state
        sel = st.selected
        text = st.draft
        violations = self.tool(ctx, "check_draft", rules.check_draft, text, len(sel))
        by_ref = {p.ref: p for p in sel}
        pairs = rules.cited_sentences(text)
        sup = self.tool(ctx, "claim_support", lambda: [
            max((rules.claim_support(s, by_ref[c].abstract) for c in cs if c in by_ref), default=0.0) for s, cs in pairs])
        cited = set(rules.extract_citations(text))

        def fb() -> dict:
            s = float(np.mean(sup)) if sup else 0.0
            cov = len(cited & set(by_ref)) / max(len(by_ref), 1)
            return {"support": round(1 + 4 * min(1.0, s * 2.5), 1), "accuracy": 4.0 if not violations else 2.0,
                    "completeness": round(1 + 4 * cov, 1),
                    "comments": [f"Не процитированы: {sorted(set(by_ref) - cited)}"] if cov < 1 else []}

        refs = "\n".join(f"[{p.ref}] {p.title}: {p.abstract[:400]}" for p in sel)
        out = ctx.llm.json(ctx, self.name,
                           "Ты — строгий рецензент. Оцени черновик по шкале 1–5: support (подтверждаются ли утверждения "
                           "аннотациями), accuracy (точность ссылок), completeness (полнота охвата). Дай замечания на русском.",
                           f"Черновик:\n{text}\n\nИсточники:\n{refs}", ScoreOut, fb)
        scores = {"support": out.support, "accuracy": out.accuracy, "completeness": out.completeness,
                  "support_rule": round(float(np.mean(sup)) if sup else 0.0, 3)}
        passed = not violations and min(out.support, out.accuracy, out.completeness) > 2
        st.reviews.append(Review(version=len(st.drafts), rule_violations=violations, scores=scores,
                                 comments=out.comments, passed=passed))
        mtype = MsgType.RESULT if passed else MsgType.REVISE
        return self.reply({"passed": passed, "violations": violations, "scores": scores},
                          ("Принято" if passed else "На доработку") + f": нарушений {len(violations)}, "
                          f"оценки {out.support:.0f}/{out.accuracy:.0f}/{out.completeness:.0f}", mtype)


AGENTS: dict[str, Agent] = {a.name: a for a in (DocumentAnalyst(), Retriever(), RelevanceSelector(),
                                                 Synthesizer(), Writer(), Critic())}
