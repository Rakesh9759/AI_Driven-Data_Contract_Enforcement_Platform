from __future__ import annotations

from datetime import datetime, timezone
import unittest

from idprp_ai_data_platform.ingestion.simulators.metrics_simulator import MetricsSimulator


class TestMetricsSimulator(unittest.TestCase):
    def test_generate_expected_count(self) -> None:
        rows = MetricsSimulator(seed=11).generate(6)
        self.assertEqual(6, len(rows))

    def test_generate_is_deterministic_for_seed(self) -> None:
        fixed_time = datetime(2025, 8, 1, 0, 0, 0, tzinfo=timezone.utc)
        sim_a = MetricsSimulator(seed=51, reference_time=fixed_time)
        sim_b = MetricsSimulator(seed=51, reference_time=fixed_time)
        self.assertEqual(sim_a.generate(3), sim_b.generate(3))

    def test_invalid_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            MetricsSimulator().generate(-1)


if __name__ == "__main__":
    unittest.main()
