"""Tests for contract schema validation."""

from __future__ import annotations

import unittest
from pathlib import Path

from idprp_ai_data_platform.contracts.definitions.loader import load_contract_from_yaml
from idprp_ai_data_platform.contracts.validators.schema_validator import validate_schema


class TestSchemaValidator(unittest.TestCase):
    """Validate schema rules against sample records."""

    def setUp(self) -> None:
        self.contract = load_contract_from_yaml(
            Path("idprp_ai_data_platform/contracts/definitions/cdr_events.yaml")
        )
        self.valid_record = {
            "event_id": "cdr-00001",
            "source": "cdr-simulator",
            "event_time": "2025-08-23T12:00:00Z",
            "caller_id": "user-a",
            "callee_id": "user-b",
            "duration_sec": 120,
            "network_type": "5g",
            "status": "ok",
        }

    def test_valid_schema_passes(self) -> None:
        result = validate_schema([self.valid_record], self.contract)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.violations, [])

    def test_missing_field_fails(self) -> None:
        invalid_record = dict(self.valid_record)
        invalid_record.pop("callee_id")

        result = validate_schema([invalid_record], self.contract)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.violations[0].rule, "missing_field")

    def test_nullability_fails(self) -> None:
        invalid_record = dict(self.valid_record)
        invalid_record["event_id"] = None

        result = validate_schema([invalid_record], self.contract)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.violations[0].rule, "nullability")

    def test_type_mismatch_fails(self) -> None:
        invalid_record = dict(self.valid_record)
        invalid_record["duration_sec"] = "120"

        result = validate_schema([invalid_record], self.contract)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.violations[0].rule, "type_mismatch")

    def test_multiple_records_accumulate_violations(self) -> None:
        invalid_record_one = dict(self.valid_record)
        invalid_record_one.pop("caller_id")
        invalid_record_two = dict(self.valid_record)
        invalid_record_two["status"] = None
        invalid_record_two["duration_sec"] = None

        result = validate_schema(
            [invalid_record_one, invalid_record_two],
            self.contract,
        )

        self.assertEqual(len(result.violations), 3)