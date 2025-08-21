from __future__ import annotations

from datetime import datetime, timezone
import unittest

from idprp_ai_data_platform.ingestion.simulators.cdr_simulator import CDREventSimulator


class TestCDREventSimulator(unittest.TestCase):
    def test_generate_expected_count(self) -> None:
        rows = CDREventSimulator(seed=7).generate(5)
        self.assertEqual(5, len(rows))

    def test_generate_is_deterministic_for_seed(self) -> None:
        fixed_time = datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
        sim_a = CDREventSimulator(seed=99, reference_time=fixed_time)
        sim_b = CDREventSimulator(seed=99, reference_time=fixed_time)
        self.assertEqual(sim_a.generate(4), sim_b.generate(4))

    def test_invalid_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            CDREventSimulator().generate(0)


if __name__ == "__main__":
    unittest.main()
