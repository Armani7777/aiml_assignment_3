@echo off
chcp 65001 >nul
cd /d %~dp0
call .venv\Scripts\activate.bat
where ollama >nul 2>nul && ( start "" /min ollama serve )
python -m streamlit run app\streamlit_app.py --server.port 8501 --server.headless false
