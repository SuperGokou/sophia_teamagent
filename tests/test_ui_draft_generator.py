from __future__ import annotations

import json
import re
import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipIf(shutil.which("node") is None, "Node.js is required for UI generator tests.")
class UiDraftGeneratorTests(unittest.TestCase):
    def test_legal_draft_generator_uses_matter_specific_input(self) -> None:
        script = textwrap.dedent(
            r"""
            const fs = require("fs");
            const source = fs.readFileSync("ui/app.js", "utf8");
            const start = source.indexOf("function parseBriefFields");
            const end = source.indexOf("function completeDraftOutput");
            if (start < 0 || end < 0) {
              throw new Error("Could not locate the UI draft generator block.");
            }
            eval(source.slice(start, end));

            const cases = {
              nda: "Need an NDA for Alpha AI and Beta Labs. Mutual confidentiality, term 3 years, California law.",
              demand: "请生成一封律师函：客户欠款 50000 美元，合同违约，需要 10 天内付款。",
              corporate: "Company legal name: Example AI Inc\nDelaware file number: 123456\nFounder 1: A\nFounder 2: B\nOwnership: 50/50",
              corporateSpec: "You are a top-tier Silicon Valley startup attorney and Delaware corporate counsel.\nYour task is to generate a complete institutional-grade post-formation legal documentation package for a Delaware C-Corporation startup.\nThe Certificate of Incorporation has already been filed.\nRequired documents include Corporate Bylaws, Initial Board Consent, Founder Stock Purchase Agreements, Stock Ledger, Cap Table, IP Assignment, and 83(b) Election Instructions.\nInclude confidential information and invention assignment language where appropriate.",
            };
            const result = {};
            for (const [name, brief] of Object.entries(cases)) {
              const draft = buildGeneratedLegalDraft(brief);
              result[name] = {
                firstLine: draft.split(/\r?\n/)[0],
                matterLine: draft.split(/\r?\n/).find((line) => line.startsWith("Detected matter type:")),
                draft,
              };
            }
            process.stdout.write(JSON.stringify(result));
            """
        )
        completed = subprocess.run(
            ["node", "-e", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        result = json.loads(completed.stdout)

        self.assertEqual(result["nda"]["firstLine"], "CONFIDENTIALITY / NDA DRAFT")
        self.assertEqual(result["nda"]["matterLine"], "Detected matter type: nda")
        self.assertIn("Alpha AI", result["nda"]["draft"])

        self.assertEqual(result["demand"]["firstLine"], "LEGAL DEMAND LETTER DRAFT")
        self.assertEqual(result["demand"]["matterLine"], "Detected matter type: demand-letter")
        self.assertIn("欠款 50000", result["demand"]["draft"])

        self.assertEqual(
            result["corporate"]["firstLine"],
            "DELAWARE C-CORP POST-FORMATION LEGAL DOCUMENTATION PACKAGE",
        )
        self.assertEqual(result["corporate"]["matterLine"], "Detected matter type: corporate")
        self.assertIn("Example AI Inc", result["corporate"]["draft"])

        self.assertEqual(
            result["corporateSpec"]["firstLine"],
            "DELAWARE C-CORP POST-FORMATION LEGAL DOCUMENTATION PACKAGE",
        )
        self.assertEqual(result["corporateSpec"]["matterLine"], "Detected matter type: corporate")
        self.assertIn("post-formation legal documentation package", result["corporateSpec"]["draft"])

    def test_ui_requires_backend_generation_before_delivery(self) -> None:
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")

        start_run = source.rindex("async function startLegalDraftRun")
        event_listeners = source.index("runButton.addEventListener", start_run)
        start_run_block = source[start_run:event_listeners]
        self.assertIn('generationServiceBaseUrl = useLocalGenerationService ? "http://127.0.0.1:9766" : ""', source)
        self.assertIn('"/api"', source)
        self.assertIn('generationServiceCommand = "python3 -m legal_doc_agent serve --port 9766"', source)
        self.assertIn("localGenerationPageIssue", source)
        self.assertIn('googleDocServiceBaseUrl = "http://127.0.0.1:9765"', source)
        self.assertIn("requestBackendLegalDraft(briefSnapshot)", start_run_block)
        self.assertNotIn("startGoogleDocHandoffForRun();", start_run_block)
        self.assertIn("clearChromeBridgeRequest();", start_run_block)
        self.assertIn('generatedDraftSource = "backend"', source)
        self.assertIn("generatedDocxBase64", source)
        self.assertIn("docxBase64ToBlob", source)
        self.assertIn('generation_mode === "timeout_recovery"', source)
        self.assertIn("已生成超时恢复 Word", source)
        self.assertNotIn("Legacy", source)

        copy_start = source.rindex("async function copyGeneratedDraft")
        xml_start = source.index("function xmlEscape", copy_start)
        copy_block = source[copy_start:xml_start]
        self.assertIn('generatedDraftSource !== "backend"', copy_block)
        self.assertNotIn("buildGeneratedLegalDraft", copy_block)

        download_start = source.rindex("function downloadLocalDocx")
        skills_start = source.index("function renderSkills", download_start)
        download_block = source[download_start:skills_start]
        self.assertIn('generatedDraftSource !== "backend"', download_block)
        self.assertIn("!generatedDocxBase64", download_block)
        self.assertIn("docxBase64ToBlob(generatedDocxBase64)", download_block)
        self.assertNotIn("createLocalDocxBlob(generatedDraftText)", download_block)
        self.assertNotIn("completeDraftOutput();", download_block)

    def test_processing_panel_starts_idle_and_tracks_agent_count(self) -> None:
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")

        self.assertIn('<strong id="runningCount">0</strong>', html)
        self.assertIn('<strong id="totalCount">4</strong>', html)
        self.assertIn('<em id="runStatus">待输入</em>', html)
        self.assertIn('<span id="conversationTimeLabel">未开始</span>', html)
        self.assertIn("等待生成文书", html)
        self.assertNotIn("02:52 05/31", html)

        self.assertIn('let runState = "idle"', source)
        self.assertIn('return runState === "running";', source)
        self.assertIn("totalCount.textContent = String(agents.length)", source)
        self.assertIn("doneCount.textContent = String(agents.length)", source)
        self.assertIn("step = Math.min(livePhases.length - 1, step + 1)", source)
        self.assertNotIn("step = (step + 1) % agents.length", source)

    def test_processing_panel_shows_live_agent_activity(self) -> None:
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="agentLiveStatus"', html)
        self.assertIn('id="agentLiveList"', html)
        self.assertIn('id="agentEventLog"', html)
        self.assertIn("Agent 实时动态", html)
        self.assertIn("显示每个 Agent 的当前动作、耗时和后端回传事件", html)

        self.assertIn("let agentRuntimeState = createInitialAgentRuntime();", source)
        self.assertIn("function resetAgentRuntime", source)
        self.assertIn("function updateAgentRuntime", source)
        self.assertIn("function appendAgentEvent", source)
        self.assertIn("function syncAgentRuntimeFromPayload", source)
        self.assertIn("renderAgentLiveStatus();", source)
        self.assertIn("payload?.observations", source)
        self.assertIn('updateAgentRuntime("browser"', source)
        self.assertIn('updateAgentRuntime("file"', source)
        self.assertIn('updateAgentRuntime("reviewer"', source)

    def test_agent_status_panel_is_compact_and_not_duplicated(self) -> None:
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        styles = (ROOT / "ui" / "styles.css").read_text(encoding="utf-8")

        self.assertNotIn('id="agentWorkFeed"', html)
        self.assertIn('class="agent-live-row', source)
        self.assertNotIn('class="agent-live-card', source)
        live_render = source[source.index("function renderAgentLiveStatus"):source.index("function agentStatusLabel")]
        self.assertNotIn("agent.model", live_render)
        self.assertIn(".agent-live-row", styles)
        self.assertNotIn(".agent-live-card", styles)

    def test_frontend_phase_timer_does_not_fake_agent_completion(self) -> None:
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
        start_run = source.rindex("async function startLegalDraftRun")
        request_block = source[start_run:source.index("try {", start_run)]

        self.assertNotIn('updateAgentRuntime(previousPhase.agentId, "done"', request_block)
        self.assertNotIn("该阶段已提交给下一位 Agent", request_block)
        self.assertIn('"tracking"', source)
        self.assertIn("等待后端真实事件确认", request_block)

    def test_local_generation_uses_run_status_polling(self) -> None:
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")

        self.assertIn('generationServiceGenerateStartUrl = useLocalGenerationService', source)
        self.assertIn('`${generationServiceBaseUrl}/legal-doc/generate/start`', source)
        self.assertIn('function generationServiceRunStatusUrl(runId)', source)
        self.assertIn('async function pollBackendGenerationRun', source)
        self.assertIn("syncAgentRuntimeFromEvents(status.data?.events || [])", source)
        self.assertIn('status.data?.status === "completed"', source)
        self.assertIn('status.data?.result', source)
        self.assertIn("renderedBackendEventKeys = new Set()", source)

    def test_prompt_entry_has_one_clear_generation_action(self) -> None:
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Ctrl + Enter 开始生成 Word 文书", html)
        self.assertIn("生成 Word 文书", html)
        self.assertNotIn("发送给 Agent", html)
        self.assertNotIn('id="sendToAgentButton"', html)
        self.assertIn('document.querySelector("#sendToAgentButton")', source)
        self.assertIn("if (sendToAgentButton) {", source)
        self.assertIn("startLegalDraftRun();", source)

    def test_brief_textarea_starts_empty(self) -> None:
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
        match = re.search(r'<textarea id="briefInput"[^>]*>(.*?)</textarea>', html, re.S)

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group(1).strip(), "")
        self.assertNotIn("Company legal name:", match.group(1))

    def test_google_doc_handoff_copy_does_not_require_chrome_extension(self) -> None:
        source = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")

        self.assertIn("Google Doc 接管请求", html)
        self.assertNotIn("Chrome 监控编辑", html)
        self.assertNotIn("Playwright", source)
        self.assertNotIn("Chrome bridge", source)
        self.assertNotIn("插件", source)
