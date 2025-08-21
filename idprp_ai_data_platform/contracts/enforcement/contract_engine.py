"""Runtime contract enforcement engine built on the contract loader and validators."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from idprp_ai_data_platform.common.exceptions import (
    ContractDefinitionError,
    ContractValidationError,
)
from idprp_ai_data_platform.contracts.definitions.loader import (
    DataContract,
    load_contracts_from_directory,
)
from idprp_ai_data_platform.contracts.validators.data_quality_validator import (
    QualityValidationResult,
    validate_quality_rules,
)
from idprp_ai_data_platform.contracts.validators.schema_validator import (
    SchemaValidationResult,
    validate_schema,
)


@dataclass(frozen=True)
class ContractValidationReport:
    """Combined runtime validation report for one dataset batch."""

    dataset_name: str
    contract: DataContract
    schema_result: SchemaValidationResult
    quality_result: QualityValidationResult

    @property
    def is_valid(self) -> bool:
        return self.schema_result.is_valid and self.quality_result.is_valid

    @property
    def total_violations(self) -> int:
        return len(self.schema_result.violations) + len(self.quality_result.violations)


class ContractEngine:
    """Loads contracts and applies schema and quality validation at runtime."""

    def __init__(self, contracts_directory: Path) -> None:
        self.contracts_directory = contracts_directory
        self.contracts = load_contracts_from_directory(contracts_directory)

    def get_contract(self, dataset_name: str) -> DataContract:
        """Return a loaded contract for the named dataset."""

        contract = self.contracts.get(dataset_name)
        if contract is None:
            raise ContractValidationError(
                f"No contract loaded for dataset: {dataset_name}"
            )
        return contract

    def validate_records(
        self,
        dataset_name: str,
        records: list[dict[str, Any]],
        observed_max_lag_ms: float | None = None,
    ) -> ContractValidationReport:
        """Apply schema and quality validation for a dataset batch."""

        if not isinstance(records, list):
            raise ContractValidationError("Contract engine expects records as a list")

        contract = self.get_contract(dataset_name)
        schema_result = validate_schema(records, contract)
        quality_result = validate_quality_rules(
            records,
            contract,
            observed_max_lag_ms=observed_max_lag_ms,
        )

        return ContractValidationReport(
            dataset_name=dataset_name,
            contract=contract,
            schema_result=schema_result,
            quality_result=quality_result,
        )

    def validate_jsonl_file(
        self,
        dataset_name: str,
        file_path: Path,
        observed_max_lag_ms: float | None = None,
    ) -> ContractValidationReport:
        """Load a JSONL file and apply runtime contract enforcement."""

        if not file_path.exists():
            raise ContractValidationError(f"Validation input file not found: {file_path}")

        contract = self.get_contract(dataset_name)
        records: list[dict[str, Any]] = []
        with file_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                content = line.strip()
                if not content:
                    continue
                try:
                    payload = json.loads(content)
                except json.JSONDecodeError as exc:
                    raise ContractValidationError(
                        f"Invalid JSON in validation input at line {line_number}: {file_path}"
                    ) from exc

                if not isinstance(payload, dict):
                    raise ContractValidationError(
                        f"Validation input must contain JSON objects at line {line_number}: {file_path}"
                    )

                if (
                    contract.source_system is not None
                    and payload.get("source") != contract.source_system
                ):
                    continue
                records.append(payload)

        if not records:
            raise ContractValidationError(
                f"No records matched dataset {dataset_name} in file: {file_path}"
            )

        return self.validate_records(
            dataset_name,
            records,
            observed_max_lag_ms=observed_max_lag_ms,
        )

    @classmethod
    def from_default_directory(cls) -> "ContractEngine":
        """Create an engine from the repository default contracts directory."""

        contracts_directory = (
            Path(__file__).resolve().parents[1] / "definitions"
        )
        try:
            return cls(contracts_directory)
        except ContractDefinitionError as exc:
            raise ContractValidationError(
                f"Failed to initialize contract engine: {exc}"
            ) from exc