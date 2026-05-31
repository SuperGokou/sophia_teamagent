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
    model: "qwen/qwen3-coder-480b-a35b-instruct",
    role: "文件装配",
    detail: "管理模板、DOCX 结构、附件和批量生成脚本。",
    step: "DOCX assembly",
  },
  {
    id: "browser",
    name: "Browser Agent",
    model: "minimaxai/minimax-m2.7",
    role: "检索核验",
    detail: "对照公开来源、法规引用、本地 RAG 和 Obsidian 索引。",
    step: "Citation check",
  },
  {
    id: "reviewer",
    name: "Reviewer",
    model: "google/gemma-3n-e2b-it",
    role: "格式复核",
    detail: "快速检查缺项、风险、格式和导出可读性。",
    step: "Word export",
  },
];

const timeline = ["公司资料", "清单规划", "模板草拟", "引用核验", "Word 导出"];

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
const progressValue = document.querySelector("#progressValue");
const progressBar = document.querySelector("#progressBar");
const briefInput = document.querySelector("#briefInput");
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
const automationSuggestions = document.querySelector(".automation-suggestions");
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
const conversationDeletedKey = "sophia.conversation.deleted";

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
  automationEmpty.hidden = true;
  automationActive.hidden = false;
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
  officeStage.classList.remove("is-running");
  activate("planner");
  setProgress(18);
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

runButton.addEventListener("click", () => {
  window.clearInterval(runTimer);
  showOfficeView();
  restoreConversation();
  setConversationOpen(false);
  officeStage.classList.add("is-running");
  runStatus.textContent = "进行中";
  runningCount.textContent = "1";
  doneCount.textContent = "0";

  let step = 0;
  let progress = 18;
  activate(agents[0].id);
  setProgress(progress);

  runTimer = window.setInterval(() => {
    step += 1;
    progress += 20;
    tokenUsed.textContent = String(Number(tokenUsed.textContent) + 8399);
    tokenSaved.textContent = String(Number(tokenSaved.textContent) + 1440);
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
  }, 900);
});

exportButton.addEventListener("click", () => {
  const payload = {
    brief: briefInput.value,
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
automationSuggestions.addEventListener("click", (event) => {
  const addButton = event.target.closest(".automation-card-foot button");
  if (!addButton) {
    return;
  }
  addButton.textContent = "已添加";
  addButton.classList.add("is-added");
  createAutomationTask({ currentTarget: addButton });
});
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
  loginPanel.classList.remove("is-open");
  loginButton.setAttribute("aria-expanded", "false");
});

activate("planner");
setProgress(18);
setConversationDeleted(readConversationDeleted());
renderSkills();
