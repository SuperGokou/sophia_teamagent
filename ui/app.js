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

const agentList = document.querySelector("#agentList");
const timelineList = document.querySelector("#timeline");
const officeStage = document.querySelector("#officeStage");
const runButton = document.querySelector("#runButton");
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
const historyItem = document.querySelector("#historyItem");

let activeIndex = 0;
let runTimer;
let conversationDeleted = false;

function activeAgent() {
  return agents[activeIndex] || agents[0];
}

function setProgress(value) {
  const clamped = Math.max(0, Math.min(100, value));
  progressValue.textContent = `${clamped}%`;
  progressBar.style.width = `${clamped}%`;
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

function restoreConversation() {
  conversationDeleted = false;
  conversationEntry.hidden = false;
  historyItem.hidden = false;
  totalCount.textContent = "1";
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
  event.stopPropagation();
  window.clearInterval(runTimer);
  conversationDeleted = true;
  conversationEntry.hidden = true;
  historyItem.hidden = true;
  officeStage.classList.remove("is-running");
  runningCount.textContent = "0";
  doneCount.textContent = "0";
  totalCount.textContent = "0";
  setConversationOpen(false);
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
