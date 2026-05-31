const agents = [
  {
    id: "planner",
    name: "Planner",
    model: "openai/gpt-oss-120b",
    role: "结构规划",
    detail: "拆分任务、整理清单、控制输出顺序。",
    step: "Required checklist",
  },
  {
    id: "analyst",
    name: "Analyst",
    model: "minimaxai/minimax-m2.7",
    role: "风险分析",
    detail: "比较可选文件、合同风险、谈判取舍和市场标准。",
    step: "Optional checklist",
  },
  {
    id: "reasoner",
    name: "Reasoner",
    model: "nvidia/nemotron-3-super-120b-a12b",
    role: "深度推理",
    detail: "启用 thinking 预算，分析跨文档依赖和复核风险。",
    step: "Preparation materials",
  },
  {
    id: "drafter",
    name: "Drafter",
    model: "deepseek-ai/deepseek-v4-pro",
    role: "法律草拟",
    detail: "生成长模板、条款、附件和签署页。",
    step: "Required templates",
  },
  {
    id: "coder",
    name: "Coder",
    model: "qwen/qwen3-coder-480b-a35b-instruct",
    role: "自动化",
    detail: "保留给 schema、脚本、集成和批处理。",
    step: "DOCX assembly",
  },
  {
    id: "reviewer",
    name: "Reviewer",
    model: "google/gemma-3n-e2b-it",
    role: "复核",
    detail: "快速检查缺项、风险和格式问题。",
    step: "Word export",
  },
];

const timeline = [
  "公司资料",
  "Required checklist",
  "Optional checklist",
  "Preparation materials",
  "Required templates",
  "Word export",
];

const agentList = document.querySelector("#agentList");
const timelineList = document.querySelector("#timeline");
const activeAgentTitle = document.querySelector("#activeAgentTitle");
const currentStep = document.querySelector("#currentStep");
const nextAgent = document.querySelector("#nextAgent");
const runButton = document.querySelector("#runButton");
const exportButton = document.querySelector("#exportButton");
const runStatus = document.querySelector("#runStatus");
const tokenUsed = document.querySelector("#tokenUsed");
const tokenSaved = document.querySelector("#tokenSaved");
const progressValue = document.querySelector("#progressValue");
const progressCircle = document.querySelector("#progressCircle");
const briefInput = document.querySelector("#briefInput");
const officeStage = document.querySelector("#officeStage");

let activeIndex = 0;
let runInterval;

function activateAgent(agentId) {
  const index = agents.findIndex((agent) => agent.id === agentId);
  activeIndex = index < 0 ? 0 : index;
  const current = agents[activeIndex];
  const upcoming = agents[Math.min(activeIndex + 1, agents.length - 1)];

  document.querySelectorAll(".agent-node").forEach((node) => {
    const nodeIndex = agents.findIndex((agent) => agent.id === node.dataset.agent);
    node.classList.toggle("is-selected", node.dataset.agent === current.id);
    node.classList.toggle("is-done", nodeIndex >= 0 && nodeIndex < activeIndex);
    node.classList.toggle("is-waiting", nodeIndex > activeIndex);
  });

  officeStage.dataset.active = current.id;
  activeAgentTitle.textContent = `${current.name} 正在处理 ${current.role}`;
  currentStep.textContent = current.step;
  nextAgent.textContent = upcoming.id === current.id ? "Reviewer" : upcoming.name;
  renderAgents();
  renderTimeline(activeIndex + 1);
}

function renderAgents() {
  agentList.innerHTML = agents
    .map((agent, index) => {
      const state =
        index < activeIndex ? "已完成" : index === activeIndex ? "进行中" : "等待";
      return `
        <article class="agent-card ${index === activeIndex ? "is-active" : ""}">
          <div>
            <strong>${agent.name}</strong>
            <small>${agent.model}</small>
          </div>
          <span>${agent.role}</span>
          <p>${agent.detail}</p>
          <div class="agent-card-footer">
            <em>${state}</em>
            <b style="--fill:${index < activeIndex ? 100 : index === activeIndex ? 62 : 8}%"></b>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderTimeline(progressIndex = 1) {
  timelineList.innerHTML = timeline
    .map((label, index) => {
      const state =
        index < progressIndex ? "is-done" : index === progressIndex ? "is-active" : "";
      const note = index < progressIndex ? "完成" : index === progressIndex ? "进行中" : "等待";
      return `<li class="${state}"><i></i><strong>${label}</strong><span>${note}</span></li>`;
    })
    .join("");
}

function setProgress(value) {
  const clamped = Math.max(0, Math.min(100, value));
  progressValue.textContent = `${clamped}%`;
  progressCircle.style.strokeDashoffset = `${314 - (314 * clamped) / 100}`;
}

document.querySelectorAll(".agent-node").forEach((node) => {
  node.addEventListener("click", () => {
    window.clearInterval(runInterval);
    runStatus.textContent = "查看中";
    officeStage.classList.remove("is-running");
    activateAgent(node.dataset.agent);
    setProgress(18 + activeIndex * 14);
  });
});

document.querySelectorAll(".segmented button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".segmented button").forEach((item) => {
      item.classList.toggle("is-active", item === button);
    });
  });
});

runButton.addEventListener("click", () => {
  window.clearInterval(runInterval);
  runStatus.textContent = "运行中";
  officeStage.classList.add("is-running");
  let progress = 18;
  let step = 0;
  activateAgent(agents[step].id);

  runInterval = window.setInterval(() => {
    step += 1;
    progress += step === agents.length ? 12 : 14;
    tokenUsed.textContent = String(Number(tokenUsed.textContent) + 4218);
    tokenSaved.textContent = String(Number(tokenSaved.textContent) + 620);
    setProgress(progress);

    if (step < agents.length) {
      activateAgent(agents[step].id);
      return;
    }

    window.clearInterval(runInterval);
    officeStage.classList.remove("is-running");
    runStatus.textContent = "完成";
    activeIndex = agents.length - 1;
    renderAgents();
    renderTimeline(timeline.length);
    setProgress(100);
  }, 780);
});

exportButton.addEventListener("click", () => {
  const payload = {
    brief: briefInput.value,
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

activateAgent("planner");
setProgress(18);
