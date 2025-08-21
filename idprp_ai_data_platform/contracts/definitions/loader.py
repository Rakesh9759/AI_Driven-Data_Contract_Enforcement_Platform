"""Typed loader for YAML data contract definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from idprp_ai_data_platform.common.exceptions import ContractDefinitionError


@dataclass(frozen=True)
class ContractField:
    """Schema field definition for a dataset contract."""

    name: str
    field_type: str
    nullable: bool = True
    description: str = ""


@dataclass(frozen=True)
class QualityRule:
    """Field-level quality expectation."""

    field: str
    max_null_ratio: float | None = None
    required: bool = False
    allow_duplicates: bool = True


@dataclass(frozen=True)
class FreshnessRule:
    """Freshness expectation for a dataset."""

    max_lag_ms: float


@dataclass(frozen=True)
class DataContract:
    """Complete contract definition for a dataset."""

    contract_name: str
    version: str
    dataset_name: str
    description: str = ""
    owners: list[str] = field(default_factory=list)
    schema: list[ContractField] = field(default_factory=list)
    quality_rules: list[QualityRule] = field(default_factory=list)
    freshness: FreshnessRule | None = None


def _expect_mapping(payload: Any, *, context: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractDefinitionError(f"Expected mapping for {context}")
    return payload


def _expect_list(payload: Any, *, context: str) -> list[Any]:
    if not isinstance(payload, list):
        raise ContractDefinitionError(f"Expected list for {context}")
    return payload


def _parse_schema(payload: Any) -> list[ContractField]:
    raw_fields = _expect_list(payload, context="schema")
    if not raw_fields:
        raise ContractDefinitionError("Contract schema must contain at least one field")

    fields: list[ContractField] = []
    for index, item in enumerate(raw_fields):
        field_mapping = _expect_mapping(item, context=f"schema[{index}]")
        name = str(field_mapping.get("name", "")).strip()
        field_type = str(field_mapping.get("type", "")).strip()
        if not name or not field_type:
            raise ContractDefinitionError(
                f"Schema field at index {index} must include name and type"
            )

        fields.append(
            ContractField(
                name=name,
                field_type=field_type,
                nullable=bool(field_mapping.get("nullable", True)),
                description=str(field_mapping.get("description", "")),
            )
        )

    return fields


def _parse_quality_rules(payload: Any) -> list[QualityRule]:
    if payload is None:
        return []

    raw_rules = _expect_list(payload, context="quality_rules")
    rules: list[QualityRule] = []

    for index, item in enumerate(raw_rules):
        rule_mapping = _expect_mapping(item, context=f"quality_rules[{index}]")
        field_name = str(rule_mapping.get("field", "")).strip()
        if not field_name:
            raise ContractDefinitionError(
                f"Quality rule at index {index} must include a field"
            )

        max_null_ratio_raw = rule_mapping.get("max_null_ratio")
        max_null_ratio = None
        if max_null_ratio_raw is not None:
            max_null_ratio = float(max_null_ratio_raw)
            if max_null_ratio < 0.0 or max_null_ratio > 1.0:
                raise ContractDefinitionError(
                    f"Quality rule for field {field_name} has invalid max_null_ratio"
                )

        rules.append(
            QualityRule(
                field=field_name,
                max_null_ratio=max_null_ratio,
                required=bool(rule_mapping.get("required", False)),
                allow_duplicates=bool(rule_mapping.get("allow_duplicates", True)),
            )
        )

    return rules


def _parse_freshness(payload: Any) -> FreshnessRule | None:
    if payload is None:
        return None

    freshness_mapping = _expect_mapping(payload, context="freshness")
    if "max_lag_ms" not in freshness_mapping:
        raise ContractDefinitionError("Freshness rule must include max_lag_ms")

    max_lag_ms = float(freshness_mapping["max_lag_ms"])
    if max_lag_ms <= 0:
        raise ContractDefinitionError("Freshness max_lag_ms must be greater than zero")

    return FreshnessRule(max_lag_ms=max_lag_ms)


def load_contract_from_yaml(file_path: Path) -> DataContract:
    """Load a single data contract from a YAML file."""

    if not file_path.exists():
        raise ContractDefinitionError(f"Contract file not found: {file_path}")

    try:
        payload = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ContractDefinitionError(f"Invalid YAML contract: {file_path}") from exc

    mapping = _expect_mapping(payload, context=file_path.name)
    required_keys = {"contract_name", "version", "dataset_name", "schema"}
    missing_keys = sorted(required_keys.difference(mapping.keys()))
    if missing_keys:
        raise ContractDefinitionError(
            "Missing required contract keys: " + ", ".join(missing_keys)
        )

    return DataContract(
        contract_name=str(mapping["contract_name"]),
        version=str(mapping["version"]),
        dataset_name=str(mapping["dataset_name"]),
        description=str(mapping.get("description", "")),
        owners=[str(owner) for owner in mapping.get("owners", [])],
        schema=_parse_schema(mapping["schema"]),
        quality_rules=_parse_quality_rules(mapping.get("quality_rules")),
        freshness=_parse_freshness(mapping.get("freshness")),
    )


def load_contracts_from_directory(directory_path: Path) -> dict[str, DataContract]:
    """Load all YAML contracts from a directory keyed by dataset name."""

    if not directory_path.exists() or not directory_path.is_dir():
        raise ContractDefinitionError(
            f"Contract directory not found: {directory_path}"
        )

    contracts: dict[str, DataContract] = {}
    for file_path in sorted(directory_path.glob("*.yaml")):
        contract = load_contract_from_yaml(file_path)
        contracts[contract.dataset_name] = contract

    return contracts