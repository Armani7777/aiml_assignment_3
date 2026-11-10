@echo off
chcp 65001 >nul
REM ResearchAssist: установка (venv, зависимости, модель Ollama, корпус и индексы)
cd /d %~dp0
if not exist .venv ( py -3.13 -m venv .venv || python -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || goto :error
where ollama >nul 2>nul && ( ollama pull qwen2.5:7b & ollama pull qwen2.5:3b ) || echo [!] Ollama не найдена: установите с https://ollama.com (без неё работает офлайн-режим)
python scenarios\make_inputs.py
python prepare_data.py || goto :error
echo.
echo Готово. Запуск: run.bat
exit /b 0
:error
echo Ошибка установки. См. сообщения выше.
exit /b 1
