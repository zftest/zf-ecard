/* =========================================================
   词练 · UI Prototype
   Mock-only interaction layer. No backend, no persistence.
   ========================================================= */

const WORDS = [
  { id: "w01", word: "environment", pos: "n.", meaning: "环境", meanings: ["环境"], phonetic: "/ɪnˈvaɪrənmənt/", unit: "Unit 3", theme: "自然", status: "待复习" },
  { id: "w02", word: "volunteer", pos: "n.", meaning: "志愿者", meanings: ["志愿者"], phonetic: "/ˌvɒlənˈtɪə(r)/", unit: "Unit 3", theme: "成长", status: "学习中" },
  { id: "w03", word: "communicate", pos: "v.", meaning: "交流；沟通", meanings: ["交流", "沟通", "交流；沟通"], phonetic: "/kəˈmjuːnɪkeɪt/", unit: "Unit 3", theme: "交流", status: "待复习" },
  { id: "w04", word: "experience", pos: "n.", meaning: "经历；经验", meanings: ["经历", "经验", "经历；经验"], phonetic: "/ɪkˈspɪəriəns/", unit: "Unit 3", theme: "成长", status: "本轮通过" },
  { id: "w05", word: "achieve", pos: "v.", meaning: "实现；达到", meanings: ["实现", "达到", "实现；达到"], phonetic: "/əˈtʃiːv/", unit: "Unit 3", theme: "成长", status: "学习中" },
  { id: "w06", word: "protect", pos: "v.", meaning: "保护", meanings: ["保护"], phonetic: "/prəˈtekt/", unit: "Unit 3", theme: "自然", status: "本轮通过" },
  { id: "w07", word: "discover", pos: "v.", meaning: "发现", meanings: ["发现"], phonetic: "/dɪˈskʌvə(r)/", unit: "Unit 3", theme: "成长", status: "学习中" },
  { id: "w08", word: "encourage", pos: "v.", meaning: "鼓励", meanings: ["鼓励"], phonetic: "/ɪnˈkʌrɪdʒ/", unit: "Unit 3", theme: "交流", status: "学习中" },
  { id: "w09", word: "pollution", pos: "n.", meaning: "污染", meanings: ["污染"], phonetic: "/pəˈluːʃn/", unit: "Unit 3", theme: "自然", status: "待复习" },
  { id: "w10", word: "improve", pos: "v.", meaning: "改善；提高", meanings: ["改善", "提高", "改善；提高"], phonetic: "/ɪmˈpruːv/", unit: "Unit 3", theme: "成长", status: "本轮通过" },
  { id: "w11", word: "confident", pos: "adj.", meaning: "自信的", meanings: ["自信的"], phonetic: "/ˈkɒnfɪdənt/", unit: "Unit 3", theme: "成长", status: "待复习" },
  { id: "w12", word: "opportunity", pos: "n.", meaning: "机会", meanings: ["机会"], phonetic: "/ˌɒpəˈtjuːnəti/", unit: "Unit 4", theme: "成长", status: "学习中" },
  { id: "w13", word: "challenge", pos: "n.", meaning: "挑战", meanings: ["挑战"], phonetic: "/ˈtʃælɪndʒ/", unit: "Unit 4", theme: "成长", status: "学习中" },
  { id: "w14", word: "consider", pos: "v.", meaning: "考虑", meanings: ["考虑"], phonetic: "/kənˈsɪdə(r)/", unit: "Unit 4", theme: "交流", status: "本轮通过" },
  { id: "w15", word: "develop", pos: "v.", meaning: "发展；培养", meanings: ["发展", "培养", "发展；培养"], phonetic: "/dɪˈveləp/", unit: "Unit 4", theme: "成长", status: "学习中" },
  { id: "w16", word: "influence", pos: "v.", meaning: "影响", meanings: ["影响"], phonetic: "/ˈɪnfluəns/", unit: "Unit 4", theme: "交流", status: "学习中" },
  { id: "w17", word: "recognize", pos: "v.", meaning: "认出；认可", meanings: ["认出", "认可", "认出；认可"], phonetic: "/ˈrekəɡnaɪz/", unit: "Unit 4", theme: "成长", status: "待复习" },
  { id: "w18", word: "responsible", pos: "adj.", meaning: "有责任的", meanings: ["有责任的"], phonetic: "/rɪˈspɒnsəbl/", unit: "Unit 4", theme: "成长", status: "学习中" },
  { id: "w19", word: "solution", pos: "n.", meaning: "解决办法", meanings: ["解决办法", "解决方案"], phonetic: "/səˈluːʃn/", unit: "Unit 3", theme: "自然", status: "学习中" },
  { id: "w20", word: "valuable", pos: "adj.", meaning: "有价值的", meanings: ["有价值的", "宝贵的"], phonetic: "/ˈvæljuəbl/", unit: "Unit 3", theme: "成长", status: "本轮通过" },
  { id: "w21", word: "reduce", pos: "v.", meaning: "减少", meanings: ["减少"], phonetic: "/rɪˈdjuːs/", unit: "Unit 3", theme: "自然", status: "学习中" },
  { id: "w22", word: "recycle", pos: "v.", meaning: "回收利用", meanings: ["回收利用", "回收"], phonetic: "/ˌriːˈsaɪkl/", unit: "Unit 3", theme: "自然", status: "学习中" },
  { id: "w23", word: "energy", pos: "n.", meaning: "能源；能量", meanings: ["能源", "能量", "能源；能量"], phonetic: "/ˈenədʒi/", unit: "Unit 3", theme: "自然", status: "本轮通过" },
  { id: "w24", word: "habitat", pos: "n.", meaning: "栖息地", meanings: ["栖息地"], phonetic: "/ˈhæbɪtæt/", unit: "Unit 3", theme: "自然", status: "学习中" },
  { id: "w25", word: "realize", pos: "v.", meaning: "意识到", meanings: ["意识到"], phonetic: "/ˈriːəlaɪz/", unit: "Unit 3", theme: "成长", status: "待复习" },
  { id: "w26", word: "support", pos: "v.", meaning: "支持", meanings: ["支持"], phonetic: "/səˈpɔːt/", unit: "Unit 3", theme: "交流", status: "学习中" },
  { id: "w27", word: "purpose", pos: "n.", meaning: "目的", meanings: ["目的"], phonetic: "/ˈpɜːpəs/", unit: "Unit 3", theme: "成长", status: "学习中" }
];

const MODE_LABELS = {
  zh_to_en: "汉译英",
  audio_to_en: "听音写词",
  en_to_zh: "英译汉",
  phonetic_to_en: "音标写词"
};

const MODE_HINTS = {
  zh_to_en: "看中文写英文，检测拼写产出。",
  audio_to_en: "播放英文发音，检测音形对应。",
  en_to_zh: "看英文写中文，检测词义回忆；不并入拼写掌握。",
  phonetic_to_en: "看音标写英文，检测音标与拼写映射。"
};

const VIEW_META = {
  dashboard: ["LEARNING DESK", "学习首页"],
  words: ["WORD LIBRARY", "单词库"],
  config: ["DICTATION SETUP", "分类默写"],
  practice: ["DICTATION SESSION", "默写作答"],
  result: ["SESSION RESULT", "练习结果"],
  wrong: ["MISTAKE NOTEBOOK", "错词复习"],
  import: ["IMPORT STUDIO", "词库导入"],
  settings: ["SETTINGS", "学习设置"]
};

const state = {
  currentView: "dashboard",
  selected: new Set(),
  filters: { q: "", unit: "all", themes: new Set(), pos: new Set(), statuses: new Set() },
  config: { range: "unit3", mode: "zh_to_en", size: 20, order: "random", hint: true },
  session: null,
  result: null,
  wrongBook: [
    { wordId: "w01", lastAnswer: "enviroment", count: 3, due: "今天", status: "待复习" },
    { wordId: "w03", lastAnswer: "comunicate", count: 2, due: "今天", status: "待复习" },
    { wordId: "w11", lastAnswer: "confidant", count: 2, due: "明天", status: "待复习" }
  ]
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function escapeHTML(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getWord(id) {
  return WORDS.find((word) => word.id === id);
}

function normalizeEn(value) {
  return value
    .trim()
    .replace(/\s+/g, " ")
    .replace(/[’‘]/g, "'")
    .toLowerCase();
}

function normalizeZh(value) {
  return value
    .trim()
    .replace(/\s+/g, "")
    .replace(/[，。；、,.;]/g, "");
}

function shuffle(items) {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const random = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[random]] = [copy[random], copy[index]];
  }
  return copy;
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => node.classList.remove("show"), 2200);
}

function speak(word) {
  if (!("speechSynthesis" in window)) {
    toast("当前浏览器不支持设备语音，请使用音频素材方案");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(word);
  utterance.lang = "en-GB";
  utterance.rate = 0.82;
  utterance.pitch = 1;
  const voice = window.speechSynthesis.getVoices().find((item) => item.lang === "en-GB");
  if (voice) utterance.voice = voice;
  window.speechSynthesis.speak(utterance);
  toast("设备语音演示；生产环境由后端统一提供合法音频");
}

/* ---------------- Navigation ---------------- */
function switchView(name, options = {}) {
  if (!VIEW_META[name]) return;
  state.currentView = name;
  const [eyebrow, title] = VIEW_META[name];
  $("#pageEyebrow").textContent = eyebrow;
  $("#pageTitle").textContent = title;

  $$(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  $$(".nav-item[data-view], .mobile-nav [data-view]").forEach((item) => {
    const target = item.dataset.view;
    const active = target === name || (name === "result" && target === "config");
    item.classList.toggle("active", active);
  });

  $(".app-shell").classList.toggle("focus-mode", name === "practice");
  document.body.classList.toggle("focus-mode", name === "practice");

  if (name === "words") renderWords();
  if (name === "config") renderConfigSummary();
  if (name === "wrong") renderWrongBook();
  if (name === "result") renderResult();
  if (name === "practice") renderPractice();

  if (!options.keepScroll) window.scrollTo({ top: 0, behavior: "smooth" });
}

/* ---------------- Words ---------------- */
function getFilteredWords() {
  const { q, unit, themes, pos, statuses } = state.filters;
  const text = q.trim().toLowerCase();
  return WORDS.filter((word) => {
    const matchText = !text || word.word.toLowerCase().includes(text) || word.meaning.includes(text);
    const matchUnit = unit === "all" || word.unit === unit;
    const matchTheme = themes.size === 0 || themes.has(word.theme);
    const matchPos = pos.size === 0 || pos.has(word.pos);
    const matchStatus = statuses.size === 0 || statuses.has(word.status);
    return matchText && matchUnit && matchTheme && matchPos && matchStatus;
  });
}

function statusClass(status) {
  if (status === "待复习") return "due";
  if (status === "本轮通过") return "pass";
  return "";
}

function renderWords() {
  const words = getFilteredWords();
  $("#wordResultCount").textContent = `共 ${words.length} 个词`;
  $("#wordEmpty").classList.toggle("hidden", words.length > 0);
  $("#wordTable").classList.toggle("hidden", words.length === 0);

  const header = `
    <div class="word-row head" role="row">
      <span></span><span>单词</span><span>词性</span><span>释义</span><span>发音</span><span>状态</span>
    </div>`;

  const rows = words.map((word) => `
    <div class="word-row" role="row" data-word-id="${word.id}">
      <input type="checkbox" aria-label="选择 ${escapeHTML(word.word)}" data-word-check="${word.id}" ${state.selected.has(word.id) ? "checked" : ""} />
      <button class="word-lemma" data-open-word="${word.id}" aria-label="查看 ${escapeHTML(word.word)} 详情">
        <strong>${escapeHTML(word.word)}</strong>
        <small>${escapeHTML(word.phonetic)}</small>
      </button>
      <span class="word-pos">${escapeHTML(word.pos)}</span>
      <span class="word-meaning">${escapeHTML(word.meaning)}</span>
      <button class="row-sound" data-say="${escapeHTML(word.word)}" aria-label="播放 ${escapeHTML(word.word)} 发音">
        <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4Zm12.5 3a4.5 4.5 0 0 0-2-3.7v7.4a4.5 4.5 0 0 0 2-3.7Z" fill="currentColor"/></svg>
      </button>
      <span class="row-status ${statusClass(word.status)}">${escapeHTML(word.status)}</span>
    </div>`).join("");

  $("#wordTable").innerHTML = header + rows;
  updateSelectionBar();
}

function updateSelectionBar() {
  const bar = $("#selectionBar");
  bar.classList.toggle("hidden", state.selected.size === 0);
  $("#selectedCount").textContent = state.selected.size;
  const all = getFilteredWords();
  $("#selectAllWords").checked = all.length > 0 && all.every((word) => state.selected.has(word.id));
}

function openWordDrawer(word) {
  $("#drawerContent").innerHTML = `
    <p class="eyebrow" style="margin-top:32px">${escapeHTML(word.unit)} · ${escapeHTML(word.theme)}</p>
    <h2 class="drawer-word">${escapeHTML(word.word)}</h2>
    <p class="drawer-phonetic">${escapeHTML(word.phonetic)} <span style="margin-left:8px">${escapeHTML(word.pos)}</span></p>
    <p class="drawer-meaning">${escapeHTML(word.meaning)}</p>
    <div class="drawer-example">
      <em>Small actions can protect the environment.</em>
      小小的行动也能保护环境。
    </div>
    <div class="drawer-tags">
      <span>${escapeHTML(word.theme)}</span>
      <span>${escapeHTML(word.unit)}</span>
      <span>${escapeHTML(word.status)}</span>
    </div>
    <div class="drawer-actions">
      <button class="secondary-btn" data-say="${escapeHTML(word.word)}">播放发音</button>
      <button class="primary-btn" data-open-practice="${word.id}">练这个单词</button>
    </div>
    <p class="drawer-note">发音由浏览器设备语音演示。生产版本将展示音频来源、许可和英美口音状态。</p>`;
  $("#wordDrawer").classList.add("open");
  $("#wordDrawer").setAttribute("aria-hidden", "false");
  $("#scrim").classList.remove("hidden");
}

function closeDrawer() {
  $("#wordDrawer").classList.remove("open");
  $("#wordDrawer").setAttribute("aria-hidden", "true");
  $("#scrim").classList.add("hidden");
}

/* ---------------- Config ---------------- */
function getRangePool(range = state.config.range) {
  if (range === "theme") return WORDS.filter((word) => word.theme === "自然");
  if (range === "wrong") return state.wrongBook.map((entry) => getWord(entry.wordId)).filter(Boolean);
  return WORDS.filter((word) => word.unit === "Unit 3");
}

function getRangeWords(range = state.config.range) {
  if (state.selected.size > 0) return WORDS.filter((word) => state.selected.has(word.id));
  return getRangePool(range);
}

function renderConfigSummary() {
  const pool = getRangeWords();
  const rangeLabels = { unit3: "Unit 3", theme: "自然与环境", wrong: "错词本" };
  $$("[data-range]").forEach((button) => {
    const range = button.dataset.range;
    button.textContent = `${rangeLabels[range]} · ${getRangePool(range).length} 词`;
  });
  const available = Math.min(state.config.size, pool.length);
  $("#summaryCount").textContent = available;
  $("#summaryMode").textContent = MODE_LABELS[state.config.mode];
  $("#summaryOrder").textContent = state.config.order === "random" ? "随机" : "词表顺序";
  $("#summaryHint").textContent = state.config.hint ? "开启" : "关闭";
  $("#modeHint").textContent = MODE_HINTS[state.config.mode];
  $("#startPracticeBtn").disabled = pool.length === 0;
  $("#startPracticeBtn").textContent = pool.length === 0 ? "当前范围没有单词" : "开始练习";
}

function updateConfigUi() {
  $$(".mode-card").forEach((card) => {
    const radio = $("input", card);
    card.classList.toggle("active", radio.checked);
  });
  $$("[data-size]").forEach((button) => button.classList.toggle("active", Number(button.dataset.size) === state.config.size));
  $$("[data-order]").forEach((button) => button.classList.toggle("active", button.dataset.order === state.config.order));
  $$("[data-range]").forEach((button) => button.classList.toggle("active", button.dataset.range === state.config.range));
  renderConfigSummary();
}

/* ---------------- Practice ---------------- */
function startPractice(itemsOverride = null, modeOverride = null) {
  const pool = itemsOverride || getRangeWords();
  if (!pool.length) {
    toast("当前范围没有可用于练习的单词");
    return;
  }
  const mode = modeOverride || state.config.mode;
  let items = state.config.order === "random" ? shuffle(pool) : [...pool];
  items = items.slice(0, Math.min(state.config.size, items.length));

  state.session = {
    mode,
    items,
    index: 0,
    answers: [],
    firstCorrect: 0,
    hintUsed: false,
    answered: false
  };
  state.result = null;
  switchView("practice");
}

function currentSessionItem() {
  if (!state.session) return null;
  return state.session.items[state.session.index] || null;
}

function renderPractice() {
  const session = state.session;
  if (!session) {
    switchView("config");
    return;
  }
  const item = currentSessionItem();
  if (!item) {
    finishPractice();
    return;
  }

  session.hintUsed = false;
  session.answered = false;

  $("#practiceCounter").textContent = `${session.index + 1} / ${session.items.length}`;
  $("#practiceModeLabel").textContent = MODE_LABELS[session.mode];
  $("#firstScore").textContent = session.firstCorrect;
  $("#practiceProgress").style.width = `${((session.index + 1) / session.items.length) * 100}%`;
  $("#feedback").classList.add("hidden");
  $("#feedback").innerHTML = "";
  $("#nextBtn").classList.add("hidden");
  $("#answerInput").disabled = false;
  $("#answerInput").value = "";
  $("#submitAnswer").disabled = true;
  $("#hintNote").textContent = "";
  $("#hintBtn").classList.remove("used");
  $("#hintBtn").disabled = !state.config.hint;
  $("#hintBtn").textContent = state.config.hint ? "看首字母" : "提示已关闭";
  $("#practiceHint").textContent = state.config.hint ? "提示使用会计入记录，不会直接判错。" : "本组练习未开启首字母提示。";

  const prompt = $("#promptArea");
  const tools = $("#practiceTools");
  tools.classList.toggle("hidden", session.mode === "en_to_zh");
  $("#replayAudio").classList.toggle("hidden", session.mode !== "audio_to_en");

  if (session.mode === "zh_to_en") {
    $("#practiceKicker").textContent = "根据中文释义与词性，写出对应的英文单词";
    prompt.innerHTML = `
      <div class="prompt-meaning">${escapeHTML(item.meaning)}<span class="prompt-pos">${escapeHTML(item.pos)}</span></div>
      <p class="prompt-sub">完整拼写，首尾空格会被忽略</p>`;
    $("#answerInput").placeholder = "输入英文单词";
    $("#answerInput").inputMode = "text";
  } else if (session.mode === "en_to_zh") {
    $("#practiceKicker").textContent = "看英文单词，写出一个核心中文释义";
    prompt.innerHTML = `
      <div class="prompt-word">${escapeHTML(item.word)}</div>
      <p class="prompt-phonetic">${escapeHTML(item.phonetic)} · ${escapeHTML(item.pos)}</p>
      <p class="prompt-sub">写出一个核心释义即可；生产版会处理待确认状态</p>`;
    $("#answerInput").placeholder = "输入中文释义";
    $("#answerInput").inputMode = "text";
  } else if (session.mode === "audio_to_en") {
    $("#practiceKicker").textContent = "听发音，写出对应的英文单词";
    prompt.innerHTML = `
      <div class="audio-prompt">
        <button class="play-big" type="button" id="promptPlay" aria-label="播放发音">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9H4Zm12.5 3a4.5 4.5 0 0 0-2-3.7v7.4a4.5 4.5 0 0 0 2-3.7Z" fill="currentColor"/></svg>
        </button>
        <p class="prompt-sub">点击播放，可重听；词形在提交前不显示</p>
      </div>`;
    $("#answerInput").placeholder = "输入听到的英文单词";
    $("#promptPlay")?.addEventListener("click", () => speak(item.word));
    window.setTimeout(() => speak(item.word), 260);
  } else {
    $("#practiceKicker").textContent = "看音标与词性，写出对应的英文单词";
    prompt.innerHTML = `
      <div class="prompt-word">${escapeHTML(item.phonetic)}</div>
      <p class="prompt-sub">${escapeHTML(item.pos)} · 根据音标还原拼写</p>`;
    $("#answerInput").placeholder = "输入英文单词";
  }

  window.setTimeout(() => $("#answerInput").focus(), 80);
}

function markDiff(user, correct) {
  const userChars = Array.from(user);
  const correctChars = Array.from(correct);
  let prefix = 0;
  while (prefix < userChars.length && prefix < correctChars.length && userChars[prefix].toLowerCase() === correctChars[prefix].toLowerCase()) prefix += 1;
  let suffix = 0;
  while (
    suffix < userChars.length - prefix &&
    suffix < correctChars.length - prefix &&
    userChars[userChars.length - 1 - suffix].toLowerCase() === correctChars[correctChars.length - 1 - suffix].toLowerCase()
  ) suffix += 1;

  const userMiddle = userChars.slice(prefix, userChars.length - suffix);
  const correctMiddle = correctChars.slice(prefix, correctChars.length - suffix);
  const before = userChars.slice(0, prefix).map((char) => `<span class="diff-char">${escapeHTML(char)}</span>`).join("");
  const after = userChars.slice(userChars.length - suffix).map((char) => `<span class="diff-char">${escapeHTML(char)}</span>`).join("");
  const bad = userMiddle.map((char) => `<span class="diff-char bad">${escapeHTML(char)}</span>`).join("");
  const missing = correctMiddle.map((char) => `<span class="diff-char missing">${escapeHTML(char)}</span>`).join("");
  return { user: before + bad + after, correct: before + missing + after };
}

function gradeAnswer(answer) {
  const session = state.session;
  const item = currentSessionItem();
  if (!session || !item) return;

  const normalized = session.mode === "en_to_zh" ? normalizeZh(answer) : normalizeEn(answer);
  let correct = false;
  if (session.mode === "en_to_zh") {
    correct = item.meanings.some((meaning) => normalizeZh(meaning) === normalized);
  } else {
    correct = normalizeEn(item.word) === normalized;
  }

  const answerRecord = {
    wordId: item.id,
    user: answer.trim(),
    correct,
    hintUsed: session.hintUsed,
    mode: session.mode
  };
  session.answers.push(answerRecord);
  session.answered = true;

  if (correct && !session.hintUsed) session.firstCorrect += 1;

  if (!correct) {
    addWrongWord(item.id, answer.trim());
  }

  $("#firstScore").textContent = session.firstCorrect;
  $("#answerInput").disabled = true;
  $("#submitAnswer").disabled = true;
  const feedback = $("#feedback");
  feedback.classList.remove("hidden", "correct", "wrong");
  feedback.classList.add(correct ? "correct" : "wrong");

  let detail = "";
  if (session.mode !== "en_to_zh") {
    const diff = markDiff(answer.trim(), item.word);
    detail = `
      <div class="diff-line"><span>你的答案</span>${diff.user || '<span class="diff-char missing">—</span>'}</div>
      <div class="diff-line"><span>标准答案</span>${diff.correct}</div>`;
  } else {
    detail = `
      <div class="feedback-meta">参考释义：<strong>${escapeHTML(item.meaning)}</strong>${correct ? "" : " · 生产版可将未命中答案标记为待确认"}</div>`;
  }

  feedback.innerHTML = `
    <div class="feedback-title">${correct ? "✓ 回答正确" : "× 需要订正"}${session.hintUsed && correct ? "（提示后答对）" : ""}</div>
    <div class="feedback-answer">${escapeHTML(item.word)} <span class="feedback-meta">${escapeHTML(item.phonetic)} · ${escapeHTML(item.pos)} ${escapeHTML(item.meaning)}</span></div>
    ${detail}
    <div class="feedback-meta">${correct && !session.hintUsed ? "计入无提示首答正确。" : session.hintUsed && correct ? "答对了，但不计入无提示首答正确。" : "已加入错词本，结果显示首答差异。"}</div>`;

  $("#nextBtn").classList.remove("hidden");
  $("#nextBtn").textContent = session.index === session.items.length - 1 ? "查看结果 →" : "下一题 →";
  $("#nextBtn").focus();
}

function useHint() {
  const item = currentSessionItem();
  if (!item || state.session.answered) return;
  state.session.hintUsed = true;
  $("#hintBtn").classList.add("used");
  $("#hintBtn").disabled = true;
  $("#hintBtn").textContent = "已提示";
  $("#hintNote").textContent = `${item.word[0]} ${"_ ".repeat(Math.max(item.word.length - 1, 0)).trim()}`;
}

function nextQuestion() {
  if (!state.session) return;
  if (state.session.index >= state.session.items.length - 1) {
    finishPractice();
    return;
  }
  state.session.index += 1;
  renderPractice();
}

function finishPractice() {
  if (!state.session) return;
  const answers = state.session.answers;
  const wrongItems = answers.filter((answer) => !answer.correct).map((answer) => getWord(answer.wordId)).filter(Boolean);
  const hintedCorrect = answers.filter((answer) => answer.correct && answer.hintUsed).length;
  state.result = {
    total: answers.length,
    firstCorrect: state.session.firstCorrect,
    hintedCorrect,
    wrongItems,
    mode: state.session.mode,
    answers
  };
  switchView("result");
}

function addWrongWord(wordId, lastAnswer) {
  const existing = state.wrongBook.find((entry) => entry.wordId === wordId);
  if (existing) {
    existing.count += 1;
    existing.lastAnswer = lastAnswer;
    existing.due = "今天";
  } else {
    state.wrongBook.unshift({ wordId, lastAnswer, count: 1, due: "今天", status: "待复习" });
  }
  $("#wrongNavBadge").textContent = state.wrongBook.length;
  $("#wrongDue").textContent = state.wrongBook.length;
}

/* ---------------- Result ---------------- */
function renderResult() {
  const result = state.result;
  if (!result) return;
  const accuracy = result.total ? Math.round((result.firstCorrect / result.total) * 100) : 0;
  $("#resultSummary").textContent = `${MODE_LABELS[result.mode]} · 共作答 ${result.total} 词 · 单次结果不代表永久掌握`;
  $("#resultMetrics").innerHTML = `
    <div class="metric"><span>实际作答</span><strong>${result.total}</strong><small>个词</small></div>
    <div class="metric"><span>无提示首答正确</span><strong>${result.firstCorrect}</strong><small>${accuracy}% 首答正确率</small></div>
    <div class="metric"><span>提示后答对</span><strong>${result.hintedCorrect}</strong><small>单独记录</small></div>
    <div class="metric"><span>错词</span><strong>${result.wrongItems.length}</strong><small>可只练错词</small></div>`;

  const wrongList = $("#resultWrongList");
  wrongList.innerHTML = result.wrongItems.map((word) => {
    const answer = result.answers.find((item) => item.wordId === word.id);
    return `
      <div class="result-wrong">
        <div class="wrong-word-line">
          <strong>${escapeHTML(word.word)}</strong>
          <span>${escapeHTML(word.pos)} ${escapeHTML(word.meaning)} · ${escapeHTML(word.phonetic)}</span>
        </div>
        <div class="wrong-compare">
          <div><span>你的答案</span><code>${escapeHTML(answer?.user || "未作答")}</code></div>
          <div class="correct"><span>标准答案</span><code>${escapeHTML(word.word)}</code></div>
        </div>
      </div>`;
  }).join("");

  const perfect = result.wrongItems.length === 0;
  $("#resultPerfect").classList.toggle("hidden", !perfect);
  wrongList.classList.toggle("hidden", perfect);
  $("#wrongCountLabel").textContent = `${result.wrongItems.length} 个`;
  $("#retryWrongBtn").disabled = perfect;
  $("#retryWrongBtn").textContent = perfect ? "本轮没有错词" : "只练本次错词";
}

function retryWrongWords() {
  if (!state.result) return;
  const items = state.result.wrongItems;
  if (!items.length) {
    toast("本轮没有错词，可以做一次到期复习");
    return;
  }
  const previousMode = state.result.mode;
  startPractice(items, previousMode);
  toast("已重新开始，只包含本次错词");
}

/* ---------------- Wrong book ---------------- */
function renderWrongBook() {
  $("#wrongDue").textContent = state.wrongBook.length;
  $("#wrongNavBadge").textContent = state.wrongBook.length;
  if (!state.wrongBook.length) {
    $("#wrongList").innerHTML = `<div class="wrong-empty">错词本是空的。先完成一组默写，错词会自动出现在这里。</div>`;
    return;
  }
  const header = `
    <div class="wrong-row head">
      <span>单词</span><span>释义</span><span>最近错误</span><span>下次复习</span><span>操作</span>
    </div>`;
  const rows = state.wrongBook.map((entry) => {
    const word = getWord(entry.wordId);
    if (!word) return "";
    return `
      <div class="wrong-row">
        <span class="wrong-lemma">${escapeHTML(word.word)}</span>
        <span class="wrong-meaning">${escapeHTML(word.pos)} ${escapeHTML(word.meaning)}</span>
        <span class="wrong-last">${escapeHTML(entry.lastAnswer || "—")}</span>
        <span>${escapeHTML(entry.due)} · ${entry.count} 次</span>
        <button class="text-btn" data-retry-one="${word.id}">重练</button>
      </div>`;
  }).join("");
  $("#wrongList").innerHTML = header + rows;
}

function retryAllWrong() {
  const items = state.wrongBook.map((entry) => getWord(entry.wordId)).filter(Boolean);
  if (!items.length) {
    toast("错词本是空的");
    return;
  }
  startPractice(items, state.config.mode);
  toast(`开始重练 ${items.length} 个错词`);
}

/* ---------------- Import ---------------- */
const REVIEW_ROWS = [
  { word: "environment", pos: "n.", meaning: "环境", phonetic: "/ɪnˈvaɪrənmənt/", confidence: "0.98", low: false, suspect: false },
  { word: "volunteer", pos: "n.", meaning: "志愿者", phonetic: "/ˌvɒlənˈtɪə(r)/", confidence: "0.94", low: false, suspect: false },
  { word: "enviroment", pos: "n.", meaning: "环境", phonetic: "缺失", confidence: "0.42", low: true, suspect: true },
  { word: "protect", pos: "v.", meaning: "保护", phonetic: "/prəˈtekt/", confidence: "0.88", low: false, suspect: false }
];

function renderReviewRows() {
  $("#reviewRows").innerHTML = `
    <div class="review-row head"><span>单词</span><span>词性</span><span>释义 / 音标</span><span>置信度</span></div>
    ${REVIEW_ROWS.map((row, index) => `
      <div class="review-row" data-review-row="${index}">
        <strong class="${row.suspect ? "suspect" : ""}">${escapeHTML(row.word)}</strong>
        <span>${escapeHTML(row.pos)}</span>
        <span>${escapeHTML(row.meaning)}<br><small class="${row.suspect ? "suspect" : "muted"}">${escapeHTML(row.phonetic)}</small></span>
        <span><span class="confidence ${row.low ? "low" : ""}">${row.confidence}</span><button class="text-btn" data-confirm-row="${index}">确认</button></span>
      </div>`).join("")}`;
}

function simulateParsing(fileName) {
  const stage = $("#importUploadStage");
  stage.classList.remove("hidden");
  $("#importReviewStage").classList.add("hidden");
  stage.innerHTML = `
    <div class="panel" style="grid-column:1/-1; min-height:280px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center">
      <p class="eyebrow">PARSING PDF</p>
      <h2 style="margin:10px 0 8px">正在提取词条</h2>
      <p id="parseFile" class="muted" style="font-size:12px">${escapeHTML(fileName || "七年级词表.pdf")}</p>
      <div class="progress-track" style="width:min(420px,80%); margin:26px 0 10px"><span id="parseProgress" style="width:12%; transition:width 1.2s ease"></span></div>
      <p id="parseStage" class="muted" style="font-size:11px">检查文件与页面结构…</p>
      <p class="panel-note">原型演示：生产环境解析在后台异步运行，低置信度词条必须人工校对后发布。</p>
    </div>`;
  window.setTimeout(() => { $("#parseProgress").style.width = "58%"; $("#parseStage").textContent = "识别栏位、音标与词义…"; }, 350);
  window.setTimeout(() => { $("#parseProgress").style.width = "86%"; $("#parseStage").textContent = "生成草稿并计算置信度…"; }, 1050);
  window.setTimeout(() => {
    stage.classList.add("hidden");
    $("#importReviewStage").classList.remove("hidden");
    renderReviewRows();
    toast("解析完成：发现 1 条低置信度、1 条缺音标");
  }, 1900);
}

/* ---------------- Events ---------------- */
function bindNavigation() {
  document.addEventListener("click", (event) => {
    const viewTrigger = event.target.closest("[data-view]");
    if (viewTrigger && !viewTrigger.matches("input, select, textarea")) {
      event.preventDefault();
      if (viewTrigger.dataset.view === "result" && !state.result) {
        toast("先完成一组练习，才能看到结果页");
        return;
      }
      switchView(viewTrigger.dataset.view);
      return;
    }

    const goTrigger = event.target.closest("[data-go]");
    if (goTrigger) {
      event.preventDefault();
      if (goTrigger.dataset.go === "config") switchView("config");
      if (goTrigger.dataset.go === "practice") {
        if (state.session) switchView("practice");
        else startPractice();
      }
      return;
    }

    const modeQuick = event.target.closest("[data-mode-quick]");
    if (modeQuick) {
      state.config.mode = modeQuick.dataset.modeQuick;
      updateConfigUi();
      switchView("config");
      return;
    }

    const openWord = event.target.closest("[data-open-word]");
    if (openWord) {
      openWordDrawer(getWord(openWord.dataset.openWord));
      return;
    }

    const say = event.target.closest("[data-say]");
    if (say) {
      speak(say.dataset.say);
      return;
    }

    const retryOne = event.target.closest("[data-retry-one]");
    if (retryOne) {
      const word = getWord(retryOne.dataset.retryOne);
      if (word) startPractice([word], state.config.mode);
      return;
    }

    const openPractice = event.target.closest("[data-open-practice]");
    if (openPractice) {
      closeDrawer();
      const word = getWord(openPractice.dataset.openPractice);
      if (word) startPractice([word], "zh_to_en");
      return;
    }

    if (event.target.closest("[data-action='review-due']")) {
      retryAllWrong();
      return;
    }

    if (event.target.closest("[data-action='resume']")) {
      toast("原型演示：已恢复上次练习进度");
      startPractice();
    }
  });

  $$(".nav-item[data-view], .mobile-nav [data-view], .brand").forEach((item) => {
    // Main navigation is handled by the delegated data-view listener;
    // preventing the brand anchor default keeps the prototype self-contained.
    item.addEventListener("click", (event) => event.preventDefault());
  });
}

function bindWords() {
  $("#wordSearch").addEventListener("input", (event) => {
    state.filters.q = event.target.value;
    renderWords();
  });

  $$("[data-filter-unit]").forEach((button) => {
    button.addEventListener("click", () => {
      state.filters.unit = button.dataset.filterUnit;
      $$("[data-filter-unit]").forEach((item) => item.classList.toggle("active", item === button));
      renderWords();
    });
  });

  $$("[data-filter-theme]").forEach((input) => {
    input.addEventListener("change", () => {
      input.checked ? state.filters.themes.add(input.value) : state.filters.themes.delete(input.value);
      renderWords();
    });
  });
  $$("[data-filter-pos]").forEach((input) => {
    input.addEventListener("change", () => {
      input.checked ? state.filters.pos.add(input.value) : state.filters.pos.delete(input.value);
      renderWords();
    });
  });
  $$("[data-filter-status]").forEach((input) => {
    input.addEventListener("change", () => {
      input.checked ? state.filters.statuses.add(input.value) : state.filters.statuses.delete(input.value);
      renderWords();
    });
  });

  $("#wordTable").addEventListener("change", (event) => {
    const checkbox = event.target.closest("[data-word-check]");
    if (!checkbox) return;
    if (checkbox.checked) state.selected.add(checkbox.dataset.wordCheck);
    else state.selected.delete(checkbox.dataset.wordCheck);
    updateSelectionBar();
  });

  $("#selectAllWords").addEventListener("change", (event) => {
    const visible = getFilteredWords();
    visible.forEach((word) => {
      if (event.target.checked) state.selected.add(word.id);
      else state.selected.delete(word.id);
    });
    renderWords();
  });

  $("#clearSelection").addEventListener("click", () => {
    state.selected.clear();
    renderWords();
  });

  const clearAllFilters = () => {
    state.filters = { q: "", unit: "all", themes: new Set(), pos: new Set(), statuses: new Set() };
    state.selected.clear();
    $("#wordSearch").value = "";
    $$("[data-filter-theme], [data-filter-pos], [data-filter-status]").forEach((input) => { input.checked = false; });
    $$("[data-filter-unit]").forEach((button) => button.classList.toggle("active", button.dataset.filterUnit === "all"));
    renderWords();
  };
  $("#clearFilters").addEventListener("click", clearAllFilters);
  $("#emptyClear").addEventListener("click", clearAllFilters);
}

function bindConfig() {
  $$(".mode-card input[name='mode']").forEach((radio) => {
    radio.addEventListener("change", () => {
      state.config.mode = radio.value;
      updateConfigUi();
    });
  });
  $$("[data-size]").forEach((button) => {
    button.addEventListener("click", () => {
      state.config.size = Number(button.dataset.size);
      updateConfigUi();
    });
  });
  $$("[data-order]").forEach((button) => {
    button.addEventListener("click", () => {
      state.config.order = button.dataset.order;
      updateConfigUi();
    });
  });
  $$("[data-range]").forEach((button) => {
    button.addEventListener("click", () => {
      state.config.range = button.dataset.range;
      state.selected.clear();
      updateConfigUi();
    });
  });
  $("#hintToggle").addEventListener("change", (event) => {
    state.config.hint = event.target.checked;
    updateConfigUi();
  });
  $("#startPracticeBtn").addEventListener("click", () => startPractice());
}

function bindPractice() {
  $("#answerInput").addEventListener("input", (event) => {
    $("#submitAnswer").disabled = !event.target.value.trim();
  });

  $("#answerForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const answer = $("#answerInput").value.trim();
    if (!answer) return;
    if (state.session?.answered) {
      nextQuestion();
      return;
    }
    gradeAnswer(answer);
  });

  $("#nextBtn").addEventListener("click", nextQuestion);
  $("#hintBtn").addEventListener("click", useHint);
  $("#replayAudio").addEventListener("click", () => {
    const item = currentSessionItem();
    if (item) speak(item.word);
  });
  $("#exitPractice").addEventListener("click", () => {
    if (window.confirm("退出后本次已完成作答会保留，未完成的题目下次可继续。确定退出吗？")) {
      switchView("dashboard");
    }
  });

  document.addEventListener("keydown", (event) => {
    if (state.currentView !== "practice") return;
    if (event.key === "Enter" && state.session?.answered) {
      event.preventDefault();
      nextQuestion();
    }
  });
}

function bindResultAndWrong() {
  $("#retryWrongBtn").addEventListener("click", retryWrongWords);
  $("#retryAllWrong").addEventListener("click", retryAllWrong);
}

function bindImport() {
  $("#loadSamplePdf").addEventListener("click", () => simulateParsing("七年级词表 · 示例.pdf"));
  $("#pdfFile").addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (file) simulateParsing(file.name);
  });
  $("#publishDraft").addEventListener("click", () => {
    toast("原型到此为止：生产环境会继续进入重复与冲突处理");
  });
  $("#reviewRows").addEventListener("click", (event) => {
    const confirmButton = event.target.closest("[data-confirm-row]");
    if (!confirmButton) return;
    const row = confirmButton.closest(".review-row");
    row.style.opacity = "0.55";
    confirmButton.textContent = "已确认";
    confirmButton.disabled = true;
    toast("词条已确认（原型演示）");
  });
}

function bindShell() {
  $("#heroSound")?.addEventListener("click", () => speak("environment"));
  $("#closeDrawer").addEventListener("click", closeDrawer);
  $("#scrim").addEventListener("click", closeDrawer);
  $("#helpBtn").addEventListener("click", () => $("#helpDialog").showModal());
  $("#closeHelp").addEventListener("click", () => $("#helpDialog").close());
  $("#startTour").addEventListener("click", () => {
    $("#helpDialog").close();
    switchView("dashboard");
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeDrawer();
      if ($("#helpDialog").open) $("#helpDialog").close();
    }
  });
}

bindNavigation();
bindWords();
bindConfig();
bindPractice();
bindResultAndWrong();
bindImport();
bindShell();
renderWords();
renderConfigSummary();
updateConfigUi();
