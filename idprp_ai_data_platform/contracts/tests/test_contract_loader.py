"""Tests for YAML contract definitions and loader."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from idprp_ai_data_platform.common.exceptions import ContractDefinitionError
from idprp_ai_data_platform.contracts.definitions.loader import (
    DataContract,
    load_contract_from_yaml,
    load_contracts_from_directory,
)


class TestContractLoader(unittest.TestCase):
    """Tests for contract YAML loading and validation."""

    def test_load_sample_cdr_contract(self) -> None:
        contract = load_contract_from_yaml(
            Path("idprp_ai_data_platform/contracts/definitions/cdr_events.yaml")
        )

        self.assertIsInstance(contract, DataContract)
        self.assertEqual(contract.dataset_name, "cdr_events")
        self.assertEqual(contract.version, "v1")
        self.assertEqual(len(contract.schema), 6)
        self.assertIsNotNone(contract.freshness)
        self.assertEqual(contract.freshness.max_lag_ms, 5000.0)

    def test_load_sample_metrics_contract(self) -> None:
        contract = load_contract_from_yaml(
            Path("idprp_ai_data_platform/contracts/definitions/device_metrics.yaml")
        )

        self.assertEqual(contract.dataset_name, "device_metrics")
        self.assertEqual(len(contract.quality_rules), 2)

    def test_load_contracts_from_directory(self) -> None:
        contracts = load_contracts_from_directory(
            Path("idprp_ai_data_platform/contracts/definitions")
        )

        self.assertIn("cdr_events", contracts)
        self.assertIn("device_metrics", contracts)
        self.assertEqual(len(contracts), 2)

    def test_missing_contract_file_raises(self) -> None:
        with self.assertRaises(ContractDefinitionError):
            load_contract_from_yaml(Path("idprp_ai_data_platform/contracts/definitions/missing.yaml"))

    def test_invalid_yaml_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            contract_file = Path(tmp_dir) / "broken.yaml"
            contract_file.write_text("contract_name: [broken", encoding="utf-8")

            with self.assertRaises(ContractDefinitionError):
                load_contract_from_yaml(contract_file)

    def test_missing_required_keys_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            contract_file = Path(tmp_dir) / "missing_keys.yaml"
            contract_file.write_text(
                "dataset_name: cdr_events\nschema: []\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractDefinitionError):
                load_contract_from_yaml(contract_file)

    def test_empty_schema_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            contract_file = Path(tmp_dir) / "empty_schema.yaml"
            contract_file.write_text(
                "contract_name: sample\nversion: v1\ndataset_name: sample\nschema: []\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractDefinitionError):
                load_contract_from_yaml(contract_file)

    def test_invalid_quality_rule_threshold_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            contract_file = Path(tmp_dir) / "bad_quality.yaml"
            contract_file.write_text(
                "contract_name: sample\n"
                "version: v1\n"
                "dataset_name: sample\n"
                "schema:\n"
                "  - name: event_id\n"
                "    type: string\n"
                "quality_rules:\n"
                "  - field: event_id\n"
                "    max_null_ratio: 1.5\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractDefinitionError):
                load_contract_from_yaml(contract_file)

    def test_invalid_freshness_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            contract_file = Path(tmp_dir) / "bad_freshness.yaml"
            contract_file.write_text(
                "contract_name: sample\n"
                "version: v1\n"
                "dataset_name: sample\n"
                "schema:\n"
                "  - name: event_id\n"
                "    type: string\n"
                "freshness:\n"
                "  max_lag_ms: 0\n",
                encoding="utf-8",
            )

            with self.assertRaises(ContractDefinitionError):
                load_contract_from_yaml(contract_file)

    def test_directory_loader_requires_directory(self) -> None:
        with self.assertRaises(ContractDefinitionError):
            load_contracts_from_directory(Path("idprp_ai_data_platform/contracts/definitions/missing"))