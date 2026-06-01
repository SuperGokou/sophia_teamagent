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

        self.assertEqual(result["corporate"]["firstLine"], "CORPORATE POST-FORMATION PACKAGE DRAFT")
        self.assertEqual(result["corporate"]["matterLine"], "Detected matter type: corporate")
        self.assertIn("Example AI Inc", result["corporate"]["draft"])
