"""Tests for contract data-quality validation."""

from __future__ import annotations

import unittest
from pathlib import Path

from idprp_ai_data_platform.contracts.definitions.loader import load_contract_from_yaml
from idprp_ai_data_platform.contracts.validators.data_quality_validator import (
    validate_quality_rules,
)


class TestDataQualityValidator(unittest.TestCase):
    """Validate quality rules against sample records."""

    def setUp(self) -> None:
        self.contract = load_contract_from_yaml(
            Path("idprp_ai_data_platform/contracts/definitions/cdr_events.yaml")
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
                "duration_sec": 98,
                "network_type": "lte",
                "status": "warn",
            },
        ]

    def test_valid_quality_rules_pass(self) -> None:
        result = validate_quality_rules(self.valid_records, self.contract, observed_max_lag_ms=1000.0)
        self.assertTrue(result.is_valid)

    def test_required_rule_fails_for_nulls(self) -> None:
        records = [dict(self.valid_records[0]), dict(self.valid_records[1])]
        records[0]["event_time"] = None

        result = validate_quality_rules(records, self.contract)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.violations[0].rule, "required")

    def test_null_ratio_rule_fails(self) -> None:
        records = [dict(self.valid_records[0]), dict(self.valid_records[1])]
        records[0]["duration_sec"] = None

        result = validate_quality_rules(records, self.contract)

        self.assertFalse(result.is_valid)
        self.assertTrue(any(v.rule == "max_null_ratio" for v in result.violations))

    def test_duplicate_rule_fails(self) -> None:
        records = [dict(self.valid_records[0]), dict(self.valid_records[1])]
        records[1]["event_id"] = "cdr-00001"

        result = validate_quality_rules(records, self.contract)

        self.assertFalse(result.is_valid)
        self.assertTrue(any(v.rule == "duplicates" for v in result.violations))

    def test_freshness_rule_fails(self) -> None:
        result = validate_quality_rules(
            self.valid_records,
            self.contract,
            observed_max_lag_ms=7000.0,
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.violations[0].field, "freshness")