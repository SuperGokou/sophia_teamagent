const agents = [
  {
    id: "planner",
    name: "Planner",
    model: "openai/gpt-oss-120b",
    role: "结构规划",
    detail: "拆分任务、整理清单、控制输出顺序。",
  },
  {
    id: "drafter",
    name: "Drafter",
    model: "deepseek-ai/deepseek-v4-pro",
    role: "法律草拟",
    detail: "生成长模板、条款、附件和签署页。",
  },
  {
    id: "coder",
    name: "Coder",
    model: "qwen/qwen3-coder-480b-a35b-instruct",
    role: "自动化",
    detail: "保留给 schema、脚本、集成和批处理。",
  },
  {
    id: "reviewer",
    name: "Reviewer",
    model: "google/gemma-3n-e2b-it",
    role: "复核",
    detail: "快速检查缺项、风险和格式问题。",
  },
];

const timeline = [
  ["公司资料", "is-done"],
  ["Required checklist", "is-active"],
  ["Preparation materials", ""],
  ["Required templates", ""],
  ["Word export", ""],
];

const agentList = document.querySelector("#agentList");
const timelineList = document.querySelector("#timeline");
const activeAgentTitle = document.querySelector("#activeAgentTitle");
const runButton = document.querySelector("#runButton");
const exportButton = document.querySelector("#exportButton");
const runStatus = document.querySelector("#runStatus");
const tokenUsed = document.querySelector("#tokenUsed");
const tokenSaved = document.querySelector("#tokenSaved");
const progressValue = document.querySelector("#progressValue");
const progressCircle = document.querySelector("#progressCircle");
const briefInput = document.querySelector("#briefInput");

function renderAgents(selected = "planner") {
  agentList.innerHTML = agents
    .map(
      (agent) => `
        <article class="agent-card" data-agent-card="${agent.id}">
          <strong>${agent.name}</strong>
          <span>${agent.role}</span>
          <small>${agent.model}</small>
          <small>${agent.detail}</small>
        </article>
      `,
    )
    .join("");

  document.querySelectorAll(".agent-node").forEach((node) => {
    node.classList.toggle("is-selected", node.dataset.agent === selected);
  });

  const current = agents.find((agent) => agent.id === selected) || agents[0];
  activeAgentTitle.textContent = `${current.id} 正在处理 ${current.role}`;
}

function renderTimeline(progressIndex = 1) {
  timelineList.innerHTML = timeline
    .map(([label], index) => {
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
  node.addEventListener("click", () => renderAgents(node.dataset.agent));
});

document.querySelectorAll(".segmented button").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".segmented button").forEach((item) => {
      item.classList.toggle("is-active", item === button);
    });
  });
});

runButton.addEventListener("click", () => {
  runStatus.textContent = "运行中";
  let progress = 18;
  let step = 1;
  const sequence = ["planner", "planner", "drafter", "drafter", "reviewer"];
  const interval = window.setInterval(() => {
    progress += 14;
    step += 1;
    const agentId = sequence[Math.min(step - 1, sequence.length - 1)];
    renderAgents(agentId);
    renderTimeline(Math.min(step, timeline.length - 1));
    setProgress(progress);
    tokenUsed.textContent = String(Number(tokenUsed.textContent) + 4218);
    tokenSaved.textContent = String(Number(tokenSaved.textContent) + 620);

    if (progress >= 100) {
      window.clearInterval(interval);
      runStatus.textContent = "完成";
      renderTimeline(timeline.length);
      setProgress(100);
    }
  }, 620);
});

exportButton.addEventListener("click", () => {
  const payload = {
    brief: briefInput.value,
    agents: agents.map(({ id, model, role }) => ({ id, model, role })),
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

renderAgents();
renderTimeline();
setProgress(18);
