/**
 * Презентация ResearchAssist (PPTX, 16:9). Запуск:
 *   NODE_PATH=<папка с node_modules pptxgenjs> ICONS=<папка с PNG-иконками> node presentation/build_deck.js
 * Цифры берутся из results/ (summary.json, agent_load.csv, scenarios_table.csv).
 */
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const IMG = path.join(__dirname, "img");
const ICONS = process.env.ICONS;
const OUT = path.join(__dirname, "ResearchAssist_презентация.pptx");
const SPEECH = JSON.parse(fs.readFileSync(path.join(__dirname, "speech.json"), "utf8")); // текст выступления по слайдам

// ---------- данные из results/ ----------
const summary = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "summary.json"), "utf8"));
const loadRows = fs.readFileSync(path.join(ROOT, "results", "agent_load.csv"), "utf8").trim().split(/\r?\n/).slice(1)
  .map((l) => l.split(","));
const AGENT_RU = { analyst: "Аналитик", retriever: "Поисковик", selector: "Отборщик", synthesizer: "Синтезатор",
  writer: "Писатель", critic: "Проверяющий" };
const load = loadRows.map(([k, v]) => ({ name: AGENT_RU[k], v: Math.round(parseFloat(v) * 1000) / 10 }));
const scen = fs.readFileSync(path.join(ROOT, "results", "scenarios_table.csv"), "utf8").trim().split(/\r?\n/).slice(1)
  .map((l) => l.match(/("[^"]*"|[^,]*)(,|$)/g).map((x) => x.replace(/,$/, "").replace(/^"|"$/g, "")));
const pct = (x) => `${(x * 100).toFixed(1).replace(".", ",").replace(",0", "")} %`;
const nRuns = summary.n_runs;
const okRuns = Math.round(summary.success_rate * nRuns);

// ---------- палитра (как в интерфейсе) ----------
const P = { indigo: "4F46E5", indigoDk: "3730A3", night: "1E1B4B", teal: "0EA5A4", amber: "F59E0B", red: "DC2626",
  ink: "1E2235", muted: "5B6474", line: "D5DAE6", bg: "F6F7FB", white: "FFFFFF", tint: "EEF2FF", tealTint: "E6FFFA",
  lilac: "C7D2FE" };
const FONT = "Segoe UI";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 × 7.5
pres.author = "Арман Тұрсынбаев";
pres.title = "ResearchAssist — многоагентный помощник для поиска и анализа научной литературы";
pres.theme = { headFontFace: FONT, bodyFontFace: FONT };

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: P.bg },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.4, w: 12.1, h: 0.85, fontFace: FONT,
      fontSize: 30, bold: true, color: P.ink, valign: "middle", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontFace: FONT, fontSize: 10, color: P.muted, align: "right" },
});
pres.defineSlideMaster({ title: "DARK", background: { color: P.night }, objects: [] });

// ---------- помощники ----------
const icon = (name, col = "w") => path.join(ICONS, `${name}_${col}.png`);
const shadow = () => ({ type: "outer", color: "1E2235", opacity: 0.12, blur: 8, offset: 2, angle: 90 });

function card(s, x, y, w, h, opts = {}) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: opts.fill || P.white },
    line: { color: opts.line || "E6E8F0", width: opts.lineW || 0.75 }, shadow: opts.noShadow ? undefined : shadow(),
    objectName: opts.name });
}
function iconCircle(s, x, y, d, name, fill = P.indigo, col = "w") {
  s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
  const pad = d * 0.25;
  s.addImage({ path: icon(name, col), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
}
function txt(s, text, o) {
  s.addText(text, { fontFace: FONT, color: P.ink, margin: 0, isTextBox: true, valign: "top", ...o });
}
function framedImage(s, file, x, y, w, h) {
  card(s, x - 0.06, y - 0.06, w + 0.12, h + 0.12, { line: "E2E5EE" });
  s.addImage({ path: path.join(IMG, file), x, y, w, h });
}
function badge(s, n, x, y) {
  s.addShape(pres.shapes.OVAL, { x, y, w: 0.42, h: 0.42, fill: { color: P.amber }, line: { color: P.white, width: 1.5 } });
  txt(s, String(n), { x, y, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: P.white, align: "center", valign: "middle" });
}
const content = (title) => {
  const s = pres.addSlide({ masterName: "CONTENT" });
  s.addText(title, { placeholder: "title" });
  return s;
};

// =====================================================================================
// 1. Титул
{
  const s = pres.addSlide({ masterName: "DARK" });
  txt(s, "МАГИСТЕРСКАЯ ДИССЕРТАЦИЯ · AI AND MACHINE LEARNING",
    { x: 0.7, y: 1.2, w: 7.2, h: 0.4, fontSize: 12, bold: true, color: "5EEAD4", charSpacing: 1 });
  txt(s, "ResearchAssist", { x: 0.7, y: 1.75, w: 7.2, h: 1.1, fontSize: 56, bold: true, color: P.white });
  txt(s, "Многоагентный помощник для поиска\nи анализа научной литературы",
    { x: 0.7, y: 2.95, w: 7.2, h: 1.2, fontSize: 24, color: P.lilac });
  txt(s, "Часть диссертации «Разработка интеллектуального помощника для сопровождения научно-исследовательской работы»",
    { x: 0.7, y: 4.35, w: 6.6, h: 0.8, fontSize: 14, italic: true, color: "A5B4FC" });
  txt(s, [{ text: "Арман Тұрсынбаев", options: { bold: true, color: P.white, breakLine: true } },
    { text: "Группа CSE-2506M · 2026", options: { color: P.lilac } }],
    { x: 0.7, y: 5.7, w: 6, h: 0.8, fontSize: 16 });
  // мини-схема агентов
  const cx = 10.3, cy = 3.75, R = 1.95;
  const ring = [["FaFileLines", P.teal], ["FaMagnifyingGlass", P.teal], ["FaScaleBalanced", P.teal],
    ["FaPuzzlePiece", P.teal], ["FaPenNib", P.teal], ["FaCircleCheck", P.teal]];
  ring.forEach(([ic, col], i) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / 6;
    const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
    s.addShape(pres.shapes.LINE, { x: Math.min(cx, x), y: Math.min(cy, y), w: Math.abs(x - cx) || 0.001,
      h: Math.abs(y - cy) || 0.001, flipH: (x < cx) !== (y < cy) ? true : false, line: { color: "4338CA", width: 1.5 } });
    iconCircle(s, x - 0.42, y - 0.42, 0.84, ic, col);
  });
  s.addShape(pres.shapes.OVAL, { x: cx - 0.75, y: cy - 0.75, w: 1.5, h: 1.5, fill: { color: P.indigo },
    line: { color: "818CF8", width: 2 } });
  s.addImage({ path: icon("FaCompass"), x: cx - 0.38, y: cy - 0.38, w: 0.76, h: 0.76 });
  s.addNotes(SPEECH[0]);
}

// 2. Проблема
{
  const s = content("Обзор литературы — долго, а LLM выдумывает ссылки");
  const rows = [
    ["FaHourglassHalf", P.indigo, "Долго", "найти, прочитать и сгруппировать работы — недели ручного труда"],
    ["FaBullseye", P.teal, "Нужна та же задача", "а не просто статьи из той же области"],
    ["FaTriangleExclamation", P.red, "LLM выдумывает ссылки", "часть источников, которые пишет чат-бот, не существует (Walters & Wilder, 2023)"],
  ];
  rows.forEach(([ic, col, h, d], i) => {
    const y = 1.75 + i * 1.6;
    iconCircle(s, 0.7, y, 0.8, ic, col);
    txt(s, h, { x: 1.75, y: y - 0.02, w: 4.9, h: 0.45, fontSize: 20, bold: true });
    txt(s, d, { x: 1.75, y: y + 0.45, w: 4.9, h: 0.75, fontSize: 15, color: P.muted });
  });
  // сравнение
  card(s, 7.2, 1.6, 5.5, 2.25);
  txt(s, "Обычный чат-бот", { x: 7.5, y: 1.8, w: 4.9, h: 0.4, fontSize: 15, bold: true, color: P.muted });
  txt(s, "«…этот подход впервые предложен в [7] (Smith et al., 2023)»", { x: 7.5, y: 2.25, w: 4.9, h: 0.75,
    fontSize: 16, italic: true });
  s.addImage({ path: icon("FaXmark", "r"), x: 7.5, y: 3.12, w: 0.36, h: 0.36 });
  txt(s, "такой статьи не существует", { x: 7.98, y: 3.1, w: 4.4, h: 0.4, fontSize: 15, bold: true, color: P.red,
    valign: "middle" });
  card(s, 7.2, 4.2, 5.5, 2.25, { fill: P.tealTint, line: "99F6E4" });
  txt(s, "ResearchAssist", { x: 7.5, y: 4.4, w: 4.9, h: 0.4, fontSize: 15, bold: true, color: "0F766E" });
  txt(s, "«…полноволновая инверсия с нейросетевым представлением [4]»", { x: 7.5, y: 4.85, w: 4.9, h: 0.75,
    fontSize: 16, italic: true });
  s.addImage({ path: icon("FaCheck", "t"), x: 7.5, y: 5.72, w: 0.36, h: 0.36 });
  txt(s, "[4] = arXiv:2209.03525 — найдено и проверено", { x: 7.98, y: 5.7, w: 4.6, h: 0.4, fontSize: 15, bold: true,
    color: "0F766E", valign: "middle" });
  s.addNotes(SPEECH[1]);
}

// 3. Цель и вопросы
{
  const s = content("Цель и исследовательские вопросы");
  card(s, 0.6, 1.5, 12.1, 1.25, { fill: P.tint, line: P.lilac, noShadow: true });
  iconCircle(s, 0.95, 1.73, 0.8, "FaBullseye");
  txt(s, [{ text: "Цель: ", options: { bold: true, color: P.indigoDk } },
    { text: "по статье или теме пользователя найти работы, решающие ту же задачу, и написать проверенный черновик " +
      "Related Work со ссылками только на найденные статьи" }],
    { x: 2.0, y: 1.62, w: 10.4, h: 1.0, fontSize: 18, valign: "middle" });
  const rq = [
    ["RQ1", "FaShieldHalved", "Стабильна ли система на типовых и нештатных сценариях?", "≥ 90 % успешных прогонов"],
    ["RQ2", "FaScaleBalanced", "Сбалансирована ли нагрузка между агентами?", "≤ 40 % вызовов на агента"],
    ["RQ3", "FaRobot", "Что даёт разделение на агентов по сравнению с одним агентом?", "сравнение по 7 метрикам"],
  ];
  rq.forEach(([id, ic, q, req], i) => {
    const x = 0.6 + i * 4.1, y = 3.15, w = 3.9, h = 3.45;
    card(s, x, y, w, h);
    iconCircle(s, x + 0.35, y + 0.35, 0.75, ic, i === 2 ? P.teal : P.indigo);
    txt(s, id, { x: x + 1.3, y: y + 0.42, w: 2.2, h: 0.6, fontSize: 26, bold: true, color: P.indigo, valign: "middle" });
    txt(s, q, { x: x + 0.35, y: y + 1.35, w: w - 0.7, h: 1.2, fontSize: 17 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.35, y: y + 2.65, w: w - 0.7, h: 0.5, rectRadius: 0.25,
      fill: { color: P.tealTint }, line: { color: "99F6E4" } });
    txt(s, req, { x: x + 0.35, y: y + 2.65, w: w - 0.7, h: 0.5, fontSize: 14, bold: true, color: "0F766E",
      align: "center", valign: "middle" });
  });
  s.addNotes(SPEECH[2]);
}

// 4. Путь пользователя
{
  const s = content("Как это работает: от документа до обзора");
  const steps = [
    ["FaFileLines", "Документ", "TXT, DOCX, PDF или текст темы"],
    ["FaBrain", "Задача", "задача, ключевые понятия, методы"],
    ["FaMagnifyingGlass", "Поиск", "гибридный поиск по 20 000 статей"],
    ["FaScaleBalanced", "Отбор", "та же задача? дубли и версии убираются"],
    ["FaPuzzlePiece", "Темы и пробелы", "группы подходов и что ещё не изучено"],
    ["FaPenNib", "Related Work", "текст со ссылками [n] и проверка"],
  ];
  const w = 1.8, gap = 0.26, x0 = 0.6;
  steps.forEach(([ic, h, d], i) => {
    const x = x0 + i * (w + gap), y = 1.75;
    card(s, x, y, w, 3.5);
    iconCircle(s, x + (w - 0.95) / 2, y + 0.4, 0.95, ic, i === 5 ? P.teal : P.indigo);
    txt(s, String(i + 1), { x: x + 0.15, y: y + 0.12, w: 0.4, h: 0.35, fontSize: 13, bold: true, color: P.muted });
    txt(s, h, { x: x + 0.1, y: y + 1.5, w: w - 0.2, h: 0.75, fontSize: 16, bold: true, align: "center", valign: "middle" });
    txt(s, d, { x: x + 0.15, y: y + 2.35, w: w - 0.3, h: 1.0, fontSize: 13.5, color: P.muted, align: "center" });
    if (i < 5) s.addShape(pres.shapes.CHEVRON, { x: x + w + 0.07, y: y + 0.72, w: 0.13, h: 0.3,
      fill: { color: "A5B4FC" }, line: { color: "A5B4FC" } });
  });
  card(s, 0.6, 5.65, 12.1, 0.95, { fill: P.tealTint, line: "99F6E4", noShadow: true });
  s.addImage({ path: icon("FaCircleCheck", "t"), x: 0.9, y: 5.9, w: 0.45, h: 0.45 });
  txt(s, "На выходе — черновик обзора, в котором каждая ссылка ведёт на реальную статью arXiv",
    { x: 1.55, y: 5.65, w: 10.9, h: 0.95, fontSize: 16.5, bold: true, color: "0F766E", valign: "middle" });
  s.addNotes(SPEECH[3]);
}

// 5. Архитектура
{
  const s = content("Архитектура: оркестратор + общее состояние");
  const bw = 3.55, bh = 1.15;
  const top = [["1. Аналитик", "read_document · chunk_text", "FaFileLines"],
    ["2. Поисковик", "metadata_filter · hybrid_search", "FaMagnifyingGlass"],
    ["3. Отборщик", "flag_papers + LLM", "FaScaleBalanced"]];
  const bot = [["6. Проверяющий", "check_draft · claim_support", "FaCircleCheck"],
    ["5. Писатель", "LLM: текст со ссылками [n]", "FaPenNib"],
    ["4. Синтезатор", "cluster_papers · compute_stats", "FaPuzzlePiece"]];
  const xs = [0.75, 4.89, 9.03], yTop = 1.55, yBot = 5.25, cx = 6.665, cy = 4.0;
  // линии от центра
  [...xs.map((x) => [x + bw / 2, yTop + bh]), ...xs.map((x) => [x + bw / 2, yBot])].forEach(([x, y]) => {
    s.addShape(pres.shapes.LINE, { x: Math.min(cx, x), y: Math.min(cy, y), w: Math.max(Math.abs(x - cx), 0.001),
      h: Math.abs(y - cy), flipH: (x < cx) !== (y < cy), line: { color: "A5B4FC", width: 1.5 } });
  });
  const agentBox = ([t, tools, ic], x, y) => {
    card(s, x, y, bw, bh, { line: "5EEAD4", lineW: 1.25 });
    iconCircle(s, x + 0.22, y + 0.25, 0.65, ic, P.teal);
    txt(s, t, { x: x + 1.05, y: y + 0.2, w: bw - 1.2, h: 0.42, fontSize: 15.5, bold: true });
    txt(s, tools, { x: x + 1.05, y: y + 0.63, w: bw - 1.2, h: 0.4, fontSize: 12, color: P.muted });
  };
  top.forEach((a, i) => agentBox(a, xs[i], yTop));
  bot.forEach((a, i) => agentBox(a, xs[i], yBot));
  // центр и хранилища
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: cx - 1.6, y: cy - 0.55, w: 3.2, h: 1.1, rectRadius: 0.14,
    fill: { color: P.indigo }, line: { color: P.indigo }, shadow: shadow() });
  txt(s, [{ text: "Оркестратор", options: { bold: true, fontSize: 18, breakLine: true } },
    { text: "план запроса · маршрутизация", options: { fontSize: 12, color: P.lilac } }],
    { x: cx - 1.6, y: cy - 0.55, w: 3.2, h: 1.1, color: P.white, align: "center", valign: "middle" });
  [[0.75, "TaskState (JSON)", "общее состояние задачи", "FaDatabase"], [9.53, "journal.jsonl", "каждый вызов LLM и инструмента", "FaListCheck"]]
    .forEach(([x, t, d, ic]) => {
      card(s, x, cy - 0.5, 3.05, 1.0, { fill: "F1F3F9", line: P.line, noShadow: true });
      s.addImage({ path: icon(ic, "p"), x: x + 0.2, y: cy - 0.22, w: 0.44, h: 0.44 });
      txt(s, [{ text: t, options: { bold: true, breakLine: true } }, { text: d, options: { fontSize: 11.5, color: P.muted } }],
        { x: x + 0.8, y: cy - 0.45, w: 2.15, h: 0.9, fontSize: 14, valign: "middle" });
      const lx = x < cx ? x + 3.05 : cx + 1.6, lw = x < cx ? cx - 1.6 - (x + 3.05) : x - (cx + 1.6);
      s.addShape(pres.shapes.LINE, { x: lx, y: cy, w: lw, h: 0, line: { color: "94A3B8", width: 1.25, dashType: "dash" } });
    });
  // доработка: Проверяющий → Писатель
  s.addShape(pres.shapes.LINE, { x: xs[0] + bw + 0.04, y: yBot + bh / 2, w: xs[1] - xs[0] - bw - 0.08, h: 0,
    line: { color: P.amber, width: 2.5, endArrowType: "triangle" } });
  txt(s, "доработка ≤ 1 раза", { x: xs[0] + bw - 0.6, y: yBot + bh + 0.1, w: 1.8, h: 0.3, fontSize: 11.5, bold: true,
    color: "B45309", align: "center" });
  s.addNotes(SPEECH[4]);
}

// 6. Код считает, модель рассуждает
{
  const s = content("Главный принцип: код считает, модель рассуждает");
  const H = (t) => ({ text: t, options: { bold: true, color: P.white, fill: { color: P.indigo } } });
  const rows = [
    ["Аналитик", "чтение файлов, фрагменты по 2 500 символов", "задача, понятия, методы"],
    ["Поисковик", "BM25 + косинус, z-нормировка, фильтр SQLite", "—"],
    ["Отборщик", "дубли, версии, похожие заголовки", "«та же задача?» + обоснование"],
    ["Синтезатор", "кластеры, статистика по годам и темам", "названия тем, пробелы"],
    ["Писатель", "—", "текст со ссылками [n]"],
    ["Проверяющий", "ссылка есть в списке? дубли? длина?", "оценки 1–5"],
  ].map((r) => r.map((c, j) => ({ text: c, options: { bold: j === 0, color: c === "—" ? "A0A7B4" : P.ink } })));
  s.addTable([[H("Агент"), H("Решает код"), H("Решает LLM")], ...rows], {
    x: 0.6, y: 1.55, w: 7.9, colW: [1.75, 3.55, 2.6], rowH: 0.62, fontFace: FONT, fontSize: 13.5, valign: "middle",
    border: { type: "solid", color: "E2E5EE", pt: 0.75 }, fill: { color: P.white }, margin: [0, 0.12, 0, 0.12] });
  card(s, 8.95, 1.55, 3.75, 4.35, { fill: P.tint, line: P.lilac, noShadow: true });
  txt(s, "Гибридный скор поиска", { x: 9.25, y: 1.8, w: 3.2, h: 0.4, fontSize: 15, bold: true, color: P.indigoDk });
  txt(s, "0,8 · z(cos)\n+ 0,2 · z(BM25)", { x: 9.25, y: 2.35, w: 3.2, h: 1.4, fontSize: 28, bold: true,
    color: P.indigo });
  txt(s, "Вес 0,8 на смысловую часть — результат моей предыдущей статьи о поиске похожих работ arXiv",
    { x: 9.25, y: 3.95, w: 3.2, h: 1.6, fontSize: 14, color: P.ink });
  txt(s, "Модель не может «посчитать неправильно»: все цифры, ссылки и правила — в коде",
    { x: 0.6, y: 6.1, w: 12.1, h: 0.5, fontSize: 16, italic: true, color: P.muted });
  s.addNotes(SPEECH[5]);
}

// 7. Данные и технологии
{
  const s = content("Данные и технологии");
  card(s, 0.6, 1.55, 4.6, 4.95);
  iconCircle(s, 0.95, 1.9, 0.8, "FaBookOpen");
  txt(s, "20 000", { x: 0.95, y: 2.9, w: 4.0, h: 1.2, fontSize: 64, bold: true, color: P.indigo });
  txt(s, "аннотаций статей arXiv", { x: 0.95, y: 4.05, w: 4.0, h: 0.45, fontSize: 19, bold: true });
  txt(s, "2020–2024 и май 2026 · заголовок, аннотация, авторы, категории, дата", { x: 0.95, y: 4.55, w: 3.95,
    h: 0.9, fontSize: 14, color: P.muted });
  txt(s, "из моего репозитория arxiv-similar-paper-retrieval", { x: 0.95, y: 5.55, w: 4.0, h: 0.6, fontSize: 12.5,
    italic: true, color: P.muted });
  const tiles = [
    ["FaMicrochip", "Ollama · qwen2.5", "локальная LLM, ответы в JSON"],
    ["FaMagnifyingGlass", "Гибридный поиск", "BM25 + эмбеддинги"],
    ["FaDatabase", "SQLite", "фильтр по годам и категориям"],
    ["FaCode", "pydantic", "проверка каждого ответа модели"],
    ["FaLayerGroup", "Streamlit", "веб-интерфейс на русском"],
    ["FaHouseLaptop", "Полностью офлайн", "без внешних API и интернета"],
  ];
  tiles.forEach(([ic, h, d], i) => {
    const x = 5.55 + (i % 2) * 3.62, y = 1.55 + Math.floor(i / 2) * 1.72;
    card(s, x, y, 3.45, 1.51);
    iconCircle(s, x + 0.25, y + 0.38, 0.75, ic, i === 5 ? P.teal : P.indigo);
    txt(s, h, { x: x + 1.2, y: y + 0.3, w: 2.1, h: 0.45, fontSize: 15.5, bold: true });
    txt(s, d, { x: x + 1.2, y: y + 0.75, w: 2.1, h: 0.62, fontSize: 12.5, color: P.muted });
  });
  s.addNotes(SPEECH[6]);
}

// 8. Демо: запуск и ход работы
{
  const s = content("Демо: запуск и ход работы в реальном времени");
  const lw = 5.95, lh = lw * 1460 / 2000;
  framedImage(s, "launch.png", 0.66, 1.6, lw, lh);
  const rw = 5.2, rh1 = rw * 888 / 1960, rh2 = rw * 722 / 1960;
  framedImage(s, "diagram.png", 7.48, 1.6, rw, rh1);
  framedImage(s, "feed.png", 7.48, 1.6 + rh1 + 0.3, rw, rh2);
  badge(s, 1, 0.42, 1.38); badge(s, 2, 7.24, 1.38); badge(s, 3, 7.24, 1.6 + rh1 + 0.08);
  txt(s, [{ text: "1 ", options: { bold: true, color: "B45309" } }, { text: "Ввод темы и настройки   " },
    { text: "2 ", options: { bold: true, color: "B45309" } }, { text: "Активный агент подсвечен   " },
    { text: "3 ", options: { bold: true, color: "B45309" } }, { text: "Лента сообщений «кто → кому»" }],
    { x: 0.6, y: 6.42, w: 12.1, h: 0.4, fontSize: 14, color: P.muted });
  s.addNotes(SPEECH[7]);
}

// 9. Демо: результаты
{
  const s = content("Демо: результаты — задача, статьи и черновик");
  const lw = 6.1, lh = lw * 1200 / 1960;
  framedImage(s, "draft.png", 0.66, 1.6, lw, lh);
  const rw = 5.3, rh1 = rw * 640 / 2000, rh2 = rw * 922 / 1960;
  framedImage(s, "task.png", 7.39, 1.6, rw, rh1);
  framedImage(s, "papers.png", 7.39, 1.6 + rh1 + 0.3, rw, rh2);
  badge(s, 1, 0.42, 1.38); badge(s, 2, 7.15, 1.38); badge(s, 3, 7.15, 1.6 + rh1 + 0.08);
  txt(s, [{ text: "1 ", options: { bold: true, color: "B45309" } }, { text: "Related Work: ссылки [n] ведут на arXiv   " },
    { text: "2 ", options: { bold: true, color: "B45309" } }, { text: "Выделенная задача   " },
    { text: "3 ", options: { bold: true, color: "B45309" } }, { text: "Скор и решение по каждой статье" }],
    { x: 0.6, y: 6.42, w: 12.1, h: 0.4, fontSize: 14, color: P.muted });
  s.addNotes(SPEECH[8]);
}

// 10. Надёжность
{
  const s = content("Надёжность: понятные ошибки и защиты");
  const w = 12.1, h = w * 164 / 1960;
  framedImage(s, "error.png", 0.6, 1.65, w, h);
  txt(s, "Неверный формат файла: система не падает, а подсказывает, что сделать", { x: 0.6, y: 1.65 + h + 0.18,
    w: 12.1, h: 0.4, fontSize: 14, italic: true, color: P.muted });
  const items = [
    ["FaStopwatch", "Лимит: 150 шагов", "прогон не уходит в бесконечный цикл"],
    ["FaClock", "Лимит: 20 минут", "1 200 с — затем остановка"],
    ["FaRotate", "Повтор при сбое", "и при невалидном JSON от модели"],
    ["FaShieldHalved", "Изоляция ошибок", "сбой на одной статье не ломает прогон"],
    ["FaDatabase", "Частичный результат", "состояние сохраняется при любой остановке"],
    ["FaListCheck", "Журнал каждого шага", "видно, кто и почему принял решение"],
  ];
  items.forEach(([ic, t, d], i) => {
    const x = 0.6 + (i % 3) * 4.1, y = 3.45 + Math.floor(i / 3) * 1.6;
    card(s, x, y, 3.9, 1.4);
    iconCircle(s, x + 0.25, y + 0.33, 0.74, ic, i < 3 ? P.indigo : P.teal);
    txt(s, t, { x: x + 1.15, y: y + 0.27, w: 2.6, h: 0.42, fontSize: 15.5, bold: true });
    txt(s, d, { x: x + 1.15, y: y + 0.7, w: 2.6, h: 0.6, fontSize: 12.5, color: P.muted });
  });
  s.addNotes(SPEECH[9]);
}

// 11. Результаты
{
  const s = content("Результаты оценки: 15 сценариев × 3 прогона");
  const stats = [
    [pct(summary.success_rate).replace(" %", " %"), `${okRuns} из ${nRuns} прогонов успешны`, "требование ≥ 90 %", P.indigo],
    [pct(summary.max_agent_share), "макс. нагрузка на агента", "требование ≤ 40 %", P.teal],
    ["10 / 10", "тестов pytest проходят", "инструменты и правила", P.indigo],
  ];
  stats.forEach(([v, l, r, col], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.5, 3.9, 1.95);
    txt(s, v, { x: x + 0.3, y: 1.62, w: 3.3, h: 0.95, fontSize: 44, bold: true, color: col });
    txt(s, l, { x: x + 0.3, y: 2.55, w: 3.4, h: 0.4, fontSize: 15, bold: true });
    txt(s, r, { x: x + 0.3, y: 2.95, w: 3.4, h: 0.35, fontSize: 12.5, color: P.muted });
  });
  card(s, 0.6, 3.75, 12.1, 3.0);
  const labels = load.map((d) => d.name);
  s.addChart([
    { type: pres.charts.BAR, data: [{ name: "Доля вызовов, %", labels, values: load.map((d) => d.v) }],
      options: { chartColors: [P.indigo], barGapWidthPct: 55 } },
    { type: pres.charts.LINE, data: [{ name: "Порог 40 %", labels, values: labels.map(() => 40) }],
      options: { chartColors: [P.red], lineSize: 1.5, lineDash: "dash", lineDataSymbol: "none", showValue: false } },
  ], {
    x: 0.8, y: 3.85, w: 11.7, h: 2.8, showTitle: true, title: "Доля вызовов LLM и инструментов по агентам, %",
    titleFontFace: FONT, titleFontSize: 13, titleColor: P.ink, showValue: true, dataLabelFontFace: FONT,
    dataLabelFontSize: 11, dataLabelColor: P.ink, dataLabelFormatCode: "0.0", catAxisLabelFontFace: FONT,
    catAxisLabelFontSize: 12, catAxisLabelColor: P.muted, valAxisLabelFontFace: FONT, valAxisLabelFontSize: 10,
    valAxisLabelColor: P.muted, valAxisMaxVal: 45, valAxisMinVal: 0, valAxisMajorUnit: 10,
    valGridLine: { color: "E6E8F0", size: 0.75 }, catGridLine: { style: "none" }, showLegend: true,
    legendPos: "r", legendFontFace: FONT, legendFontSize: 11, legendColor: P.muted,
  });
  s.addNotes(SPEECH[10]);
}

// 12. Итог
{
  const s = pres.addSlide({ masterName: "DARK" });
  txt(s, "Итог", { x: 0.7, y: 0.6, w: 6, h: 0.8, fontSize: 36, bold: true, color: P.white });
  const pts = [
    "Шесть агентов и оркестратор: поиск, отбор, синтез, текст и проверка",
    "Каждая ссылка — реальная статья arXiv, проверенная кодом",
    `${pct(summary.success_rate)} успешных прогонов, нагрузка на агента ${pct(summary.max_agent_share)} ≤ 40 %`,
  ];
  pts.forEach((t, i) => {
    const y = 1.75 + i * 1.0;
    iconCircle(s, 0.75, y, 0.6, "FaCheck", P.teal);
    txt(s, t, { x: 1.6, y, w: 10.5, h: 0.6, fontSize: 20, color: P.white, valign: "middle" });
  });
  txt(s, "Спасибо! Готов ответить на вопросы", { x: 0.7, y: 4.95, w: 11, h: 0.9, fontSize: 34, bold: true,
    color: "5EEAD4" });
  s.addImage({ path: icon("FaGithub"), x: 0.75, y: 6.1, w: 0.42, h: 0.42 });
  txt(s, "github.com/Armani7777/aiml_assignment_3", { x: 1.35, y: 6.08, w: 8, h: 0.46, fontSize: 16, color: P.lilac,
    valign: "middle", hyperlink: { url: "https://github.com/Armani7777/aiml_assignment_3" } });
  s.addNotes(SPEECH[11]);
}

// 13. Запасной: сценарии
{
  const s = content("Запасной слайд: 15 сценариев оценки");
  const H = (t) => ({ text: t, options: { bold: true, color: P.white, fill: { color: P.indigo } } });
  const status = { done: "готово", failed: "ошибка входа", limit: "сработал лимит" };
  const rows = scen.map((r) => [r[0], r[2], r[1], `${r[3]}/${r[4]}`, status[r[5]] || r[5], r[6] || "—"])
    .map((r) => r.map((c, j) => ({ text: c, options: { bold: j === 0, color: j === 3 ? "0F766E" : P.ink } })));
  s.addTable([[H("ID"), H("Сценарий"), H("Группа"), H("Успешно"), H("Итог"), H("Код ошибки")], ...rows], {
    x: 0.6, y: 1.4, w: 12.1, colW: [0.8, 3.9, 2.3, 1.2, 1.9, 2.0], rowH: 0.33, fontFace: FONT, fontSize: 11.5,
    valign: "middle", border: { type: "solid", color: "E2E5EE", pt: 0.75 }, fill: { color: P.white },
    margin: [0, 0.1, 0, 0.1] });
  s.addNotes(SPEECH[12]);
}

// 14. Запасной: журнал
{
  const s = content("Запасной слайд: журнал решений агентов");
  const w = 7.0, h = w * 1700 / 2000;
  framedImage(s, "journal.png", 0.66, 1.5, w * 0.86, h * 0.86);
  txt(s, "Каждый вызов LLM и инструмента — строка JSONL", { x: 7.65, y: 1.7, w: 5.0, h: 0.9, fontSize: 20, bold: true });
  const pts = ["время и агент", "тип: llm, tool или message", "длительность и токены", "статус: ok, retry, error"];
  txt(s, pts.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < pts.length - 1 } })),
    { x: 7.65, y: 2.75, w: 5.0, h: 2.0, fontSize: 16, paraSpaceAfter: 8 });
  txt(s, "Аудиторский след: по журналу видно, какой агент и на основании чего принял решение",
    { x: 7.65, y: 4.9, w: 5.0, h: 1.0, fontSize: 15, italic: true, color: P.muted });
  s.addNotes(SPEECH[13]);
}

pres.writeFile({ fileName: OUT }).then((f) => console.log("saved", f));
