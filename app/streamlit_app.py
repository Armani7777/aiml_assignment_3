"""Веб-интерфейс ResearchAssist (Streamlit): Запуск · Ход работы · Результаты · Эксперименты · Журнал."""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from app import ui  # noqa: E402
from app.export import to_docx, to_markdown  # noqa: E402
from core import config  # noqa: E402
from core.journal import read_journal  # noqa: E402
from core.llm import ollama_available  # noqa: E402
from core.models import MsgType, RunRequest  # noqa: E402
from core.orchestrator import Orchestrator  # noqa: E402

st.set_page_config(page_title="ResearchAssist", page_icon="📚", layout="wide")
ui.apply_theme()
REG = ui.run_registry()
SAMPLES = {
    "★ Демо: галлюцинации в RAG (TXT)": "demo_rag_hallucination.txt",
    "Гибридный поиск похожих статей (TXT)": "retrieval_paper.txt",
    "Retrieval-Augmented Generation (DOCX)": "rag_paper.docx",
    "GNN для молекул (PDF)": "gnn_paper.pdf",
    "Многоагентные LLM-системы (TXT)": "multiagent_topic.txt",
    "Расплывчатый текст": "vague_text.txt",
    "Документ без научной задачи": "not_scientific.txt",
    "Слишком короткий файл": "too_short.txt",
    "Неподдерживаемый формат (CSV)": "table.csv",
}


# ---------------------------------------------------------------- 1. Запуск
def page_launch() -> None:
    ui.hero("📚 ResearchAssist", "Многоагентный помощник для поиска и анализа научной литературы · "
            "локально, офлайн, на корпусе arXiv (20 000 статей)")
    ok = ollama_available()
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.subheader("1. Исходный документ")
        src = st.radio("Источник", ["Пример из набора", "Загрузить файл", "Ввести тему"], horizontal=True,
                       label_visibility="collapsed")
        file_path, topic = None, None
        if src == "Пример из набора":
            name = st.selectbox("Тестовый документ", list(SAMPLES))
            file_path = str(config.SCENARIO_DIR / "inputs" / SAMPLES[name])
        elif src == "Загрузить файл":
            up = st.file_uploader("Статья или описание темы", type=None, help="TXT, DOCX или PDF")
            if up:
                d = config.RUNS_DIR / "_uploads"
                d.mkdir(parents=True, exist_ok=True)
                fp = d / up.name
                fp.write_bytes(up.getvalue())
                file_path = str(fp)
        else:
            topic = st.text_area("Описание темы исследования (лучше на английском — корпус англоязычный)", height=180,
                                 placeholder="We study ... using ... evaluated on ...")
        query = st.text_input("Запрос в свободной форме (необязательно)",
                              placeholder="например: 8 статей 2021-2024 cs.CL фокус: dense retrieval")
    with c2:
        st.subheader("2. Настройки")
        n = st.slider("Число статей", 3, 12, 6)
        y1, y2 = st.columns(2)
        yf = y1.number_input("Год с", 2000, 2026, 2020)
        yt = y2.number_input("Год по", 2000, 2026, 2026)
        cats = st.multiselect("Категории arXiv", ["cs.CL", "cs.IR", "cs.LG", "cs.AI", "cs.CV", "cs.SE", "stat.ML",
                                                  "q-bio.QM", "physics.chem-ph"])
        m1, m2 = st.columns(2)
        model = m1.selectbox("Модель", config.AVAILABLE_MODELS, help="qwen2.5:3b — для слабого ПК")
        max_rev = m2.number_input("MAX_REVISIONS", 0, 3, 1)
        mode = st.selectbox("Режим LLM", ["auto", "ollama", "offline"],
                            format_func={"auto": "Авто (Ollama, если запущена)", "ollama": "Только Ollama",
                                         "offline": "Офлайн-эвристики (без LLM)"}.get)
        slow = st.toggle("Замедлить анимацию для показа", value=True)
        st.markdown(ui.chips(["Ollama: запущена" if ok else "Ollama: не запущена"], "teal" if ok else "red"),
                    unsafe_allow_html=True)
        if not ok:
            st.caption("Без Ollama в режиме «Авто» используются детерминированные эвристики. "
                       "Для LLM выполните `ollama serve` и `ollama pull qwen2.5:7b`.")
    st.write("")
    if st.button("🚀 Запустить", type="primary", use_container_width=True):
        req = RunRequest(file_path=file_path, topic_text=topic, query=query, n_papers=n, year_from=int(yf),
                         year_to=int(yt), categories=cats, model=model, llm_mode=mode, max_revisions=int(max_rev))
        if not file_path and not (topic and topic.strip()):
            req.file_path = str(config.RUNS_DIR / "_uploads" / "__нет_файла__.txt")
        start_run(req, slow)
        st.switch_page(PAGES["live"])


def start_run(req: RunRequest, slow: bool) -> str:
    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    holder = {"state": None, "done": False}

    def on_event(state, msg):
        holder["state"] = state
        if slow and msg is not None:
            time.sleep(0.35)

    def work():
        holder["state"] = Orchestrator(on_event).run(req, run_id)
        holder["done"] = True

    REG["runs"][run_id] = holder
    st.session_state["run_id"] = run_id
    threading.Thread(target=work, daemon=True).start()
    return run_id


# ---------------------------------------------------------------- 2. Ход работы
def page_live() -> None:
    ui.hero("⚙️ Ход работы", "Оркестратор маршрутизирует типизированные сообщения AgentMessage между шестью агентами")
    run_id = st.session_state.get("run_id")
    if not run_id or run_id not in REG["runs"]:
        st.info("Запустите обработку на странице «Запуск» — здесь появится живая схема агентов.")
        return

    @st.fragment(run_every=0.6)
    def live():
        h = REG["runs"][run_id]
        s = h["state"]
        if s is None:
            st.caption("Подготовка…")
            return
        done = {m.sender for m in s.messages if m.type in (MsgType.RESULT, MsgType.REVISE)}
        revise = any(m.type == MsgType.REVISE for m in s.messages)
        active = s.active_agent or ("" if h["done"] else "orchestrator")
        stage = len(done) / 6 if s.status != "done" else 1.0
        c = st.columns(4)
        for col, (l, v) in zip(c, [("Шагов", f"{s.steps} / {s.request.max_steps}"),
                                   ("Время", f"{time.time() - s.started_at if not h['done'] else s.elapsed:.1f} с"),
                                   ("Вызовов LLM", str(s.llm_calls)), ("Режим LLM", s.llm_mode_used or "…")]):
            col.markdown(ui.metric(l, v), unsafe_allow_html=True)
        st.progress(min(stage, 1.0), text=f"Статус: {s.status} · активен: {ui.AGENT_TITLES.get(active, '—')}")
        st.markdown(f'<div class="ra-card">{ui.agent_diagram(active, done, revise)}</div>', unsafe_allow_html=True)
        st.markdown("#### Лента сообщений")
        rows = "".join(ui.message_row(m) for m in reversed(s.messages[-40:]))
        st.markdown(f'<div class="ra-card" style="max-height:360px;overflow:auto">{rows or "—"}</div>',
                    unsafe_allow_html=True)
        if h["done"]:
            for e in s.errors[:1]:
                ui.error_box(e)
            if s.status == "done":
                st.success("Готово! Откройте страницу «Результаты».")
                if st.button("Открыть результаты →", type="primary"):
                    st.switch_page(PAGES["results"])
            raise_stop()

    live()


def raise_stop() -> None:
    """Прекращает автообновление фрагмента после завершения прогона."""
    st.session_state["live_finished"] = True


# ---------------------------------------------------------------- 3. Результаты
def linkify(text: str, refs: dict[int, str]) -> str:
    def rep(m):
        nums = re.findall(r"\d+", m.group(0))
        return "[" + ", ".join(f'<a href="{refs.get(int(n), "#")}" target="_blank" title="arXiv">{n}</a>' for n in nums) + "]"

    pat = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
    return "".join("<p>" + pat.sub(rep, html.escape(p)) + "</p>" for p in text.split("\n\n") if p.strip())


def pick_run(key: str) -> str | None:
    runs = ui.list_runs()
    if not runs:
        st.info("Пока нет завершённых прогонов. Запустите обработку на странице «Запуск».")
        return None
    cur = st.session_state.get("run_id")
    idx = runs.index(cur) if cur in runs else 0
    return st.selectbox("Прогон", runs, index=idx, key=key)


def page_results() -> None:
    ui.hero("📑 Результаты", "Исследовательская задача, отобранные статьи, темы, пробелы и черновик Related Work")
    run_id = pick_run("res_run")
    if not run_id:
        return
    s = ui.load_state(run_id)
    for e in s.errors:
        ui.error_box(e)
    if not s.task:
        return
    t = s.task
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        ui.card("Исследовательская задача", f"<p style='font-size:1.05rem'>{html.escape(t.problem)}</p>"
                f"<div class='ra-muted'>Ключевые понятия</div>{ui.chips(t.keywords)}"
                f"<div class='ra-muted' style='margin-top:6px'>Методы</div>{ui.chips(t.methods or ['—'], 'teal')}")
    with c2:
        m = st.columns(3)
        m[0].markdown(ui.metric("Отобрано статей", f"{len(s.selected)} / {s.request.n_papers}"), unsafe_allow_html=True)
        m[1].markdown(ui.metric("Время, с", f"{s.elapsed:.1f}"), unsafe_allow_html=True)
        m[2].markdown(ui.metric("Доработок", str(s.revisions)), unsafe_allow_html=True)
        st.caption(f"Фрагментов документа: {t.n_chunks} · символов: {t.n_chars} · режим LLM: {s.llm_mode_used} · "
                   f"шагов: {s.steps}")
        if s.stats:
            st.bar_chart(pd.Series(s.stats.get("by_year", {}), name="статей"), height=150, color="#4F46E5")

    tab1, tab2, tab3, tab4 = st.tabs(["✍️ Related Work", "📚 Найденные статьи", "🧩 Темы и пробелы", "✅ Проверка"])
    with tab1:
        refs = {p.ref: p.url for p in s.selected}
        st.markdown(f'<div class="ra-card ra-draft">{linkify(s.draft, refs)}</div>', unsafe_allow_html=True)
        st.markdown("**Список литературы**")
        for p in s.selected:
            st.markdown(f"[{p.ref}] {p.title} — *{', '.join(p.authors[:2])}{' и др.' if len(p.authors) > 2 else ''}*, "
                        f"{p.year} · [arXiv:{p.id}]({p.url})")
        e1, e2, e3 = st.columns(3)
        e1.download_button("⬇️ Markdown", to_markdown(s), f"related_work_{run_id}.md", use_container_width=True)
        e2.download_button("⬇️ DOCX", to_docx(s), f"related_work_{run_id}.docx", use_container_width=True)
        e3.download_button("⬇️ JSON", s.model_dump_json(indent=2), f"state_{run_id}.json", use_container_width=True)
    with tab2:
        df = pd.DataFrame([{"№": p.ref or "", "Заголовок": p.title, "Год": p.year, "Категория": p.primary_category,
                            "Скор": p.score, "BM25": p.bm25, "Косинус": p.dense,
                            "Решение": "✅ та же задача" if p.selected else ("— не рассм." if p.same_task is None else "❌ нет"),
                            "Обоснование": p.reason, "Пометки": ", ".join(p.flags), "arXiv": p.url} for p in s.candidates])
        st.dataframe(df, use_container_width=True, hide_index=True, height=460,
                     column_config={"arXiv": st.column_config.LinkColumn("arXiv", display_text="открыть"),
                                    "Скор": st.column_config.ProgressColumn("Скор", min_value=float(df["Скор"].min()),
                                                                            max_value=float(df["Скор"].max()), format="%.2f")})
    with tab3:
        cols = st.columns(max(len(s.themes), 1))
        byid = {p.id: p for p in s.selected}
        for col, th in zip(cols, s.themes):
            with col:
                items = "".join(f"<li>[{byid[i].ref}] {html.escape(byid[i].title)}</li>" for i in th.paper_ids if i in byid)
                ui.card(th.name, f"<div class='ra-muted'>{html.escape(th.description)}</div><ul>{items}</ul>")
        ui.card("Пробелы в исследованиях", "<ul>" + "".join(f"<li>{html.escape(g)}</li>" for g in s.gaps) + "</ul>")
    with tab4:
        for r in s.reviews:
            status = "✅ принята" if r.passed else "↩️ возвращена писателю"
            sc = " · ".join(f"{k}: {v}" for k, v in r.scores.items())
            viol = "".join(f"<li>{html.escape(v)}</li>" for v in r.rule_violations) or "<li>нарушений правил нет</li>"
            com = "".join(f"<li>{html.escape(c)}</li>" for c in r.comments)
            ui.card(f"Версия {r.version} — {status}", f"<div class='ra-muted'>{sc}</div><b>Правила:</b><ul>{viol}</ul>"
                    + (f"<b>Замечания LLM:</b><ul>{com}</ul>" if com else ""))
        if len(s.drafts) > 1:
            with st.expander("Сравнить версии черновика (до / после доработки)"):
                a, b = st.columns(2)
                a.markdown("**Версия 1**"); a.write(s.drafts[0])
                b.markdown(f"**Версия {len(s.drafts)}**"); b.write(s.drafts[-1])


# ---------------------------------------------------------------- 4. Эксперименты
def page_experiments() -> None:
    ui.hero("🧪 Эксперименты", "15 сценариев × 3 прогона, нагрузка по агентам и сравнение с базовой схемой «один агент»")
    R = config.RESULTS_DIR
    c1, c2 = st.columns([1, 3])
    with c1:
        quick = st.selectbox("Режим оценки", ["offline", "auto"], help="offline — без LLM, быстро и детерминированно")
        if st.button("▶️ Запустить оценку", type="primary", use_container_width=True):
            with st.spinner("Идёт оценка… это может занять несколько минут"):
                p = subprocess.run([sys.executable, str(ROOT / "evaluate.py"), "--llm", quick], cwd=ROOT,
                                   capture_output=True, text=True, encoding="utf-8")
            (st.success if p.returncode == 0 else st.error)(p.stdout[-600:] or p.stderr[-600:])
    summ = R / "summary.json"
    if not summ.exists():
        st.info("Результатов пока нет — нажмите «Запустить оценку» или выполните `python evaluate.py`.")
        return
    s = json.loads(summ.read_text(encoding="utf-8"))
    with c2:
        m = st.columns(4)
        m[0].markdown(ui.metric("Успешных прогонов", f"{s['success_rate']:.0%}"), unsafe_allow_html=True)
        m[1].markdown(ui.metric("Макс. нагрузка на агента", f"{s['max_agent_share']:.0%}"), unsafe_allow_html=True)
        m[2].markdown(ui.metric("Прогонов", str(s["n_runs"])), unsafe_allow_html=True)
        m[3].markdown(ui.metric("Режим LLM", s["llm_mode"]), unsafe_allow_html=True)
    st.markdown("#### Сценарии")
    st.dataframe(pd.read_csv(R / "scenarios_table.csv"), use_container_width=True, hide_index=True)
    g = st.columns(2)
    for i, (f, cap) in enumerate([("agent_load.png", "Нагрузка по агентам"), ("critic_scores.png", "Оценки проверяющего"),
                                  ("baseline_comparison.png", "Сравнение с одним агентом"),
                                  ("time_by_scenario.png", "Время по сценариям")]):
        if (R / f).exists():
            g[i % 2].image(str(R / f), caption=cap, use_container_width=True)
    if (R / "baseline_comparison.csv").exists():
        st.markdown("#### Многоагентная схема vs один агент")
        st.dataframe(pd.read_csv(R / "baseline_comparison.csv"), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------- 5. Журнал
def page_journal() -> None:
    ui.hero("🗂️ Журнал", "Аудиторский след: каждый вызов LLM и инструмента с временем, длительностью и статусом")
    run_id = pick_run("log_run")
    if not run_id:
        return
    rows = read_journal(config.RUNS_DIR / run_id / "journal.jsonl")
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("Журнал пуст.")
        return
    agents = sorted(df["agent"].unique())
    c1, c2 = st.columns(2)
    sel = c1.multiselect("Агент", agents, default=agents)
    kinds = c2.multiselect("Тип", sorted(df["kind"].unique()), default=sorted(df["kind"].unique()))
    view = df[df["agent"].isin(sel) & df["kind"].isin(kinds)]
    st.dataframe(view, use_container_width=True, hide_index=True, height=520)
    st.download_button("⬇️ Скачать JSONL", (config.RUNS_DIR / run_id / "journal.jsonl").read_bytes(),
                       f"journal_{run_id}.jsonl")


PAGES = {
    "launch": st.Page(page_launch, title="Запуск", icon="🚀", url_path="launch", default=True),
    "live": st.Page(page_live, title="Ход работы", icon="⚙️", url_path="live"),
    "results": st.Page(page_results, title="Результаты", icon="📑", url_path="results"),
    "exp": st.Page(page_experiments, title="Эксперименты", icon="🧪", url_path="experiments"),
    "log": st.Page(page_journal, title="Журнал", icon="🗂️", url_path="journal"),
}
with st.sidebar:
    st.markdown("### 📚 ResearchAssist")
    st.caption("Магистерская диссертация: интеллектуальный помощник для сопровождения НИР")
st.navigation(list(PAGES.values())).run()
