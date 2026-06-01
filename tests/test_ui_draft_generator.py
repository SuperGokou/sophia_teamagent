from __future__ import annotations

import json
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
        self.assertIn('generationServiceBaseUrl = "http://127.0.0.1:9766"', source)
        self.assertIn('googleDocServiceBaseUrl = "http://127.0.0.1:9765"', source)
        self.assertIn("requestBackendLegalDraft(briefSnapshot)", start_run_block)
        self.assertNotIn("startGoogleDocHandoffForRun();", start_run_block)
        self.assertIn("clearChromeBridgeRequest();", start_run_block)
        self.assertIn('generatedDraftSource = "backend"', source)
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
        self.assertNotIn("completeDraftOutput();", download_block)
