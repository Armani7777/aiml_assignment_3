#!/usr/bin/env bash
# ResearchAssist: установка (venv, зависимости, модель Ollama, корпус и индексы)
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
[ -d .venv ] || $PY -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
if command -v ollama >/dev/null; then ollama pull qwen2.5:7b; ollama pull qwen2.5:3b; else
  echo "[!] Ollama не найдена: https://ollama.com (без неё работает офлайн-режим)"; fi
python scenarios/make_inputs.py
python prepare_data.py
echo "Готово. Запуск: ./run.sh"
