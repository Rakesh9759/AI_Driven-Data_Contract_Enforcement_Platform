from __future__ import annotations

import unittest

from idprp_ai_data_platform.ingestion.simulators.drift_injector import DriftInjector


class TestDriftInjector(unittest.TestCase):
    def test_invalid_rate_rejected(self) -> None:
        injector = DriftInjector(seed=23)
        with self.assertRaises(ValueError):
            injector.inject([], drift_rate=1.2, bad_data_rate=0, late_event_rate=0, duplicate_rate=0)

    def test_duplicate_rate_adds_rows(self) -> None:
        rows = [{"event_id": "evt-1", "event_time": "2025-08-01T00:00:00+00:00", "duration_sec": 10}]
        output = DriftInjector(seed=23).inject(
            rows,
            drift_rate=0.0,
            bad_data_rate=0.0,
            late_event_rate=0.0,
            duplicate_rate=1.0,
        )
        self.assertEqual(2, len(output))

    def test_late_event_marker_added(self) -> None:
        rows = [{"event_id": "evt-1", "event_time": "2025-08-01T00:00:00+00:00", "duration_sec": 10}]
        output = DriftInjector(seed=23).inject(
            rows,
            drift_rate=0.0,
            bad_data_rate=0.0,
            late_event_rate=1.0,
            duplicate_rate=0.0,
        )
        self.assertTrue(output[0].get("is_late_event"))


if __name__ == "__main__":
    unittest.main()
