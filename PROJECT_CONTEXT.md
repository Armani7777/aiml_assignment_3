# ResearchAssist: контекст проекта (для работы в другом чате)

## Кто и что

- **Автор:** Арман Тұрсынбаев, группа CSE-2506M, магистратура.
- **Дисциплина:** Artificial Intelligence and Machine Learning, задание «Многоагентная ИИ-система» (ТЗ лежит в `…\artificial_intelligence_and_machine_learning\ТЗ Многоагентная ИИ-система.docx`).
- **Тема:** ResearchAssist — многоагентный помощник для поиска и анализа научной литературы. Это часть магистерской диссертации «Разработка интеллектуального помощника для сопровождения научно-исследовательской работы».
- **Что делает:** по статье или теме (TXT/DOCX/PDF/текст) выделяет задачу → ищет похожие работы в локальном корпусе arXiv → отбирает работы по той же задаче → группирует по подходам и находит пробелы → пишет черновик Related Work со ссылками [n] только на найденные статьи → проверяет ссылки и при ошибке возвращает текст на доработку.

## Где лежит

- **Папка проекта:** `C:\Users\kyzyl\work_projects\university_projects\artificial_intelligence_and_machine_learning\research_assist`
- **Репозиторий:** https://github.com/Armani7777/aiml_assignment_3 (ветка `main`, всё запушено).
- **Корпус (источник данных):** https://github.com/Armani7777/arxiv-similar-paper-retrieval — файлы `data/arxiv_2020_2024.jsonl` и `data/arxiv_may2026.jsonl` по 10 000 статей (поле id называется `arxiv_id`; в `categories` основная категория часто отсутствует — она в `primary_category`).
- **Машина:** Windows 11, Python 3.13, CPU без GPU (8 потоков), 7,8 ГБ ОЗУ. Ollama установлена (winget), сервис запущен, **моделей не скачано**. Word и PowerPoint установлены (через COM ими рендерятся DOCX/PPTX в PDF).

## Структура

```
research_assist/
  core/        config.py, models.py (AgentMessage, TaskState, RunRequest — pydantic), orchestrator.py,
               llm.py (Ollama format=json, T=0.2, seed=42, повторы, офлайн-эвристики), journal.py, errors.py
  agents/      agents.py — 6 агентов: analyst, retriever, selector, synthesizer, writer, critic
  tools/       documents.py (чтение, нарезка 2500 симв.), search.py (BM25 + эмбеддинги, z-норм., w=0.8,
               фильтр SQLite), rules.py (дубли/версии/похожие заголовки, проверки черновика)
  app/         streamlit_app.py (5 страниц), ui.py (тема CSS, SVG-схема агентов), export.py (MD/DOCX)
  data/        корпус *.jsonl + index/ (bm25.pkl, embeddings.npy, papers.sqlite, meta.json) — в .gitignore
  scenarios/   make_inputs.py + inputs/ (тестовые TXT/DOCX/PDF/CSV, demo_rag_hallucination.txt)
  tests/       test_tools_rules.py — 10 тестов pytest, все проходят
  results/     summary.json, runs.csv, scenarios_table.csv, agent_load.*, critic_scores.*, baseline_*.*, time_by_scenario.png
  runs/        state.json + journal.jsonl каждого прогона — в .gitignore
  report/      Отчёт_ResearchAssist.docx (14 стр.), build_report.py, Текст_защиты.md, Пример_для_демонстрации.md
  presentation/ ResearchAssist_презентация.pptx (12 + 2 запасных), build_deck.js, speech.json,
               Текст_по_слайдам.md, make_shots.py, img/
  evaluate.py, prepare_data.py, setup.bat/.sh, run.bat/.sh, Dockerfile, docker-compose.yml, README.md, LICENSE (MIT)
```

## Архитектура (кратко)

- Схема «оркестратор + общее состояние». Оркестратор только планирует (разбирает запрос: число статей, годы, категории, фокус) и маршрутизирует `AgentMessage {sender, receiver, type, payload}`; типы task/result/revise/error/done.
- У каждого агента ≤ 2 инструментов. Код считает скоры, дубли, статистику и проверку ссылок; LLM — задача, «та же задача?», названия тем, текст, оценки 1–5.
- Гибридный скор: `0,8·z(cos) + 0,2·z(BM25)` (вес 0,8 из предыдущей статьи автора).
- Проверяющий: правила (ссылки ∈ списку, 2–4 абзаца, длина 150–1600, нет дублей) + оценки support/accuracy/completeness; при нарушении или оценке ≤ 2 — доработка, не больше MAX_REVISIONS (=1).
- Надёжность: лимит 150 шагов и 1200 с, повторы, изоляция ошибки на одной статье, частичное состояние сохраняется. Журнал JSONL: время, агент, тип, длительность, токены, статус.

## Как запустить

```
cd research_assist
.venv\Scripts\python -m streamlit run app\streamlit_app.py      (или run.bat) → http://localhost:8501
.venv\Scripts\python evaluate.py --llm offline                   (оценка, ~1 мин)
.venv\Scripts\python -m pytest -q
.venv\Scripts\python report\build_report.py                      (пересобрать отчёт из results/)
```

Презентация пересобирается `node presentation/build_deck.js`. Скрипту нужны переменные `NODE_PATH` (папка с pptxgenjs) и `ICONS` (папка с PNG-иконками). Иконки и node_modules лежали во временной папке сессии и могут пропасть. Тогда: `npm install pptxgenjs@3.12.0 react-icons react react-dom`, а иконки нужно сгенерировать заново (FA6 SVG → PNG через Playwright + Edge).

## Результаты (то, что в отчёте и презентации)

- 15 сценариев × 3 прогона = 45. **Успешно 45/45 (100 %)** при требовании ≥ 90 %.
- **Максимальная нагрузка на агента — 36,7 % (отборщик)** при требовании ≤ 40 %. Аналитик 22,4 %, критик и синтезатор по 14,3 %, поисковик 7,5 %, писатель 4,8 %.
- Сценарии: S01–S07 содержательные (S07 «расплывчатый текст» отклоняется как не научный — проверка это допускает), S08–S12 ошибки входа/окружения, S13–S15 защиты.
- Сравнение с одним агентом (S01, S05, S06 × 3): обе схемы дают 0 выдуманных ссылок; один агент — 1 вызов LLM, многоагентная ≈ 10,7.

## Важные оговорки (честно)

1. **Вся оценка выполнена в офлайн-режиме:** LLM не скачана, решения модели заменены детерминированными эвристиками (`llm_mode=offline` в результатах). Поэтому сравнение с одним агентом предварительное. С моделью: `ollama pull qwen2.5:3b`, затем `python evaluate.py --llm auto --model qwen2.5:3b` (на CPU это часы).
2. **Эмбеддинги — хеш-эмбеддинги, не MiniLM.** Расчёт MiniLM (fastembed/ONNX) для 20 000 аннотаций на CPU шёл > 15 мин и был остановлен; индекс построен командой `prepare_data.py --hash`. `python prepare_data.py` без флага построит MiniLM. README описывает MiniLM как целевой вариант.
3. torch не установлен: он не ставится из-за длинных путей Windows. Вместо sentence-transformers используется fastembed.
4. Офлайн-отборщик путает «та же область» и «та же задача» (смотрит на совпадение слов), поэтому иногда попадают нерелевантные статьи. В ключевые понятия могут попадать служебные слова вроде «addresses».
5. В корпусе **нет статей про георадар (GPR)**. Демо-тема про радар находит ближайшие работы: FWI-инверсия, радарная съёмка, геофизика.
6. В отчёте (`report/img/ui_*.jpg`) старые скриншоты из узкой панели. Новые чёткие скриншоты лежат в `presentation/img/`.

## Демо-примеры

- Тема «Ввести тему», запрос пустой (георадар, проверено, 6 статей по радару/геофизике):
  `This research addresses subsurface imaging with radar using deep learning. The problem is to classify materials and estimate terrain and subsurface parameters from radar sounder and ground penetrating radar signals, which are noisy and hard to interpret manually. We propose a neural network that learns radar signal features and solves the geophysical inverse problem, using seismic-style full waveform inversion and denoising. We evaluate classification accuracy, inversion error and robustness to noise on simulated and real radar measurements.`
- Тема про галлюцинации в RAG + запрос `5 статей 2023-2026 cs.CL` — 5 статей, все по теме (файл `scenarios/inputs/demo_rag_hallucination.txt`, есть в списке примеров «★ Демо»).
- Ошибка: пример «Неподдерживаемый формат (CSV)».

## Стиль, который уже принят

- Язык всех материалов — русский. Палитра интерфейса и презентации: индиго `#4F46E5`, бирюза `#0EA5A4`, оранжевый `#F59E0B` (только «доработка»), фон `#F6F7FB`, тёмный `#1E1B4B`. Шрифт: Inter в интерфейсе, Segoe UI в презентации, Times New Roman в отчёте.
- Пользователь просил: делать быстро; в презентации **не показывать ограничения** и не ставить подпись в нижнем колонтитуле; текст для защиты — короткий и простой.
- Коммиты заканчиваются строкой `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
