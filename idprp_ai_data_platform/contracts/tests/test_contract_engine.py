"""Tests for runtime contract enforcement engine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from idprp_ai_data_platform.common.exceptions import ContractValidationError
from idprp_ai_data_platform.contracts.enforcement.contract_engine import ContractEngine


class TestContractEngine(unittest.TestCase):
    """Validate runtime enforcement composition for contracts."""

    def setUp(self) -> None:
        self.engine = ContractEngine(
            Path("idprp_ai_data_platform/contracts/definitions")
        )
        self.valid_records = [
            {
                "event_id": "cdr-00001",
                "source": "cdr-simulator",
                "event_time": "2025-08-23T12:00:00Z",
                "caller_id": "user-a",
                "callee_id": "user-b",
                "duration_sec": 120,
                "network_type": "5g",
                "status": "ok",
            },
            {
                "event_id": "cdr-00002",
                "source": "cdr-simulator",
                "event_time": "2025-08-23T12:01:00Z",
                "caller_id": "user-a",
                "callee_id": "user-b",
                "duration_sec": 90,
                "network_type": "lte",
                "status": "warn",
            },
        ]

    def test_default_directory_initializes(self) -> None:
        engine = ContractEngine.from_default_directory()
        self.assertIn("cdr_events", engine.contracts)

    def test_unknown_dataset_raises(self) -> None:
        with self.assertRaises(ContractValidationError):
            self.engine.validate_records("unknown_dataset", self.valid_records)

    def test_non_list_records_raise(self) -> None:
        with self.assertRaises(ContractValidationError):
            self.engine.validate_records("cdr_events", {"event_id": "evt-1"})  # type: ignore[arg-type]

    def test_valid_records_produce_valid_report(self) -> None:
        report = self.engine.validate_records(
            "cdr_events",
            self.valid_records,
            observed_max_lag_ms=1000.0,
        )

        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_violations, 0)
        self.assertEqual(report.dataset_name, "cdr_events")

    def test_report_combines_schema_and_quality_violations(self) -> None:
        records = [dict(self.valid_records[0]), dict(self.valid_records[1])]
        records[0].pop("callee_id")
        records[1]["event_id"] = "cdr-00001"

        report = self.engine.validate_records(
            "cdr_events",
            records,
            observed_max_lag_ms=7000.0,
        )

        self.assertFalse(report.is_valid)
        self.assertEqual(len(report.schema_result.violations), 1)
        self.assertEqual(len(report.quality_result.violations), 2)
        self.assertEqual(report.total_violations, 3)

    def test_validate_jsonl_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_file = Path(tmp_dir) / "cdr_events.jsonl"
            sample_file.write_text(
                "\n".join([
                    '{"event_id": "cdr-00001", "source": "cdr-simulator", "event_time": "2025-08-23T12:00:00Z", "caller_id": "user-a", "callee_id": "user-b", "duration_sec": 120, "network_type": "5g", "status": "ok"}',
                    '{"event_id": "cdr-00002", "source": "cdr-simulator", "event_time": "2025-08-23T12:01:00Z", "caller_id": "user-a", "callee_id": "user-b", "duration_sec": 90, "network_type": "lte", "status": "warn"}',
                ]),
                encoding="utf-8",
            )

            report = self.engine.validate_jsonl_file(
                "cdr_events",
                sample_file,
                observed_max_lag_ms=1000.0,
            )

            self.assertTrue(report.is_valid)
            self.assertEqual(report.total_violations, 0)

    def test_validate_jsonl_file_filters_mixed_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_file = Path(tmp_dir) / "mixed_events.jsonl"
            sample_file.write_text(
                "\n".join([
                    '{"event_id": "cdr-00001", "source": "cdr-simulator", "event_time": "2025-08-23T12:00:00Z", "caller_id": "user-a", "callee_id": "user-b", "duration_sec": 120, "network_type": "5g", "status": "ok"}',
                    '{"metric_id": "met-00001", "source": "metrics-simulator", "event_time": "2025-08-23T12:00:05Z", "throughput_rps": 320.5, "consumer_lag": 5, "latency_ms": 100, "null_ratio": 0.01}',
                    '{"event_id": "cdr-00002", "source": "cdr-simulator", "event_time": "2025-08-23T12:01:00Z", "caller_id": "user-a", "callee_id": "user-b", "duration_sec": 90, "network_type": "lte", "status": "warn"}',
                ]),
                encoding="utf-8",
            )

            report = self.engine.validate_jsonl_file(
                "cdr_events",
                sample_file,
                observed_max_lag_ms=1000.0,
            )

            self.assertTrue(report.is_valid)
            self.assertEqual(report.total_violations, 0)