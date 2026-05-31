from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from legal_doc_agent.cli import main


class CliTests(unittest.TestCase):
    def test_kb_db_argument_works_before_or_after_subcommand(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            after_db = root / "after.sqlite"
            before_db = root / "before.sqlite"
            authority = root / "authority.txt"
            authority.write_text(
                "Issuer means a person who issues or proposes to issue securities.",
                encoding="utf-8",
            )

            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                self.assertEqual(
                    main(["kb", "init", "--db", str(after_db), "--seed-sources"]),
                    0,
                )
                self.assertEqual(main(["kb", "sources", "--db", str(after_db)]), 0)
                self.assertEqual(
                    main(
                        [
                            "kb",
                            "ingest-text",
                            "--db",
                            str(after_db),
                            "--source-key",
                            "govinfo-uscode",
                            "--citation",
                            "15 U.S.C. 77a",
                            "--title",
                            "Definitions",
                            "--url",
                            "https://example.test/15/77a",
                            "--text-file",
                            str(authority),
                            "--heading",
                            "Issuer definition",
                        ]
                    ),
                    0,
                )
                self.assertEqual(
                    main(["kb", "search", "--db", str(after_db), "issuer"]),
                    0,
                )
                self.assertEqual(main(["kb", "--db", str(before_db), "init"]), 0)

            self.assertTrue(after_db.exists())
            self.assertTrue(before_db.exists())

    def test_generate_reports_uninitialized_kb_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_db = Path(temp_dir) / "missing.sqlite"

            stderr = StringIO()
            with redirect_stdout(StringIO()), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "--dry-run",
                        "--brief-text",
                        "Company: Example AI, Inc.",
                        "--kb-db",
                        str(missing_db),
                        "--kb-query",
                        "issuer",
                    ]
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("error:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
