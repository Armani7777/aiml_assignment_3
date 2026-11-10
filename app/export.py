"""Экспорт результатов прогона в Markdown, DOCX и JSON."""
from __future__ import annotations

import io
import re

from core.models import TaskState


def to_markdown(st: TaskState) -> str:
    """Отчёт прогона в Markdown: задача, статьи, темы, пробелы, Related Work, проверка."""
    t = st.task
    lines = [f"# ResearchAssist — прогон {st.run_id}", "", "## Исследовательская задача", "", t.problem if t else "—", ""]
    if t:
        lines += [f"**Ключевые понятия:** {', '.join(t.keywords)}", "", f"**Методы:** {', '.join(t.methods) or '—'}", ""]
    lines += ["## Related Work (черновик)", "", st.draft, "", "## Список литературы", ""]
    for p in st.selected:
        lines.append(f"[{p.ref}] {', '.join(p.authors[:3])}{' et al.' if len(p.authors) > 3 else ''}. "
                     f"{p.title}. arXiv:{p.id}, {p.year}. {p.url}")
    lines += ["", "## Темы и пробелы", ""]
    lines += [f"- **{th.name}** — {th.description}" for th in st.themes]
    lines += [""] + [f"- Пробел: {g}" for g in st.gaps]
    lines += ["", "## Отчёт проверяющего", ""]
    for r in st.reviews:
        lines.append(f"- Версия {r.version}: {'принята' if r.passed else 'возвращена на доработку'}; "
                     f"оценки {r.scores}; нарушения: {r.rule_violations or 'нет'}")
    return "\n".join(lines)


def to_docx(st: TaskState) -> bytes:
    """Тот же отчёт в DOCX."""
    import docx

    d = docx.Document()
    for line in to_markdown(st).splitlines():
        if line.startswith("# "):
            d.add_heading(line[2:], 0)
        elif line.startswith("## "):
            d.add_heading(line[3:], 1)
        elif line.startswith("- "):
            d.add_paragraph(re.sub(r"\*\*", "", line[2:]), style="List Bullet")
        elif line.strip():
            d.add_paragraph(re.sub(r"\*\*", "", line))
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
