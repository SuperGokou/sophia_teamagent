const agents = [
  {
    id: "planner",
    name: "Planner",
    model: "openai/gpt-oss-120b",
    role: "结构规划",
    detail: "拆分需求、列出文件清单、控制多模型输出顺序。",
    step: "Required checklist",
  },
  {
    id: "file",
    name: "File Agent",
    model: "deepseek-ai/deepseek-v4-pro",
    role: "法律草拟",
    detail: "生成长模板、条款、附件、签署页和缺项标记。",
    step: "Draft package",
  },
  {
    id: "browser",
    name: "Browser Agent",
    model: "nvidia/nemotron-3-super-120b-a12b",
    role: "检索核验",
    detail: "对照本地 RAG、SQLite FTS5、引用依据和版本日期。",
    step: "Citation check",
  },
  {
    id: "reviewer",
    name: "Reviewer",
    model: "openai/gpt-oss-120b",
    role: "最终审核",
    detail: "最终质量门：完整性、内部一致性、引用支持、版式和律师复核风险。",
    step: "Quality gate",
  },
];

const timeline = ["需求录入", "结构规划", "法律草拟", "引用核验", "最终审核", "Word / Google Doc"];

const marketplaceSkills = [
  {
    title: "frontend-design",
    desc: "帮你做更耐看、更有记忆点的页面",
    source: "Claude",
    count: "7.6万人添加",
    icon: "🧩",
    category: "office",
  },
  {
    title: "brainstorming",
    desc: "把模糊想法整理成清晰方案和执行路径",
    source: "GitHub",
    count: "6.8万人添加",
    icon: "💡",
    category: "creative",
  },
  {
    title: "humanizer",
    desc: "把生硬文案改得更自然、更像真人写作",
    source: "SkillHub",
    count: "3.8万人添加",
    icon: "🖋️",
    category: "office",
  },
  {
    title: "legal-cite-checker",
    desc: "检查法条引用、版本日期和来源可信度",
    source: "Local",
    count: "3.7万人添加",
    icon: "⚖️",
    category: "pro",
  },
  {
    title: "docx-assembler",
    desc: "把条款、附件、签署页装配成 Word 文档",
    source: "Sophia",
    count: "3.4万人添加",
    icon: "📄",
    category: "office",
  },
  {
    title: "multi-search-engine",
    desc: "聚合多个检索源，统一做摘要和去重",
    source: "ClawHub",
    count: "3.3万人添加",
    icon: "🔎",
    category: "system",
  },
  {
    title: "UI/UX Pro Max",
    desc: "为当前界面提供设计规范和可落地代码",
    source: "ClawHub",
    count: "3.2万人添加",
    icon: "🪟",
    category: "office",
  },
  {
    title: "skill-creator",
    desc: "快速创建和打包自定义 Skill",
    source: "Claude",
    count: "3万人添加",
    icon: "💍",
    category: "system",
  },
  {
    title: "legal-rag-builder",
    desc: "构建 SQLite、FTS5、向量检索和引用校验",
    source: "Local",
    count: "2.8万人添加",
    icon: "🧬",
    category: "pro",
  },
  {
    title: "Find Skills",
    desc: "根据你的需求查询全网，用已有 skill 完成任务",
    source: "GitHub",
    count: "2.7万人添加",
    icon: "🧪",
    category: "system",
  },
  {
    title: "business-writing",
    desc: "撰写商务邮件、报告、合同摘要和备忘录",
    source: "ClawHub",
    count: "1.9万人添加",
    icon: "💼",
    category: "office",
  },
  {
    title: "Deep Research Skill",
    desc: "系统化多角度搜索，产出高质量研究结论",
    source: "GitHub",
    count: "1.7万人添加",
    icon: "🧭",
    category: "pro",
  },
];

const agentList = document.querySelector("#agentList");
const timelineList = document.querySelector("#timeline");
const appShell = document.querySelector(".app-shell");
const officeView = document.querySelector(".office");
const inspectorView = document.querySelector(".inspector");
const officeStage = document.querySelector("#officeStage");
const runButton = document.querySelector("#runButton");
const automationButton = document.querySelector("#automationButton");
const skillMarketButton = document.querySelector("#skillMarketButton");
const officeButton = document.querySelector("#officeButton");
const exportButton = document.querySelector("#exportButton");
const runStatus = document.querySelector("#runStatus");
const runningCount = document.querySelector("#runningCount");
const doneCount = document.querySelector("#doneCount");
const totalCount = document.querySelector("#totalCount");
const tokenUsed = document.querySelector("#tokenUsed");
const tokenSaved = document.querySelector("#tokenSaved");
const tokenUsedNote = document.querySelector("#tokenUsedNote");
const tokenSavedNote = document.querySelector("#tokenSavedNote");
const progressValue = document.querySelector("#progressValue");
const progressBar = document.querySelector("#progressBar");
const conversationTokenLabel = document.querySelector("#conversationTokenLabel");
const briefInput = document.querySelector("#briefInput");
const googleDocInput = document.querySelector("#googleDocInput");
const googleDocCheckButton = document.querySelector("#googleDocCheckButton");
const googleDocStatus = document.querySelector("#googleDocStatus");
const openGoogleDocButton = document.querySelector("#openGoogleDocButton");
const chromeMonitorButton = document.querySelector("#chromeMonitorButton");
const downloadDocxButton = document.querySelector("#downloadDocxButton");
const bridgeStatus = document.querySelector("#bridgeStatus");
const generateLegalButton = document.querySelector("#generateLegalButton");
const loginButton = document.querySelector("#loginButton");
const loginPanel = document.querySelector("#loginPanel");
const conversationEntry = document.querySelector("#conversationEntry");
const conversationRow = document.querySelector("#conversationRow");
const conversationDelete = document.querySelector("#conversationDelete");
const conversationOpenCard = document.querySelector("#conversationOpenCard");
const historyEntry = document.querySelector("#historyEntry");
const historyItem = document.querySelector("#historyItem");
const historyDelete = document.querySelector("#historyDelete");
const automationPage = document.querySelector("#automationPage");
const automationEmpty = document.querySelector("#automationEmpty");
const automationActive = document.querySelector("#automationActive");
const automationCreateButtons = document.querySelectorAll("#automationCreateButton, #automationCreateAnother");
const automationCountLabel = document.querySelector("#automationCountLabel");
const automationTaskList = document.querySelector("#automationTaskList");
const automationComposer = document.querySelector("#automationComposer");
const automationForm = document.querySelector("#automationForm");
const automationComposerClose = document.querySelector("#automationComposerClose");
const automationCancel = document.querySelector("#automationCancel");
const automationTaskTitle = document.querySelector("#automationTaskTitle");
const automationWorkflow = document.querySelector("#automationWorkflow");
const automationFrequency = document.querySelector("#automationFrequency");
const automationTime = document.querySelector("#automationTime");
const automationInstruction = document.querySelector("#automationInstruction");
const automationDocLink = document.querySelector("#automationDocLink");
const automationRequireReview = document.querySelector("#automationRequireReview");
const automationFormStatus = document.querySelector("#automationFormStatus");
const skillsPage = document.querySelector("#skillsPage");
const skillLibraryView = document.querySelector("#skillLibraryView");
const mySkillsView = document.querySelector("#mySkillsView");
const skillGrid = document.querySelector("#skillGrid");
const skillSearchInput = document.querySelector("#skillSearchInput");
const mySkillsButton = document.querySelector("#mySkillsButton");
const skillBackButton = document.querySelector("#skillBackButton");
const importSkillButton = document.querySelector("#importSkillButton");
const mySkillsEmpty = document.querySelector("#mySkillsEmpty");

let activeIndex = 0;
let runTimer;
let conversationDeleted = false;
let activeSkillFilter = "all";
let currentRunTokens = 0;
let automationTasks = [];
const conversationDeletedKey = "sophia.conversation.deleted";
const tokenLedgerKey = "sophia.tokenLedger.v1";
const currentRunTokenKey = "sophia.currentRunTokens.v1";
const automationTasksKey = "sophia.automation.tasks.v1";
const chromeBridgeRequestKey = "sophia.chromeDocBridge.v1";
const dailyTokenLimit = 10000000;
const tokenEstimates = {
  planner: { used: 5200, saved: 680 },
  file: { used: 15400, saved: 1200 },
  browser: { used: 7800, saved: 2300 },
  reviewer: { used: 5199, saved: 1580 },
};
const localDocxTokenEstimate = { used: 0, saved: 4200 };
const automationTokenEstimate = { used: 2400, saved: 760 };
const automationWorkflows = {
  "legal-review": "法律文书复核",
  "google-doc-layout": "Google Doc 法律版式整理",
  "rag-refresh": "法律知识库增量更新",
  "word-export": "Word 导出质量检查",
};
const automationFrequencies = {
  daily: "每天",
  weekly: "每周一",
  workday: "工作日",
  manual: "仅手动",
};
const tokenNumberFormatter = new Intl.NumberFormat("en-US");

function todayKey() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function emptyTokenLedger() {
  return {
    date: todayKey(),
    used: 0,
    saved: 0,
    entries: [],
  };
}

function readTokenLedger() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(tokenLedgerKey) || "null");
    if (!parsed || parsed.date !== todayKey()) {
      return emptyTokenLedger();
    }
    return {
      date: parsed.date,
      used: Number(parsed.used) || 0,
      saved: Number(parsed.saved) || 0,
      entries: Array.isArray(parsed.entries) ? parsed.entries : [],
    };
  } catch {
    return emptyTokenLedger();
  }
}

function writeTokenLedger(ledger) {
  try {
    window.localStorage.setItem(tokenLedgerKey, JSON.stringify(ledger));
  } catch {
    // Token display still works for the current session when storage is unavailable.
  }
}

function readCurrentRunTokens() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(currentRunTokenKey) || "null");
    if (!parsed || parsed.date !== todayKey()) {
      return 0;
    }
    return Number(parsed.tokens) || 0;
  } catch {
    return 0;
  }
}

function writeCurrentRunTokens(tokens) {
  try {
    window.localStorage.setItem(
      currentRunTokenKey,
      JSON.stringify({ date: todayKey(), tokens }),
    );
  } catch {
    // The top-level daily token ledger is enough when per-run storage is unavailable.
  }
}

function formatTokenCount(value) {
  return tokenNumberFormatter.format(Math.max(0, Math.round(value)));
}

function updateTokenDisplay(ledger = readTokenLedger()) {
  tokenUsed.textContent = formatTokenCount(ledger.used);
  tokenSaved.textContent = formatTokenCount(ledger.saved);
  const usedPercent = ledger.used
    ? Math.max(1, Math.min(100, Math.round((ledger.used / dailyTokenLimit) * 100)))
    : 0;
  tokenUsed.closest("article").style.setProperty("--token-progress", `${usedPercent}%`);
  const savedProgress = ledger.used ? Math.min(100, Math.round((ledger.saved / ledger.used) * 100)) : 0;
  tokenSaved.closest("article").style.setProperty("--token-progress", `${savedProgress}%`);
  tokenUsedNote.textContent = `${ledger.entries.length} 条记录 · 今日累计 Token`;
  tokenSavedNote.textContent = savedProgress
    ? `缓存与本地复用节省 ${savedProgress}%`
    : "缓存与本地复用节省";
  conversationTokenLabel.textContent = `累计Token消耗${formatTokenCount(currentRunTokens)}`;
}

function addTokenRecord(agent) {
  const estimate = tokenEstimates[agent.id] || { used: 0, saved: 0 };
  const ledger = readTokenLedger();
  const entry = {
    at: new Date().toISOString(),
    conversation: summarizeBrief(),
    agent: agent.name,
    model: agent.model,
    used: estimate.used,
    saved: estimate.saved,
  };
  const nextLedger = {
    ...ledger,
    used: ledger.used + estimate.used,
    saved: ledger.saved + estimate.saved,
    entries: [...ledger.entries, entry].slice(-80),
  };
  currentRunTokens += estimate.used;
  writeCurrentRunTokens(currentRunTokens);
  writeTokenLedger(nextLedger);
  updateTokenDisplay(nextLedger);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => (
    {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]
  ));
}

function createAutomationId() {
  return `task-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function readAutomationTasks() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(automationTasksKey) || "[]");
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .map((task) => ({
        id: String(task.id || createAutomationId()),
        title: String(task.title || "").trim(),
        workflow: automationWorkflows[task.workflow] ? task.workflow : "legal-review",
        frequency: automationFrequencies[task.frequency] ? task.frequency : "daily",
        time: /^\d{2}:\d{2}$/.test(task.time || "") ? task.time : "09:00",
        instruction: String(task.instruction || "").trim(),
        docUrl: String(task.docUrl || "").trim(),
        requireReview: task.requireReview !== false,
        enabled: task.enabled !== false,
        lastRunAt: task.lastRunAt || "",
        createdAt: task.createdAt || new Date().toISOString(),
      }))
      .filter((task) => task.title && task.instruction);
  } catch {
    return [];
  }
}

function writeAutomationTasks() {
  try {
    window.localStorage.setItem(automationTasksKey, JSON.stringify(automationTasks));
  } catch {
    setAutomationFormStatus("warn", "当前浏览器无法持久保存，但任务已在本次会话中启用。");
  }
}

function automationScheduleLabel(task) {
  if (task.frequency === "manual") {
    return "仅手动触发";
  }
  return `${automationFrequencies[task.frequency]} ${task.time || "09:00"}`;
}

function automationLastRunLabel(task) {
  if (!task.lastRunAt) {
    return "尚未运行";
  }
  const date = new Date(task.lastRunAt);
  if (Number.isNaN(date.getTime())) {
    return "尚未运行";
  }
  return `上次 ${date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}`;
}

function setAutomationFormStatus(kind, message) {
  automationFormStatus.classList.remove("is-ok", "is-warn", "is-error");
  if (kind) {
    automationFormStatus.classList.add(`is-${kind}`);
  }
  automationFormStatus.textContent = message || "";
}

function renderAutomationTasks() {
  const hasTasks = automationTasks.length > 0;
  const enabledCount = automationTasks.filter((task) => task.enabled).length;

  automationEmpty.hidden = hasTasks;
  automationActive.hidden = !hasTasks;
  automationCountLabel.textContent = `${enabledCount} 个启用 / ${automationTasks.length} 个总计`;

  if (!hasTasks) {
    automationTaskList.innerHTML = "";
    return;
  }

  automationTaskList.innerHTML = automationTasks
    .map((task) => {
      const status = task.enabled ? "已启用" : "已暂停";
      const reviewLabel = task.requireReview ? "Reviewer 最终审核" : "无最终审核";
      const docLabel = task.docUrl ? "已绑定 Google Doc" : "未绑定 Google Doc";

      return `
        <article class="automation-task-card ${task.enabled ? "" : "is-paused"}" data-automation-id="${escapeHtml(task.id)}">
          <header>
            <div>
              <span>${status}</span>
              <strong>${escapeHtml(task.title)}</strong>
            </div>
            <em>${escapeHtml(automationWorkflows[task.workflow])}</em>
          </header>
          <p>${escapeHtml(task.instruction)}</p>
          <div class="automation-task-meta">
            <span>${escapeHtml(automationScheduleLabel(task))}</span>
            <span>${escapeHtml(reviewLabel)}</span>
            <span>${escapeHtml(docLabel)}</span>
            <span>${escapeHtml(automationLastRunLabel(task))}</span>
          </div>
          <footer>
            <button type="button" data-automation-action="run" data-automation-id="${escapeHtml(task.id)}">运行一次</button>
            <button type="button" data-automation-action="toggle" data-automation-id="${escapeHtml(task.id)}">${task.enabled ? "暂停" : "启用"}</button>
            <button class="is-danger" type="button" data-automation-action="delete" data-automation-id="${escapeHtml(task.id)}">删除</button>
          </footer>
        </article>
      `;
    })
    .join("");
}

function openAutomationComposer() {
  automationForm.reset();
  automationTaskTitle.value = automationTasks.length ? "" : "公司资料定时复核";
  automationWorkflow.value = "legal-review";
  automationFrequency.value = "daily";
  automationTime.value = "09:00";
  automationInstruction.value = automationTasks.length
    ? ""
    : "自动检查文件包、引用依据、Word 导出状态和 Google Doc 权限，最后由 Reviewer 输出风险提示。";
  automationRequireReview.checked = true;
  setAutomationFormStatus(
    "warn",
    "Google Doc 链接会先检查格式；真正运行时还需要后端确认 Editor 权限。",
  );
  automationComposer.hidden = false;
  window.requestAnimationFrame(() => automationTaskTitle.focus());
}

function closeAutomationComposer() {
  automationComposer.hidden = true;
}

function validateAutomationForm() {
  const title = automationTaskTitle.value.trim();
  const instruction = automationInstruction.value.trim();
  const docUrl = automationDocLink.value.trim();

  if (!title || !instruction) {
    setAutomationFormStatus("error", "请填写任务名称和执行内容。");
    return false;
  }

  if (docUrl) {
    const documentId = extractGoogleDocIdFromUrl(docUrl);
    const hasEditPath = /\/edit(?:[?#]|$)/.test(docUrl);
    if (!documentId || !hasEditPath) {
      setAutomationFormStatus("error", "Google Doc 必须使用 docs.google.com/document/d/.../edit 编辑链接。");
      automationDocLink.focus();
      return false;
    }
  }

  if (automationWorkflow.value === "google-doc-layout" && !docUrl) {
    setAutomationFormStatus("error", "Google Doc 法律版式整理任务需要填写可编辑文档链接。");
    automationDocLink.focus();
    return false;
  }

  return true;
}

function handleAutomationSubmit(event) {
  event.preventDefault();
  if (!validateAutomationForm()) {
    return;
  }

  const task = {
    id: createAutomationId(),
    title: automationTaskTitle.value.trim(),
    workflow: automationWorkflow.value,
    frequency: automationFrequency.value,
    time: automationTime.value || "09:00",
    instruction: automationInstruction.value.trim(),
    docUrl: automationDocLink.value.trim(),
    requireReview: automationRequireReview.checked,
    enabled: true,
    lastRunAt: "",
    createdAt: new Date().toISOString(),
  };

  automationTasks = [task, ...automationTasks];
  writeAutomationTasks();
  renderAutomationTasks();
  closeAutomationComposer();
}

function addAutomationTokenRecord(task) {
  const ledger = readTokenLedger();
  const entry = {
    at: new Date().toISOString(),
    conversation: task.title,
    agent: "Automation Scheduler",
    model: automationWorkflows[task.workflow],
    used: automationTokenEstimate.used,
    saved: automationTokenEstimate.saved,
  };
  const nextLedger = {
    ...ledger,
    used: ledger.used + automationTokenEstimate.used,
    saved: ledger.saved + automationTokenEstimate.saved,
    entries: [...ledger.entries, entry].slice(-80),
  };
  writeTokenLedger(nextLedger);
  updateTokenDisplay(nextLedger);
}

function addLocalDocxTokenRecord(fileName) {
  const ledger = readTokenLedger();
  const entry = {
    at: new Date().toISOString(),
    conversation: fileName,
    agent: "Local DOCX Writer",
    model: "browser-local",
    used: localDocxTokenEstimate.used,
    saved: localDocxTokenEstimate.saved,
  };
  const nextLedger = {
    ...ledger,
    used: ledger.used + localDocxTokenEstimate.used,
    saved: ledger.saved + localDocxTokenEstimate.saved,
    entries: [...ledger.entries, entry].slice(-80),
  };
  writeTokenLedger(nextLedger);
  updateTokenDisplay(nextLedger);
}

function handleAutomationTaskAction(event) {
  const actionButton = event.target.closest("[data-automation-action]");
  if (!actionButton) {
    return;
  }

  const taskId = actionButton.dataset.automationId;
  const task = automationTasks.find((item) => item.id === taskId);
  if (!task) {
    return;
  }

  if (actionButton.dataset.automationAction === "delete") {
    automationTasks = automationTasks.filter((item) => item.id !== taskId);
  }

  if (actionButton.dataset.automationAction === "toggle") {
    task.enabled = !task.enabled;
  }

  if (actionButton.dataset.automationAction === "run") {
    task.enabled = true;
    task.lastRunAt = new Date().toISOString();
    addAutomationTokenRecord(task);
  }

  writeAutomationTasks();
  renderAutomationTasks();
}

function readConversationDeleted() {
  try {
    return window.localStorage.getItem(conversationDeletedKey) === "true";
  } catch {
    return false;
  }
}

function writeConversationDeleted(isDeleted) {
  try {
    if (isDeleted) {
      window.localStorage.setItem(conversationDeletedKey, "true");
      return;
    }
    window.localStorage.removeItem(conversationDeletedKey);
  } catch {
    // Ignore storage failures in private or restricted browser modes.
  }
}

function activeAgent() {
  return agents[activeIndex] || agents[0];
}

function setProgress(value) {
  const clamped = Math.max(0, Math.min(100, value));
  progressValue.textContent = `${clamped}%`;
  progressBar.style.width = `${clamped}%`;
}

function extractGoogleDocIdFromUrl(value) {
  const match = value.trim().match(/^https?:\/\/docs\.google\.com\/document\/d\/([A-Za-z0-9_-]+)/);
  return match ? match[1] : "";
}

function isGoogleDocEditLink(value) {
  return Boolean(extractGoogleDocIdFromUrl(value)) && /\/edit(?:[?#]|$)/.test(value.trim());
}

function setGoogleDocStatus(kind, message) {
  googleDocStatus.classList.remove("is-ok", "is-warn", "is-error");
  if (kind) {
    googleDocStatus.classList.add(`is-${kind}`);
  }
  googleDocStatus.textContent = message;
}

function checkGoogleDocLink() {
  const value = googleDocInput.value.trim();
  if (!value) {
    setGoogleDocStatus(
      "warn",
      "未提供 Google Doc。将先生成 Word；粘贴编辑链接后可自动排版 Google Doc。",
    );
    return true;
  }

  const documentId = extractGoogleDocIdFromUrl(value);
  if (!documentId || !isGoogleDocEditLink(value)) {
    setGoogleDocStatus("error", "请粘贴 docs.google.com/document/d/.../edit 格式的 Google Doc 链接。");
    googleDocInput.focus();
    return false;
  }

  setGoogleDocStatus(
    "ok",
    `链接格式正确。后端会校验 ${documentId} 是否具备 Editor 权限；无权限时会提示开放编辑权限。`,
  );
  return true;
}

function setBridgeStatus(kind, message) {
  bridgeStatus.classList.remove("is-ok", "is-warn", "is-error");
  if (kind) {
    bridgeStatus.classList.add(`is-${kind}`);
  }
  bridgeStatus.textContent = message;
}

function openGoogleDocLink({ monitor = false } = {}) {
  if (!checkGoogleDocLink()) {
    return false;
  }

  const docUrl = googleDocInput.value.trim();
  const openedWindow = window.open(docUrl, "_blank", "noopener,noreferrer");

  if (monitor) {
    writeChromeBridgeRequest(docUrl);
    if (openedWindow) {
      setBridgeStatus(
        "ok",
        "已打开 Google Doc，并创建 Chrome 接管请求；插件连接后可检查 Editor 权限并执行法律版式整理。",
      );
    } else {
      setBridgeStatus("warn", "已创建 Chrome 接管请求，但浏览器拦截了新标签；请点“打开链接”。");
    }
  } else {
    setBridgeStatus(
      openedWindow ? "ok" : "warn",
      openedWindow
        ? "已在新标签打开 Google Doc。请确认右上角 Share 里当前账号是 Editor。"
        : "浏览器拦截了新标签；请允许弹窗，或手动打开这个 Google Doc。",
    );
  }

  return true;
}

function writeChromeBridgeRequest(docUrl) {
  const request = {
    mode: "google-doc-legal-layout",
    docUrl,
    documentId: extractGoogleDocIdFromUrl(docUrl),
    brief: briefInput.value.trim(),
    requestedAt: new Date().toISOString(),
    layout: {
      margins: "1 inch",
      font: "Times New Roman",
      fontSize: "11 pt",
      lineSpacing: "115%",
      finalReviewer: true,
    },
  };

  try {
    window.localStorage.setItem(chromeBridgeRequestKey, JSON.stringify(request));
  } catch {
    setBridgeStatus("warn", "Google Doc 已打开，但当前浏览器不允许保存 Chrome 接管请求。");
  }
}

function startGoogleDocHandoffForRun() {
  const docUrl = googleDocInput.value.trim();
  if (!docUrl) {
    setBridgeStatus("warn", "未填写 Google Doc 链接。本次只生成本地任务状态，可点“本地 DOCX”下载 Word。");
    return;
  }

  writeChromeBridgeRequest(docUrl);
  const openedWindow = window.open(docUrl, "_blank", "noopener,noreferrer");
  setBridgeStatus(
    openedWindow ? "ok" : "warn",
    openedWindow
      ? "已打开 Google Doc，并创建 Chrome 接管请求；生成完成后插件/后端可继续写入和排版。"
      : "已创建 Chrome 接管请求，但新标签被拦截；Google Doc 不会自动显示变化，请点“打开链接”。",
  );
}

function summarizeBrief() {
  const firstContentLine = briefInput.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean);
  if (!firstContentLine) {
    return "法律文书生成任务";
  }
  return firstContentLine.length > 18 ? `${firstContentLine.slice(0, 18)}...` : firstContentLine;
}

function updateConversationTitle(title, subtitle) {
  conversationRow.querySelector("strong").textContent = title;
  historyItem.querySelector("strong").textContent = title;
  if (subtitle) {
    historyItem.querySelector("small").textContent = subtitle;
  }
}

function xmlEscape(value) {
  return String(value).replace(/[<>&"']/g, (char) => (
    {
      "<": "&lt;",
      ">": "&gt;",
      "&": "&amp;",
      '"': "&quot;",
      "'": "&apos;",
    }[char]
  ));
}

function textParagraph(text, style = "") {
  const styleXml = style ? `<w:pPr><w:pStyle w:val="${style}"/></w:pPr>` : "";
  return `<w:p>${styleXml}<w:r><w:t xml:space="preserve">${xmlEscape(text)}</w:t></w:r></w:p>`;
}

function buildLocalDocxDocumentXml(brief) {
  const lines = brief
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean);
  const briefParagraphs = lines.length
    ? lines.map((line) => textParagraph(line)).join("")
    : textParagraph("No brief content was provided.");
  const createdDate = new Date().toLocaleString("en-US");

  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    ${textParagraph("Eternal Presence AI", "Title")}
    ${textParagraph("Local Legal Document Draft", "Subtitle")}
    ${textParagraph("Drafting support output only. Review with qualified counsel before use.")}
    ${textParagraph(`Generated locally: ${createdDate}`)}
    ${textParagraph("Client Brief", "Heading1")}
    ${briefParagraphs}
    ${textParagraph("Agent Workflow", "Heading1")}
    ${textParagraph("Planner structures the checklist; Retriever verifies authority; Drafter assembles the package; Reviewer performs final quality checks.")}
    ${textParagraph("Google Doc Handoff", "Heading1")}
    ${textParagraph("If a Google Doc edit link is supplied, open it in Chrome and confirm the active account has Editor permission before applying automated layout changes.")}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>`;
}

function buildLocalDocxStylesXml() {
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:after="160" w:line="276" w:lineRule="auto"/></w:pPr>
    <w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:after="240"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="36"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:jc w:val="center"/><w:spacing w:after="360"/></w:pPr>
    <w:rPr><w:color w:val="666666"/><w:sz w:val="24"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr><w:spacing w:before="300" w:after="120"/></w:pPr>
    <w:rPr><w:b/><w:sz w:val="28"/></w:rPr>
  </w:style>
</w:styles>`;
}

function localDocxFiles(brief) {
  return [
    {
      name: "[Content_Types].xml",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>`,
    },
    {
      name: "_rels/.rels",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>`,
    },
    {
      name: "word/_rels/document.xml.rels",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>`,
    },
    {
      name: "word/document.xml",
      content: buildLocalDocxDocumentXml(brief),
    },
    {
      name: "word/styles.xml",
      content: buildLocalDocxStylesXml(),
    },
    {
      name: "docProps/core.xml",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Eternal Presence AI Legal Draft</dc:title>
  <dc:creator>Eternal Presence AI</dc:creator>
  <cp:lastModifiedBy>Eternal Presence AI</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">${new Date().toISOString()}</dcterms:created>
</cp:coreProperties>`,
    },
    {
      name: "docProps/app.xml",
      content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Eternal Presence AI</Application>
</Properties>`,
    },
  ];
}

let crcTable;

function getCrcTable() {
  if (crcTable) {
    return crcTable;
  }

  crcTable = new Uint32Array(256);
  for (let index = 0; index < 256; index += 1) {
    let value = index;
    for (let bit = 0; bit < 8; bit += 1) {
      value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    }
    crcTable[index] = value >>> 0;
  }
  return crcTable;
}

function crc32(bytes) {
  const table = getCrcTable();
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pushUint16(parts, value) {
  const bytes = new Uint8Array(2);
  new DataView(bytes.buffer).setUint16(0, value, true);
  parts.push(bytes);
}

function pushUint32(parts, value) {
  const bytes = new Uint8Array(4);
  new DataView(bytes.buffer).setUint32(0, value >>> 0, true);
  parts.push(bytes);
}

function concatBytes(parts) {
  const total = parts.reduce((sum, part) => sum + part.length, 0);
  const output = new Uint8Array(total);
  let offset = 0;
  parts.forEach((part) => {
    output.set(part, offset);
    offset += part.length;
  });
  return output;
}

function dosTimestamp(date = new Date()) {
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
  const day = date.getDate();
  const month = date.getMonth() + 1;
  const year = Math.max(1980, date.getFullYear()) - 1980;
  return {
    time,
    date: (year << 9) | (month << 5) | day,
  };
}

function createZip(files) {
  const encoder = new TextEncoder();
  const timestamp = dosTimestamp();
  const localParts = [];
  const centralParts = [];
  let offset = 0;

  files.forEach((file) => {
    const nameBytes = encoder.encode(file.name);
    const dataBytes = typeof file.content === "string" ? encoder.encode(file.content) : file.content;
    const checksum = crc32(dataBytes);

    const localHeader = [];
    pushUint32(localHeader, 0x04034b50);
    pushUint16(localHeader, 20);
    pushUint16(localHeader, 0x0800);
    pushUint16(localHeader, 0);
    pushUint16(localHeader, timestamp.time);
    pushUint16(localHeader, timestamp.date);
    pushUint32(localHeader, checksum);
    pushUint32(localHeader, dataBytes.length);
    pushUint32(localHeader, dataBytes.length);
    pushUint16(localHeader, nameBytes.length);
    pushUint16(localHeader, 0);
    localHeader.push(nameBytes, dataBytes);
    const localBytes = concatBytes(localHeader);
    localParts.push(localBytes);

    const centralHeader = [];
    pushUint32(centralHeader, 0x02014b50);
    pushUint16(centralHeader, 20);
    pushUint16(centralHeader, 20);
    pushUint16(centralHeader, 0x0800);
    pushUint16(centralHeader, 0);
    pushUint16(centralHeader, timestamp.time);
    pushUint16(centralHeader, timestamp.date);
    pushUint32(centralHeader, checksum);
    pushUint32(centralHeader, dataBytes.length);
    pushUint32(centralHeader, dataBytes.length);
    pushUint16(centralHeader, nameBytes.length);
    pushUint16(centralHeader, 0);
    pushUint16(centralHeader, 0);
    pushUint16(centralHeader, 0);
    pushUint16(centralHeader, 0);
    pushUint32(centralHeader, 0);
    pushUint32(centralHeader, offset);
    centralHeader.push(nameBytes);
    centralParts.push(concatBytes(centralHeader));
    offset += localBytes.length;
  });

  const centralDirectory = concatBytes(centralParts);
  const endRecord = [];
  pushUint32(endRecord, 0x06054b50);
  pushUint16(endRecord, 0);
  pushUint16(endRecord, 0);
  pushUint16(endRecord, files.length);
  pushUint16(endRecord, files.length);
  pushUint32(endRecord, centralDirectory.length);
  pushUint32(endRecord, offset);
  pushUint16(endRecord, 0);

  return concatBytes([...localParts, centralDirectory, concatBytes(endRecord)]);
}

function createLocalDocxBlob(brief) {
  const zipBytes = createZip(localDocxFiles(brief));
  return new Blob([zipBytes], {
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  });
}

function safeFileName(value) {
  const base = value
    .replace(/[^A-Za-z0-9\u4e00-\u9fa5_-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
  return base || "legal-document";
}

function downloadLocalDocx() {
  const brief = briefInput.value.trim();
  if (!brief) {
    setGoogleDocStatus("error", "请先填写法律文书需求，再生成本地 DOCX。");
    briefInput.focus();
    return;
  }

  const fileName = `${safeFileName(summarizeBrief())}.docx`;
  const blob = createLocalDocxBlob(brief);
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(link.href);
  addLocalDocxTokenRecord(fileName);
  setBridgeStatus("ok", `已生成本地 Word 文档：${fileName}`);
}

function renderSkills() {
  const query = skillSearchInput.value.trim().toLowerCase();
  const skills = marketplaceSkills.filter((skill) => {
    const matchesCategory = activeSkillFilter === "all" || skill.category === activeSkillFilter;
    const matchesQuery = !query || `${skill.title} ${skill.desc} ${skill.source}`.toLowerCase().includes(query);
    return matchesCategory && matchesQuery;
  });

  if (!skills.length) {
    skillGrid.innerHTML = `
      <div class="skill-no-results">
        <strong>没有找到匹配的 Skill</strong>
        <span>换个关键词或切回全部分类。</span>
      </div>
    `;
    return;
  }

  skillGrid.innerHTML = skills
    .map(
      (skill) => `
        <button class="skill-card" type="button" data-category="${skill.category}">
          <span class="skill-icon" aria-hidden="true">${skill.icon}</span>
          <span class="skill-copy">
            <strong>${skill.title}</strong>
            <span>${skill.desc}</span>
            <em>${skill.source} | ${skill.count}</em>
          </span>
        </button>
      `,
    )
    .join("");
}

function showOfficeView() {
  appShell.classList.remove("is-skills-mode");
  officeView.hidden = false;
  inspectorView.hidden = false;
  automationPage.hidden = true;
  skillsPage.hidden = true;
  automationButton.classList.remove("is-active");
  skillMarketButton.classList.remove("is-active");
  officeButton.classList.add("is-active");
}

function showSkillLibrary() {
  skillLibraryView.hidden = false;
  mySkillsView.hidden = true;
  renderSkills();
}

function showMySkillsView() {
  skillLibraryView.hidden = true;
  mySkillsView.hidden = false;
}

function showSkillsPage() {
  window.clearInterval(runTimer);
  officeStage.classList.remove("is-running");
  appShell.classList.add("is-skills-mode");
  officeView.hidden = true;
  inspectorView.hidden = true;
  automationPage.hidden = true;
  skillsPage.hidden = false;
  officeButton.classList.remove("is-active");
  automationButton.classList.remove("is-active");
  skillMarketButton.classList.add("is-active");
  showSkillLibrary();
}

function showAutomationPage() {
  window.clearInterval(runTimer);
  officeStage.classList.remove("is-running");
  appShell.classList.add("is-skills-mode");
  officeView.hidden = true;
  inspectorView.hidden = true;
  skillsPage.hidden = true;
  automationPage.hidden = false;
  officeButton.classList.remove("is-active");
  skillMarketButton.classList.remove("is-active");
  automationButton.classList.add("is-active");
}

function createAutomationTask(event) {
  const sourceButton = event.currentTarget;
  openAutomationComposer();
  sourceButton.blur();
}

function renderAgents() {
  agentList.innerHTML = agents
    .map((agent, index) => {
      const state = index < activeIndex ? "已完成" : index === activeIndex ? "进行中" : "等待";
      return `
        <article class="agent-card ${index === activeIndex ? "is-current" : ""}">
          <div>
            <strong>${agent.name}</strong>
            <span>${agent.role}</span>
          </div>
          <small>${agent.model}</small>
          <p>${agent.detail}</p>
          <em>${state}</em>
        </article>
      `;
    })
    .join("");
}

function renderTimeline(progressIndex = 1) {
  timelineList.innerHTML = timeline
    .map((label, index) => {
      const state = index < progressIndex ? "is-done" : index === progressIndex ? "is-active" : "";
      return `<li class="${state}"><i></i><span>${label}</span></li>`;
    })
    .join("");
}

function activate(agentId) {
  const index = agents.findIndex((agent) => agent.id === agentId);
  activeIndex = index < 0 ? 0 : index;
  const current = activeAgent();

  document.querySelectorAll(".agent-node").forEach((node) => {
    const nodeIndex = agents.findIndex((agent) => agent.id === node.dataset.agent);
    node.classList.toggle("is-active", node.dataset.agent === current.id);
    node.classList.toggle("is-done", nodeIndex >= 0 && nodeIndex < activeIndex);
    node.classList.toggle("is-idle", nodeIndex > activeIndex);
  });

  officeStage.dataset.active = current.id;
  renderAgents();
  renderTimeline(Math.min(activeIndex + 1, timeline.length - 1));
}

function setConversationOpen(isOpen) {
  conversationRow.classList.toggle("is-open", isOpen);
  conversationRow.setAttribute("aria-expanded", String(isOpen));
  conversationOpenCard.hidden = !isOpen;
  historyItem.classList.toggle("is-open", isOpen);
}

function setConversationDeleted(isDeleted) {
  conversationDeleted = isDeleted;
  conversationEntry.hidden = isDeleted;
  historyEntry.hidden = isDeleted;
  historyItem.hidden = false;
  totalCount.textContent = isDeleted ? "0" : "1";

  if (isDeleted) {
    runningCount.textContent = "0";
    doneCount.textContent = "0";
    setConversationOpen(false);
  }
}

function restoreConversation() {
  writeConversationDeleted(false);
  setConversationDeleted(false);
}

function openConversation() {
  if (conversationDeleted) {
    return;
  }

  window.clearInterval(runTimer);
  officeStage.classList.remove("is-running");
  runningCount.textContent = "0";
  doneCount.textContent = "1";
  totalCount.textContent = "1";
  runStatus.textContent = "已打开";
  activate("reviewer");
  renderTimeline(timeline.length);
  setProgress(100);
  setConversationOpen(true);
}

function deleteConversation(event) {
  event.preventDefault();
  event.stopPropagation();
  window.clearInterval(runTimer);
  writeConversationDeleted(true);
  setConversationDeleted(true);
  currentRunTokens = 0;
  writeCurrentRunTokens(currentRunTokens);
  officeStage.classList.remove("is-running");
  activate("planner");
  setProgress(18);
  updateTokenDisplay();
}

document.querySelectorAll(".agent-node").forEach((node) => {
  node.addEventListener("click", () => {
    window.clearInterval(runTimer);
    officeStage.classList.remove("is-running");
    runStatus.textContent = "查看中";
    runningCount.textContent = "0";
    activate(node.dataset.agent);
    setProgress(18 + activeIndex * 18);
  });
});

function prepareNewConversation() {
  window.clearInterval(runTimer);
  showOfficeView();
  restoreConversation();
  setConversationOpen(false);
  currentRunTokens = 0;
  writeCurrentRunTokens(currentRunTokens);
  officeStage.classList.remove("is-running");
  runStatus.textContent = "待输入";
  runningCount.textContent = "0";
  doneCount.textContent = "0";
  totalCount.textContent = "1";
  activate("planner");
  setProgress(6);
  updateTokenDisplay();
  setGoogleDocStatus("warn", "请输入法律文书需求；如需写入 Google Doc，请先粘贴可编辑链接。");
  setBridgeStatus("warn", "有 Google Doc 链接时，多 Agent 生成会创建接管请求；真实写入需要 Chrome 插件或后端服务。");
  briefInput.focus();
}

function startLegalDraftRun() {
  window.clearInterval(runTimer);
  showOfficeView();
  restoreConversation();
  setConversationOpen(false);

  if (!briefInput.value.trim()) {
    setGoogleDocStatus("error", "请先填写需要生成或填写的法律文书内容。");
    briefInput.focus();
    return;
  }

  if (!checkGoogleDocLink()) {
    return;
  }

  startGoogleDocHandoffForRun();
  currentRunTokens = 0;
  writeCurrentRunTokens(currentRunTokens);
  updateTokenDisplay();
  updateConversationTitle(summarizeBrief(), "多 Agent 协作草拟中");
  officeStage.classList.add("is-running");
  runStatus.textContent = "进行中";
  runningCount.textContent = "1";
  doneCount.textContent = "0";
  totalCount.textContent = "1";

  let step = 0;
  let progress = 12;
  activate(agents[0].id);
  setProgress(progress);

  runTimer = window.setInterval(() => {
    step += 1;
    progress += 22;
    addTokenRecord(agents[step - 1]);
    setProgress(progress);

    if (step < agents.length) {
      activate(agents[step].id);
      return;
    }

    window.clearInterval(runTimer);
    officeStage.classList.remove("is-running");
    runStatus.textContent = "已完成";
    runningCount.textContent = "0";
    doneCount.textContent = "1";
    totalCount.textContent = "1";
    activeIndex = agents.length - 1;
    renderAgents();
    renderTimeline(timeline.length);
    setProgress(100);
    updateConversationTitle(summarizeBrief(), "Reviewer 审核完成");
    const hasGoogleDoc = Boolean(googleDocInput.value.trim());
    setGoogleDocStatus(
      "ok",
      hasGoogleDoc
        ? "最终 Reviewer 已完成质量门。Google Doc 接管请求已创建；需要 Chrome 插件或后端 OAuth 服务执行真实写入。"
        : "最终 Reviewer 已完成质量门。未提供 Google Doc，可下载本地 DOCX 交付。",
    );
    setBridgeStatus(
      hasGoogleDoc ? "warn" : "ok",
      hasGoogleDoc
        ? "如果 Google Doc 没有变化，说明 Chrome 接管插件或后端 Google Docs 服务尚未运行；可先点“本地 DOCX”。"
        : "可下载本地 DOCX 交付。",
    );
  }, 900);
}

runButton.addEventListener("click", prepareNewConversation);
generateLegalButton.addEventListener("click", startLegalDraftRun);
googleDocCheckButton.addEventListener("click", checkGoogleDocLink);
googleDocInput.addEventListener("change", checkGoogleDocLink);
openGoogleDocButton.addEventListener("click", () => openGoogleDocLink());
chromeMonitorButton.addEventListener("click", () => openGoogleDocLink({ monitor: true }));
downloadDocxButton.addEventListener("click", downloadLocalDocx);

exportButton.addEventListener("click", () => {
  const payload = {
    brief: briefInput.value,
    googleDocUrl: googleDocInput.value.trim(),
    tokenLedger: readTokenLedger(),
    activeAgent: activeAgent().name,
    agents: agents.map(({ id, model, role, step }) => ({ id, model, role, step })),
    exportedAt: new Date().toISOString(),
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "sophia-teamagent-brief.json";
  link.click();
  URL.revokeObjectURL(link.href);
});

conversationRow.addEventListener("click", openConversation);
historyItem.addEventListener("click", openConversation);
conversationDelete.addEventListener("click", deleteConversation);
historyDelete.addEventListener("click", deleteConversation);
automationButton.addEventListener("click", showAutomationPage);
automationCreateButtons.forEach((button) => {
  button.addEventListener("click", createAutomationTask);
});
automationForm.addEventListener("submit", handleAutomationSubmit);
automationComposerClose.addEventListener("click", closeAutomationComposer);
automationCancel.addEventListener("click", closeAutomationComposer);
automationTaskList.addEventListener("click", handleAutomationTaskAction);
skillMarketButton.addEventListener("click", showSkillsPage);
officeButton.addEventListener("click", showOfficeView);
mySkillsButton.addEventListener("click", showMySkillsView);
skillBackButton.addEventListener("click", showSkillLibrary);
skillSearchInput.addEventListener("input", renderSkills);

document.querySelectorAll("[data-skill-filter]").forEach((chip) => {
  chip.addEventListener("click", () => {
    activeSkillFilter = chip.dataset.skillFilter;
    document.querySelectorAll("[data-skill-filter]").forEach((item) => {
      item.classList.toggle("is-active", item === chip);
    });
    renderSkills();
  });
});

skillGrid.addEventListener("click", (event) => {
  const card = event.target.closest(".skill-card");
  if (!card) {
    return;
  }
  document.querySelectorAll(".skill-card").forEach((item) => {
    item.classList.toggle("is-selected", item === card);
  });
});

importSkillButton.addEventListener("click", () => {
  mySkillsEmpty.querySelector("p").textContent = "可以从 Git URL 或本地文件导入技能";
});

loginButton.addEventListener("click", () => {
  const isOpen = loginPanel.classList.toggle("is-open");
  loginButton.setAttribute("aria-expanded", String(isOpen));
});

loginPanel.addEventListener("submit", (event) => {
  event.preventDefault();
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") {
    return;
  }
  closeAutomationComposer();
  loginPanel.classList.remove("is-open");
  loginButton.setAttribute("aria-expanded", "false");
});

activate("planner");
setProgress(18);
currentRunTokens = readCurrentRunTokens();
automationTasks = readAutomationTasks();
renderAutomationTasks();
setConversationDeleted(readConversationDeleted());
if (conversationDeleted) {
  currentRunTokens = 0;
}
updateTokenDisplay();
renderSkills();
