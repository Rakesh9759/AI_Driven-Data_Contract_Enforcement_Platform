from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from idprp_ai_data_platform.ingestion.simulators.generate_samples import main


class TestGenerateSamplesCli(unittest.TestCase):
    def test_main_generates_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "samples.jsonl"
            code = main([
                "--count",
                "5",
                "--output",
                str(output_path),
                "--drift-rate",
                "0.2",
                "--bad-data-rate",
                "0.2",
                "--late-event-rate",
                "0.2",
                "--duplicate-rate",
                "0.2",
            ])
            self.assertEqual(0, code)
            self.assertTrue(output_path.exists())
            lines = output_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreaterEqual(len(lines), 10)
            json.loads(lines[0])


if __name__ == "__main__":
    unittest.main()
