#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
if command -v ollama >/dev/null && ! curl -s localhost:11434/api/tags >/dev/null; then (ollama serve >/dev/null 2>&1 &); fi
python -m streamlit run app/streamlit_app.py --server.port 8501 --server.headless false
