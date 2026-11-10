"""Генерирует тестовые входные документы в `scenarios/inputs/` (TXT, DOCX, PDF, CSV)."""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).parent / "inputs"

RETRIEVAL = """Hybrid Retrieval of Similar Scientific Papers

Abstract. Finding papers that address the same research problem is a core step of literature review.
We study the task of similar scientific paper retrieval on arXiv abstracts. We propose a hybrid retrieval
method that combines sparse lexical matching with BM25 and dense semantic embeddings from a sentence
transformer (all-MiniLM-L6-v2). Scores of both retrievers are z-normalized and fused with a weight on the
dense component. We evaluate the approach on a corpus of 20,000 arXiv papers using recall@k and nDCG,
and compare it with pure BM25, pure dense retrieval and reciprocal rank fusion. Results show that the
hybrid method improves ranking quality for queries describing a research problem. We also discuss
citation recommendation, query expansion and the use of large language models for re-ranking candidates.
"""

RAG = """Retrieval-Augmented Generation for Question Answering

We address the problem of hallucinations in large language models for open-domain question answering.
Our approach augments a language model with a retriever that selects relevant passages from a document
collection, and a generator that conditions on retrieved evidence. We investigate dense passage retrieval,
re-ranking with cross-encoders and faithfulness evaluation of generated answers. Experiments on standard
question answering benchmarks measure exact match, answer faithfulness and attribution of claims to sources.
The study aims to reduce unsupported statements and improve factual grounding of generated text.
"""

GNN = """Graph Neural Networks for Molecular Property Prediction

The research task is to predict molecular properties from molecular graphs. We propose a message passing
graph neural network with attention over chemical bonds and self-supervised pretraining on unlabeled
molecules. The model is evaluated on molecular benchmark datasets with classification and regression
targets, compared with fingerprint-based baselines and transformer models over SMILES strings. We analyse
generalization to out-of-distribution scaffolds and the effect of contrastive pretraining objectives.
"""

AGENTS = """Multi-agent large language model systems for software engineering

This work studies how multiple LLM agents with distinct roles can cooperate to solve programming tasks.
We propose an orchestrator that plans the task and routes messages between planner, coder, tester and
reviewer agents with tool use. We evaluate code generation benchmarks, measure pass rates, cost in tokens,
and the effect of self-reflection and critic feedback loops on correctness of generated programs.
"""

VAGUE = """Some thoughts about technology and the future

Technology changes many things in our life and it is interesting to look at how computers and data could
help people in different areas. Maybe intelligent systems will be used more and more, and this raises many
questions about learning, models and the role of data. It would be nice to understand these things better
and to see what other people have written about it, especially about learning from data and networks.
"""

NOT_SCI = """Рецепт яблочного пирога

Возьмите три яблока, два яйца, стакан сахара и стакан муки. Яблоки очистите и нарежьте дольками.
Яйца взбейте с сахаром до пышной пены, добавьте муку и аккуратно перемешайте. Выложите яблоки в форму,
залейте тестом и выпекайте в духовке при температуре 180 градусов около сорока минут. Подавайте тёплым
с чаем. Пирог хорошо хранится два дня, его можно посыпать сахарной пудрой и корицей по вкусу.
"""


DEMO = """Reducing Hallucinations in Retrieval-Augmented Generation

We study hallucination in retrieval-augmented generation for question answering with large language models. The research problem is that generated answers often contain claims that are not supported by the retrieved documents. We propose a method that retrieves passages with dense retrieval, re-ranks them, and verifies each generated claim against the evidence before producing the final answer. We evaluate faithfulness, attribution accuracy and answer quality on question answering benchmarks and compare with standard RAG baselines.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "retrieval_paper.txt").write_text(RETRIEVAL, encoding="utf-8")
    (OUT / "multiagent_topic.txt").write_text(AGENTS, encoding="utf-8")
    (OUT / "vague_text.txt").write_text(VAGUE, encoding="utf-8")
    (OUT / "not_scientific.txt").write_text(NOT_SCI, encoding="utf-8")
    (OUT / "too_short.txt").write_text("Нейросети и поиск статей.", encoding="utf-8")
    (OUT / "demo_rag_hallucination.txt").write_text(DEMO, encoding="utf-8")
    (OUT / "table.csv").write_text("id,title\n1,foo\n2,bar\n", encoding="utf-8")

    import docx

    d = docx.Document()
    for par in RAG.split("\n\n"):
        d.add_paragraph(par.replace("\n", " "))
    d.save(OUT / "rag_paper.docx")

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(OUT / "gnn_paper.pdf"), pagesize=A4)
    y = 800
    for line in GNN.splitlines():
        c.drawString(50, y, line)
        y -= 16
    c.save()
    print("Входные документы созданы в", OUT)


if __name__ == "__main__":
    main()
