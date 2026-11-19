/**
 * Презентация ResearchAssist в академическом стиле (PPTX, 16:9).
 * Запуск: NODE_PATH=<папка node_modules с pptxgenjs> node presentation/build_deck.js
 * Цифры: results/ (summary.json, agent_load.csv, scenarios_table.csv) и presentation/corpus_stats.json.
 * Текст выступления (заметки докладчика): presentation/speech.json.
 */
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const IMG = path.join(__dirname, "img");
const OUT = path.join(__dirname, "ResearchAssist_презентация.pptx");
const read = (...p) => fs.readFileSync(path.join(...p), "utf8");

// ---------- данные ----------
const SPEECH = JSON.parse(read(__dirname, "speech.json"));
const summary = JSON.parse(read(ROOT, "results", "summary.json"));
const corpus = JSON.parse(read(__dirname, "corpus_stats.json"));
const csv = (f) => read(ROOT, "results", f).trim().split(/\r?\n/).slice(1)
  .map((l) => (l.match(/("[^"]*"|[^,]*)(,|$)/g) || []).map((x) => x.replace(/,$/, "").replace(/^"|"$/g, "")));
const AGENT_RU = { analyst: "Аналитик", retriever: "Поисковик", selector: "Отборщик", synthesizer: "Синтезатор",
  writer: "Писатель", critic: "Проверяющий" };
const load = csv("agent_load.csv").map(([k, v]) => ({ name: AGENT_RU[k], v: Math.round(parseFloat(v) * 1000) / 10 }));
const scen = csv("scenarios_table.csv");
const num = (x, d = 1) => x.toFixed(d).replace(".", ",");
const nRuns = summary.n_runs, okRuns = Math.round(summary.success_rate * nRuns);
const maxLoad = num(summary.max_agent_share * 100);
const fmtN = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

// ---------- стиль ----------
const C = { navy: "1F3A5F", ink: "222831", muted: "5F6B7A", accent: "2E7D78", light: "F2F4F7", line: "D9DEE5",
  white: "FFFFFF", warm: "B5651D", red: "B23B3B" };
const HEAD = "Cambria", BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 × 7.5 дюйма
pres.author = "Арман Тұрсынбаев";
pres.title = "ResearchAssist — многоагентная система для поиска и анализа научной литературы";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.white },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.38, w: 12.1, h: 0.8,
    fontFace: HEAD, fontSize: 28, bold: true, color: C.navy, align: "left", valign: "middle", margin: 0 }, text: "" } }],
  slideNumber: { x: 12.25, y: 7.0, w: 0.5, h: 0.3, fontFace: BODY, fontSize: 10, color: C.muted, align: "right" },
});

let fig = 0, tab = 0;
const T = (s, text, o) => s.addText(text, { fontFace: BODY, color: C.ink, margin: 0, isTextBox: true, valign: "top", ...o });
const slide = (title, notesIdx) => {
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText(title, { placeholder: "title" });
  s.addNotes(SPEECH[notesIdx]);
  return s;
};
const figCap = (s, text, x, y, w) => { fig += 1; T(s, `Рис. ${fig} — ${text}`, { x, y, w, h: 0.32, fontSize: 11, italic: true, color: C.muted }); };
const tabCap = (s, text, x, y, w) => { tab += 1; T(s, `Табл. ${tab} — ${text}`, { x, y, w, h: 0.32, fontSize: 11, italic: true, color: C.muted }); };
const bullets = (s, items, o) => T(s, items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 },
  breakLine: i < items.length - 1 } })), { fontSize: 16, paraSpaceAfter: 9, ...o });
const H = (t) => ({ text: t, options: { bold: true, color: C.white, fill: { color: C.navy } } });
const table = (s, header, rows, o) => s.addTable([header.map(H), ...rows.map((r, ri) => r.map((c) => (
  typeof c === "object" ? { ...c, options: { fill: { color: ri % 2 ? C.light : C.white }, ...c.options } }
    : { text: String(c), options: { fill: { color: ri % 2 ? C.light : C.white } } })))], {
  fontFace: BODY, fontSize: 13, color: C.ink, valign: "middle", border: { type: "solid", color: C.line, pt: 0.75 },
  margin: [0.04, 0.1, 0.04, 0.1], ...o });
const chartBase = (o) => ({
  catAxisLabelFontFace: BODY, catAxisLabelFontSize: 11, catAxisLabelColor: C.muted, valAxisLabelFontFace: BODY,
  valAxisLabelFontSize: 10, valAxisLabelColor: C.muted, valGridLine: { color: "E6E9EE", size: 0.75 },
  catGridLine: { style: "none" }, showValue: true, dataLabelFontFace: BODY, dataLabelFontSize: 11,
  dataLabelColor: C.ink, showLegend: false, showTitle: false, ...o });

// =====================================================================================
// Титул
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  s.addShape(pres.shapes.RECTANGLE, { x: 9.1, y: 0, w: 4.233, h: 7.5, fill: { color: C.navy }, line: { color: C.navy } });
  T(s, "Магистерская диссертация\nArtificial Intelligence and Machine Learning",
    { x: 0.8, y: 1.0, w: 7.6, h: 0.8, fontSize: 14, color: C.muted });
  T(s, "ResearchAssist", { x: 0.8, y: 2.0, w: 7.8, h: 1.0, fontFace: HEAD, fontSize: 48, bold: true, color: C.navy });
  T(s, "Многоагентная система для поиска\nи анализа научной литературы", { x: 0.8, y: 3.05, w: 7.8, h: 1.2,
    fontFace: HEAD, fontSize: 26, color: C.ink });
  T(s, "Часть диссертации «Разработка интеллектуального помощника для сопровождения научно-исследовательской работы»",
    { x: 0.8, y: 4.55, w: 7.4, h: 0.8, fontSize: 15, italic: true, color: C.muted });
  T(s, [{ text: "Арман Тұрсынбаев", options: { bold: true, fontSize: 20, breakLine: true } },
    { text: "группа CSE-2506M", options: { fontSize: 16, breakLine: true } },
    { text: "2026", options: { fontSize: 16 } }], { x: 9.6, y: 4.9, w: 3.3, h: 1.5, color: C.white });
  s.addNotes(SPEECH[0]);
}

// 1. Постановка проблемы и актуальность
{
  const s = slide("Постановка проблемы и актуальность", 1);
  bullets(s, [
    "Обзор литературы — обязательная и трудоёмкая часть НИР: нужно найти работы, решающие ту же задачу, а не просто близкие по теме",
    "Объём публикаций велик: даже выборка arXiv за один месяц (май 2026) содержит 10 000 статей [15]",
    "LLM без опоры на источники выдумывают ссылки: 55 % ссылок GPT-3.5 и 18 % ссылок GPT-4 не существуют [12]",
    "Нужен помощник, который работает только с реальными статьями и проверяет каждую ссылку",
  ], { x: 0.6, y: 1.55, w: 6.5, h: 4.9, fontSize: 18, paraSpaceAfter: 14 });
  s.addChart(pres.charts.BAR, [{ name: "Несуществующие ссылки, %", labels: ["GPT-3.5", "GPT-4"], values: [55, 18] }],
    chartBase({ x: 7.7, y: 1.6, w: 5.0, h: 4.4, chartColors: [C.navy], barGapWidthPct: 70, valAxisMaxVal: 60,
      valAxisMinVal: 0, valAxisMajorUnit: 20, dataLabelFormatCode: '0"%"', catAxisLabelFontSize: 13 }));
  figCap(s, "Доля несуществующих ссылок в текстах ChatGPT [12]", 7.7, 6.1, 5.0);
}

// 2. Цель, задачи, вопросы
{
  const s = slide("Цель и задачи работы", 2);
  T(s, [{ text: "Цель: ", options: { bold: true, color: C.navy } },
    { text: "по статье или теме пользователя найти работы, решающие ту же задачу, и сформировать проверенный черновик раздела Related Work" }],
    { x: 0.6, y: 1.45, w: 12.1, h: 0.85, fontSize: 18 });
  T(s, "Задачи", { x: 0.6, y: 2.55, w: 6, h: 0.4, fontFace: HEAD, fontSize: 18, bold: true, color: C.navy });
  T(s, ["Подготовить корпус arXiv и поисковые индексы", "Реализовать гибридный поиск и отбор релевантных работ",
    "Построить многоагентную систему с проверкой ссылок", "Разработать веб-интерфейс", "Оценить систему на 15 сценариях"]
    .map((t, i, a) => ({ text: t, options: { bullet: { type: "number", indent: 18 }, breakLine: i < a.length - 1 } })),
    { x: 0.6, y: 3.05, w: 5.7, h: 3.3, fontSize: 16, paraSpaceAfter: 9 });
  T(s, "Исследовательские вопросы", { x: 6.9, y: 2.55, w: 5.8, h: 0.4, fontFace: HEAD, fontSize: 18, bold: true, color: C.navy });
  table(s, ["", "Вопрос", "Критерий"], [
    [{ text: "RQ1", options: { bold: true } }, "Стабильна ли система на типовых и нештатных сценариях?", "≥ 90 % успешных прогонов"],
    [{ text: "RQ2", options: { bold: true } }, "Сбалансирована ли нагрузка между агентами?", "≤ 40 % вызовов на агента"],
    [{ text: "RQ3", options: { bold: true } }, "Что даёт разделение на агентов?", "сравнение с одним агентом"],
  ], { x: 6.9, y: 3.05, w: 5.8, colW: [0.65, 3.15, 2.0], rowH: [0.4, 0.75, 0.75, 0.75], fontSize: 13.5 });
}

// 3. Обзор литературы
{
  const s = slide("Краткий обзор литературы", 3);
  table(s, ["Направление", "Работы", "Что используется в проекте"], [
    [{ text: "Лексический и плотный поиск", options: { bold: true } }, "BM25 [1]; Sentence-BERT [2]; MiniLM [3]; DPR [4]",
      "BM25 и эмбеддинги all-MiniLM-L6-v2 как две части поиска"],
    [{ text: "Объединение ранжирований", options: { bold: true } }, "Reciprocal Rank Fusion [5]",
      "взвешенная сумма z-нормированных скоров, w = 0,8"],
    [{ text: "LLM-агенты и многоагентные системы", options: { bold: true } }, "ReAct [7]; AutoGen [8]; MetaGPT [9]",
      "разделение ролей, инструменты, оркестратор с типизированными сообщениями"],
    [{ text: "Генерация обзоров и проверка", options: { bold: true } }, "RAG [6]; LitLLM [11]; Self-Refine [10]; Walters & Wilder [12]",
      "текст только по найденным аннотациям, проверка ссылок кодом и одна доработка"],
  ], { x: 0.6, y: 1.5, w: 12.1, colW: [3.3, 4.0, 4.8], rowH: [0.45, 0.9, 0.9, 0.9, 0.9], fontSize: 14 });
  tabCap(s, "Направления исследований и их использование в проекте", 0.6, 5.65, 12.1);
  T(s, [{ text: "Отличие работы: ", options: { bold: true, color: C.navy } },
    { text: "гибридный поиск, отбор по задаче и проверка каждой ссылки правилами объединены в одной локальной системе" }],
    { x: 0.6, y: 6.15, w: 12.1, h: 0.6, fontSize: 16 });
}

// 4. Набор данных
{
  const s = slide("Описание набора данных", 4);
  table(s, ["Характеристика", "Значение"], [
    ["Источник", "корпус arXiv, репозиторий автора [15]"],
    ["Объём", "20 000 статей (2 файла JSONL)"],
    ["Период", "2020–2024 и май 2026"],
    ["Поля", "заголовок, аннотация, авторы, категории, дата"],
    ["Категорий arXiv", String(corpus.n_cats)],
    ["Средняя длина аннотации", `${fmtN(corpus.avg_abs)} символов`],
    ["Индексы", "BM25, эмбеддинги (.npy), SQLite"],
    ["Тестовые документы", "8: TXT, DOCX, PDF, CSV"],
  ], { x: 0.6, y: 1.5, w: 5.6, colW: [2.3, 3.3], rowH: 0.5, fontSize: 13.5 });
  tabCap(s, "Характеристики набора данных", 0.6, 6.15, 5.6);
  const yrs = corpus.years.map(([y]) => (y === 2026 ? "2026 (май)" : String(y)));
  s.addChart(pres.charts.BAR, [{ name: "Статей", labels: yrs, values: corpus.years.map(([, n]) => n) }],
    chartBase({ x: 6.7, y: 1.45, w: 6.0, h: 2.15, chartColors: [C.navy], barGapWidthPct: 45, valAxisHidden: true,
      valGridLine: { style: "none" }, dataLabelFormatCode: "#,##0" }));
  figCap(s, "Распределение статей по годам", 6.7, 3.6, 6.0);
  const cats = corpus.cats.slice().reverse();
  s.addChart(pres.charts.BAR, [{ name: "Статей", labels: cats.map(([c]) => c), values: cats.map(([, n]) => n) }],
    chartBase({ x: 6.7, y: 4.0, w: 6.0, h: 2.15, barDir: "bar", chartColors: [C.accent], barGapWidthPct: 35,
      valAxisHidden: true, valGridLine: { style: "none" }, dataLabelFormatCode: "#,##0" }));
  figCap(s, "Шесть самых частых основных категорий", 6.7, 6.15, 6.0);
}

// 5. Методы
{
  const s = slide("Методы машинного обучения", 5);
  table(s, ["Этап", "Метод", "Реализация"], [
    [{ text: "Представление текста", options: { bold: true } }, "BM25 [1]; эмбеддинги all-MiniLM-L6-v2 [2, 3]", "токенизация, косинусная близость"],
    [{ text: "Ранжирование", options: { bold: true } }, "гибридное объединение скоров", "z-нормировка, вес 0,8 на плотную часть"],
    [{ text: "Отбор", options: { bold: true } }, "zero-shot классификация LLM qwen2.5 [13]", "«та же задача / нет» + правила дублей и версий"],
    [{ text: "Группировка", options: { bold: true } }, "k-средних [14]", "по эмбеддингам аннотаций, seed = 42"],
    [{ text: "Генерация и проверка", options: { bold: true } }, "LLM-писатель и критик [10]", "проверка ссылок правилами, оценки 1–5"],
  ], { x: 0.6, y: 1.5, w: 8.2, colW: [2.3, 3.2, 2.7], rowH: [0.45, 0.82, 0.82, 0.82, 0.82, 0.82], fontSize: 13.5 });
  tabCap(s, "Методы на этапах работы системы", 0.6, 6.15, 8.2);
  s.addShape(pres.shapes.RECTANGLE, { x: 9.2, y: 1.5, w: 3.5, h: 4.55, fill: { color: C.light }, line: { color: C.light } });
  T(s, "Гибридный скор", { x: 9.45, y: 1.7, w: 3.0, h: 0.4, fontFace: HEAD, fontSize: 17, bold: true, color: C.navy });
  T(s, "s = 0,8 · z(cos)\n   + 0,2 · z(BM25)", { x: 9.45, y: 2.3, w: 3.1, h: 1.1, fontFace: "Cambria Math", fontSize: 20, color: C.ink });
  T(s, "z — нормировка скора по всем статьям корпуса. Вес 0,8 подобран в предыдущей работе автора по поиску похожих статей arXiv.",
    { x: 9.45, y: 3.6, w: 3.05, h: 2.2, fontSize: 14, color: C.muted });
}

// 6. Архитектура
{
  const s = slide("Архитектура системы", 6);
  const bw = 3.45, bh = 0.95, xs = [0.75, 4.94, 9.13], yT = 1.5, yB = 4.85, cx = 6.665, cy = 3.65;
  const box = (x, y, t, d) => {
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: bw, h: bh, fill: { color: C.white }, line: { color: "9AA6B5", width: 1 } });
    T(s, [{ text: t, options: { bold: true, fontSize: 15, breakLine: true } }, { text: d, options: { fontSize: 12, color: C.muted } }],
      { x: x + 0.15, y, w: bw - 0.3, h: bh, valign: "middle" });
  };
  const line = (x1, y1, x2, y2, o = {}) => s.addShape(pres.shapes.LINE, { x: Math.min(x1, x2), y: Math.min(y1, y2),
    w: Math.max(Math.abs(x2 - x1), 0.001), h: Math.max(Math.abs(y2 - y1), 0.001), flipH: (x2 < x1) !== (y2 < y1),
    line: { color: "9AA6B5", width: 1, ...o } });
  xs.forEach((x) => { line(cx, cy, x + bw / 2, yT + bh); line(cx, cy, x + bw / 2, yB); });
  [["1. Аналитик документа", "чтение, нарезка, выделение задачи"], ["2. Поисковик", "гибридный поиск, фильтр SQLite"],
    ["3. Отборщик", "правила дублей + решение LLM"]].forEach(([t, d], i) => box(xs[i], yT, t, d));
  [["6. Проверяющий", "правила ссылок + оценки 1–5"], ["5. Писатель", "черновик со ссылками [n]"],
    ["4. Синтезатор", "k-средних, темы и пробелы"]].forEach(([t, d], i) => box(xs[i], yB, t, d));
  s.addShape(pres.shapes.RECTANGLE, { x: cx - 1.55, y: cy - 0.5, w: 3.1, h: 1.0, fill: { color: C.navy }, line: { color: C.navy } });
  T(s, [{ text: "Оркестратор", options: { bold: true, fontSize: 16, breakLine: true } },
    { text: "план запроса и маршрутизация", options: { fontSize: 12 } }],
    { x: cx - 1.55, y: cy - 0.5, w: 3.1, h: 1.0, color: C.white, align: "center", valign: "middle" });
  [[0.75, "TaskState (JSON)", "общее состояние"], [9.63, "journal.jsonl", "журнал всех вызовов"]].forEach(([x, t, d]) => {
    s.addShape(pres.shapes.RECTANGLE, { x, y: cy - 0.42, w: 2.95, h: 0.84, fill: { color: C.light }, line: { color: C.light } });
    T(s, [{ text: t, options: { bold: true, fontSize: 14, breakLine: true } }, { text: d, options: { fontSize: 12, color: C.muted } }],
      { x: x + 0.15, y: cy - 0.42, w: 2.7, h: 0.84, valign: "middle" });
    if (x < cx) line(x + 2.95, cy, cx - 1.55, cy, { dashType: "dash" }); else line(cx + 1.55, cy, x, cy, { dashType: "dash" });
  });
  s.addShape(pres.shapes.LINE, { x: xs[0] + bw + 0.05, y: yB + bh / 2, w: xs[1] - xs[0] - bw - 0.1, h: 0,
    line: { color: C.warm, width: 2, endArrowType: "triangle" } });
  T(s, "доработка ≤ 1", { x: xs[0] + bw - 0.55, y: yB + bh + 0.06, w: 1.7, h: 0.3, fontSize: 11.5, color: C.warm, align: "center" });
  figCap(s, "Схема «оркестратор + общее состояние»: агенты обмениваются только сообщениями AgentMessage", 0.6, 6.3, 12.1);
}

// 7. Реализация
{
  const s = slide("Реализация: веб-интерфейс", 7);
  const h = 4.0, w1 = h * 2000 / 1500, w2 = h * 1960 / 1200, gap = 0.4;
  const x1 = 0.6 + (12.1 - w1 - w2 - gap) / 2;
  s.addImage({ path: path.join(IMG, "live.png"), x: x1, y: 1.55, w: w1, h });
  s.addImage({ path: path.join(IMG, "draft.png"), x: x1 + w1 + gap, y: 1.55, w: w2, h });
  [[x1, w1], [x1 + w1 + gap, w2]].forEach(([x, w]) => s.addShape(pres.shapes.RECTANGLE, { x, y: 1.55, w, h,
    fill: { type: "none" }, line: { color: C.line, width: 0.75 } }));
  figCap(s, "Ход работы: активный агент подсвечен", x1, 5.65, w1);
  figCap(s, "Результат: черновик Related Work со ссылками [n]", x1 + w1 + gap, 5.65, w2);
  T(s, "Python 3.13, Streamlit, Ollama; запуск одной командой (run.bat), экспорт результата в Markdown, DOCX и JSON",
    { x: 0.6, y: 6.25, w: 12.1, h: 0.4, fontSize: 15, color: C.muted });
}

// 8. Методика эксперимента
{
  const s = slide("Методика эксперимента", 8);
  table(s, ["Группа", "Сценарии", "Что проверяется"], [
    [{ text: "Содержательные", options: { bold: true } }, "S01–S07 (7)", "типовой запуск, фильтры по годам и категории, другое число статей, DOCX, PDF, расплывчатый текст"],
    [{ text: "Ошибки входа и окружения", options: { bold: true } }, "S08–S12 (5)", "нет научной задачи, короткий файл, неверный формат, нет файла, Ollama выключена"],
    [{ text: "Защиты", options: { bold: true } }, "S13–S15 (3)", "лимит шагов, лимит времени, MAX_REVISIONS = 0"],
  ], { x: 0.6, y: 1.5, w: 12.1, colW: [3.0, 1.9, 7.2], rowH: [0.45, 0.8, 0.8, 0.6], fontSize: 14 });
  tabCap(s, "Сценарии оценки (каждый — 3 прогона, всего 45, seed = 42)", 0.6, 4.2, 12.1);
  T(s, "Критерии", { x: 0.6, y: 4.75, w: 5.6, h: 0.4, fontFace: HEAD, fontSize: 17, bold: true, color: C.navy });
  bullets(s, ["≥ 90 % успешных прогонов (автоматические проверки)", "≤ 40 % вызовов LLM и инструментов на агента"],
    { x: 0.6, y: 5.25, w: 5.7, h: 1.3, fontSize: 15 });
  T(s, "Базовая схема «один агент»", { x: 6.9, y: 4.75, w: 5.8, h: 0.4, fontFace: HEAD, fontSize: 17, bold: true, color: C.navy });
  T(s, "Та же модель, документ и кандидаты, один запрос без проверяющего. Метрики: выдуманные ссылки, подтверждённость утверждений, число статей, дубли, покрытие тем, время, вызовы LLM",
    { x: 6.9, y: 5.25, w: 5.8, h: 1.4, fontSize: 15 });
}

// 9. Результаты
{
  const s = slide("Экспериментальные результаты", 9);
  table(s, ["Показатель", "Требование", "Результат"], [
    ["Успешные прогоны", "≥ 90 %", { text: `100 % (${okRuns} из ${nRuns})`, options: { bold: true } }],
    ["Макс. нагрузка на агента", "≤ 40 %", { text: `${maxLoad} %`, options: { bold: true } }],
    ["Выдуманные ссылки", "—", { text: "0", options: { bold: true } }],
    ["Тесты pytest", "—", { text: "10 из 10", options: { bold: true } }],
  ], { x: 0.6, y: 1.5, w: 5.4, colW: [2.5, 1.3, 1.6], rowH: [0.45, 0.6, 0.6, 0.6, 0.6], fontSize: 14 });
  tabCap(s, "Итоги оценки", 0.6, 4.4, 5.4);
  const labels = load.map((d) => d.name);
  s.addChart([
    { type: pres.charts.BAR, data: [{ name: "Доля вызовов, %", labels, values: load.map((d) => d.v) }],
      options: { chartColors: [C.navy], barGapWidthPct: 55 } },
    { type: pres.charts.LINE, data: [{ name: "Порог 40 %", labels, values: labels.map(() => 40) }],
      options: { chartColors: [C.red], lineSize: 1.5, lineDash: "dash", lineDataSymbol: "none", showValue: false } },
  ], chartBase({ x: 6.4, y: 1.45, w: 6.3, h: 4.6, valAxisMaxVal: 45, valAxisMinVal: 0, valAxisMajorUnit: 10,
    dataLabelFormatCode: "0.0", showLegend: true, legendPos: "b", legendFontFace: BODY, legendFontSize: 11,
    legendColor: C.muted }));
  figCap(s, "Доля вызовов LLM и инструментов по агентам, % (45 прогонов)", 6.4, 6.1, 6.3);
}

// 10. Анализ
{
  const s = slide("Анализ результатов", 10);
  const ids = scen.map((r) => r[0]), steps = scen.map((r) => parseFloat(r[8]));
  s.addChart(pres.charts.BAR, [{ name: "Шагов", labels: ids, values: steps }],
    chartBase({ x: 0.6, y: 1.45, w: 6.4, h: 4.6, chartColors: [C.accent], barGapWidthPct: 40, valAxisMinVal: 0,
      dataLabelFormatCode: "0", dataLabelFontSize: 10, catAxisLabelFontSize: 10 }));
  figCap(s, "Среднее число шагов по сценариям (S01–S07 — содержательные)", 0.6, 6.1, 6.4);
  bullets(s, [
    "Ошибки входа обнаруживаются до вызова модели: 2–4 шага вместо ≈ 32 в обычном прогоне",
    "Лимиты срабатывают предсказуемо (S13 — на 11-м шаге при лимите 10), частичный результат сохраняется",
    `Отборщик загружен сильнее других (${maxLoad} %): он оценивает каждого кандидата отдельно`,
    "Выдуманных ссылок нет: писатель видит только список отобранных статей, проверяющий отклоняет ссылки вне списка",
  ], { x: 7.4, y: 1.55, w: 5.3, h: 4.9, fontSize: 16, paraSpaceAfter: 14 });
}

// 11. Выводы
{
  const s = slide("Выводы и дальнейшая работа", 11);
  T(s, "Выводы", { x: 0.6, y: 1.5, w: 5.8, h: 0.4, fontFace: HEAD, fontSize: 19, bold: true, color: C.navy });
  bullets(s, [
    "Разработана многоагентная система из оркестратора и шести агентов для подготовки обзора литературы",
    "Каждая ссылка в черновике соответствует реальной статье и проверяется правилами",
    `Требования выполнены: 100 % успешных прогонов, нагрузка на агента ${maxLoad} % ≤ 40 %`,
  ], { x: 0.6, y: 2.05, w: 5.8, h: 4.3, fontSize: 16, paraSpaceAfter: 14 });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.85, y: 1.45, w: 5.85, h: 4.95, fill: { color: C.light }, line: { color: C.light } });
  T(s, "Дальнейшая работа", { x: 7.1, y: 1.65, w: 5.4, h: 0.4, fontFace: HEAD, fontSize: 19, bold: true, color: C.navy });
  bullets(s, [
    "Оценить качество текстов на моделях qwen2.5:3b и 7b",
    "Провести экспертную разметку релевантности (precision@N, nDCG)",
    "Добавить переранжирование кросс-энкодером и поиск по полным текстам",
    "Встроить систему в помощник для сопровождения НИР (диссертация)",
  ], { x: 7.1, y: 2.2, w: 5.4, h: 4.0, fontSize: 16, paraSpaceAfter: 12 });
}

// Список литературы
{
  const s = slide("Список литературы", 12);
  const refs = [
    "Robertson S., Zaragoza H. The Probabilistic Relevance Framework: BM25 and Beyond // FnTIR. 2009.",
    "Reimers N., Gurevych I. Sentence-BERT // EMNLP-IJCNLP. 2019.",
    "Wang W. et al. MiniLM: Deep Self-Attention Distillation // NeurIPS. 2020.",
    "Karpukhin V. et al. Dense Passage Retrieval for Open-Domain QA // EMNLP. 2020.",
    "Cormack G. V. et al. Reciprocal Rank Fusion // SIGIR. 2009.",
    "Lewis P. et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP // NeurIPS. 2020.",
    "Yao S. et al. ReAct: Synergizing Reasoning and Acting in LMs // ICLR. 2023.",
    "Wu Q. et al. AutoGen: Multi-Agent Conversation. arXiv:2308.08155. 2023.",
    "Hong S. et al. MetaGPT: Multi-Agent Collaborative Framework // ICLR. 2024.",
    "Madaan A. et al. Self-Refine: Iterative Refinement with Self-Feedback // NeurIPS. 2023.",
    "Agarwal S. et al. LitLLM: A Toolkit for Scientific Literature Review. arXiv:2402.01788. 2024.",
    "Walters W. H., Wilder E. I. Fabrication and errors in the bibliographic citations generated by ChatGPT // Scientific Reports. 2023. Vol. 13. 14045.",
    "Qwen Team. Qwen2.5 Technical Report. arXiv:2412.15115. 2024.",
    "Lloyd S. Least squares quantization in PCM // IEEE Trans. Information Theory. 1982.",
    "Armani7777. arxiv-similar-paper-retrieval: корпус статей arXiv. GitHub, 2026.",
  ];
  const col = (items, start, x) => T(s, items.map((r, i) => ({ text: `[${start + i}] ${r}`,
    options: { breakLine: i < items.length - 1 } })), { x, y: 1.5, w: 5.9, h: 5.3, fontSize: 14, paraSpaceAfter: 9, color: C.ink });
  col(refs.slice(0, 8), 1, 0.6);
  col(refs.slice(8), 9, 6.8);
}

pres.writeFile({ fileName: OUT }).then((f) => console.log("saved", f));
