"""Общие элементы интерфейса: тема (CSS), схема агентов (SVG), карточки, реестр прогонов."""
from __future__ import annotations

import html
import threading

import streamlit as st

from core import config
from core.models import AgentMessage, TaskState

AGENT_TITLES = {
    "orchestrator": "Оркестратор", "analyst": "Аналитик документа", "retriever": "Поисковик",
    "selector": "Отборщик", "synthesizer": "Синтезатор", "writer": "Писатель", "critic": "Проверяющий",
    "user": "Пользователь",
}
AGENT_ICONS = {"orchestrator": "🧭", "analyst": "📄", "retriever": "🔎", "selector": "⚖️",
               "synthesizer": "🧩", "writer": "✍️", "critic": "✅", "user": "👤"}
STEP_ORDER = ["analyst", "retriever", "selector", "synthesizer", "writer", "critic"]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono&display=swap');
html, body, [class*="css"], .stMarkdown, .stButton button, input, textarea, select { font-family: 'Inter', sans-serif !important; }
code, pre { font-family: 'IBM Plex Mono', monospace !important; }
.block-container { padding-top: 2rem; max-width: 1200px; }
h1, h2, h3 { color: #1E2235; letter-spacing: -0.01em; }
h1 { font-weight: 700; }
.ra-hero { background: linear-gradient(120deg, #4F46E5 0%, #6366F1 55%, #0EA5A4 100%); color: #fff;
  border-radius: 18px; padding: 22px 28px; margin-bottom: 18px; box-shadow: 0 10px 30px rgba(79,70,229,.18); }
.ra-hero h1 { color:#fff; margin:0; font-size: 1.8rem; }
.ra-hero p { margin: 6px 0 0; opacity: .92; }
.ra-card { background:#fff; border:1px solid #E6E8F0; border-radius:14px; padding:16px 18px; margin-bottom:12px;
  box-shadow: 0 1px 2px rgba(16,24,40,.04); }
.ra-card h4 { margin:0 0 6px; font-size:.95rem; color:#4F46E5; text-transform:uppercase; letter-spacing:.04em; }
.ra-muted { color:#6B7280; font-size:.9rem; }
.ra-chip { display:inline-block; background:#EEF2FF; color:#3730A3; border-radius:999px; padding:2px 10px;
  margin:2px 4px 2px 0; font-size:.82rem; }
.ra-chip.teal { background:#E6FFFA; color:#0F766E; }
.ra-chip.red { background:#FEF2F2; color:#B91C1C; }
.ra-msg { display:flex; gap:10px; align-items:flex-start; padding:8px 10px; border-bottom:1px solid #F0F1F6; font-size:.9rem; }
.ra-msg .who { white-space:nowrap; font-weight:600; color:#1E2235; min-width: 260px; }
.ra-msg .type { font-family:'IBM Plex Mono'; font-size:.75rem; padding:1px 8px; border-radius:6px; background:#F3F4F6; color:#374151; }
.ra-msg .type.revise { background:#FEF3C7; color:#92400E; } .ra-msg .type.done { background:#DCFCE7; color:#166534; }
.ra-msg .type.result { background:#E0E7FF; color:#3730A3; }
.ra-draft p { line-height:1.65; text-align: justify; }
.ra-draft a { color:#4F46E5; font-weight:600; text-decoration:none; }
.ra-metric { background:#fff; border:1px solid #E6E8F0; border-radius:14px; padding:12px 16px; }
.ra-metric .v { font-size:1.35rem; font-weight:700; color:#1E2235; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; } .ra-metric .l { color:#6B7280; font-size:.8rem; }
.ra-err { background:#FEF2F2; border:1px solid #FECACA; border-radius:14px; padding:14px 18px; color:#7F1D1D; }
.ra-err code { background:#FFE4E6; }
[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E6E8F0; }
[data-stale="true"], .stale-element { opacity: 1 !important; transition: none !important; }
.stAppDeployButton, [data-testid="stStatusWidget"], [data-testid="stMainMenu"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }
.stButton>button[kind="primary"] { border-radius: 10px; font-weight:600; padding: .55rem 1.2rem; }
</style>
"""


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="ra-hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)


def card(title: str, body_html: str) -> None:
    st.markdown(f'<div class="ra-card"><h4>{title}</h4>{body_html}</div>', unsafe_allow_html=True)


def metric(label: str, value: str) -> str:
    return f'<div class="ra-metric"><div class="v">{value}</div><div class="l">{label}</div></div>'


def chips(items: list[str], cls: str = "") -> str:
    return "".join(f'<span class="ra-chip {cls}">{html.escape(i)}</span>' for i in items)


def agent_diagram(active: str, done: set[str], revise: bool = False) -> str:
    """SVG-схема: оркестратор в центре, шесть агентов по кругу, подсветка активного."""
    import math

    W, H, cx, cy, R = 760, 330, 380, 165, 128
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" xmlns="http://www.w3.org/2000/svg">']
    pos = {}
    for i, a in enumerate(STEP_ORDER):
        ang = -math.pi / 2 + i * 2 * math.pi / 6
        pos[a] = (cx + R * 2.15 * math.cos(ang) * 0.95, cy + R * math.sin(ang))
    for a, (x, y) in pos.items():
        col = "#4F46E5" if a == active else ("#0EA5A4" if a in done else "#CBD2E1")
        w = 3 if a == active else 1.5
        dash = ' stroke-dasharray="6 4"' if a == active else ""
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.0f}" y2="{y:.0f}" stroke="{col}" stroke-width="{w}"{dash}/>')
    if revise:
        (x1, y1), (x2, y2) = pos["critic"], pos["writer"]
        parts.append(f'<path d="M{x1:.0f},{y1 - 22:.0f} Q{(x1 + x2) / 2:.0f},{min(y1, y2) - 70:.0f} {x2:.0f},{y2 - 22:.0f}" '
                     f'fill="none" stroke="#F59E0B" stroke-width="2" stroke-dasharray="5 4"/>')

    def node(x, y, name, is_active, is_done, center=False):
        fill = "#4F46E5" if is_active else ("#ECFDF5" if is_done else "#FFFFFF")
        stroke = "#4F46E5" if is_active else ("#0EA5A4" if is_done else "#D5DAE6")
        tc = "#FFFFFF" if is_active else "#1E2235"
        w, h = (170, 54) if center else (158, 46)
        glow = ' filter="url(#glow)"' if is_active else ""
        return (f'<g{glow}><rect x="{x - w / 2:.0f}" y="{y - h / 2:.0f}" width="{w}" height="{h}" rx="12" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="2"/><text x="{x:.0f}" y="{y + 5:.0f}" text-anchor="middle" '
                f'font-family="Inter, sans-serif" font-size="{14 if center else 13}" font-weight="600" fill="{tc}">'
                f'{AGENT_ICONS[name]} {AGENT_TITLES[name]}{" ✓" if is_done and not is_active else ""}</text></g>')

    parts.insert(1, '<defs><filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="4" '
                    'stdDeviation="6" flood-color="#4F46E5" flood-opacity="0.35"/></filter></defs>')
    parts.append(node(cx, cy, "orchestrator", active == "orchestrator", False, True))
    for a, (x, y) in pos.items():
        parts.append(node(x, y, a, a == active, a in done))
    parts.append("</svg>")
    return "".join(parts)


def message_row(m: AgentMessage) -> str:
    return (f'<div class="ra-msg"><span class="who">{AGENT_ICONS.get(m.sender, "")} {AGENT_TITLES.get(m.sender, m.sender)}'
            f' → {AGENT_ICONS.get(m.receiver, "")} {AGENT_TITLES.get(m.receiver, m.receiver)}</span>'
            f'<span class="type {m.type.value}">{m.type.value}</span><span>{html.escape(m.summary)}</span></div>')


def error_box(err: dict) -> None:
    hint = html.escape(err.get("hint", ""))
    hint = hint.replace("`ollama serve`", "<code>ollama serve</code>")
    st.markdown(f'<div class="ra-err"><b>⚠️ {html.escape(err["message"])}</b><br>'
                f'<span>💡 Как исправить: {hint}</span></div>', unsafe_allow_html=True)


@st.cache_resource
def run_registry() -> dict:
    """Общий реестр живых прогонов (между перерисовками Streamlit)."""
    return {"lock": threading.Lock(), "runs": {}}


def list_runs() -> list[str]:
    if not config.RUNS_DIR.exists():
        return []
    files = sorted(config.RUNS_DIR.glob("*/state.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.parent.name for p in files]  # самые свежие прогоны — первыми


def load_state(run_id: str) -> TaskState | None:
    p = config.RUNS_DIR / run_id / "state.json"
    return TaskState.load(p) if p.exists() else None
