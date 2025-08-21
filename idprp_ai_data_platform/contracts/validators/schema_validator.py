"""Schema validation for records against a loaded data contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from idprp_ai_data_platform.contracts.definitions.loader import DataContract


TYPE_MAPPING: dict[str, type[Any] | tuple[type[Any], ...]] = {
    "string": str,
    "integer": int,
    "float": (float, int),
    "boolean": bool,
    "timestamp": str,
    "object": dict,
    "array": list,
}


@dataclass(frozen=True)
class SchemaViolation:
    """Represents one schema validation failure."""

    field: str
    rule: str
    message: str
    expected: str = ""
    observed: str = ""


@dataclass(frozen=True)
class SchemaValidationResult:
    """Collects schema validation outcome and violations."""

    violations: list[SchemaViolation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.violations


def _matches_expected_type(value: Any, expected_type: str) -> bool:
    if expected_type not in TYPE_MAPPING:
        return True

    mapped_type = TYPE_MAPPING[expected_type]
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "float":
        return (isinstance(value, (float, int)) and not isinstance(value, bool))
    return isinstance(value, mapped_type)


def validate_schema(records: list[dict[str, Any]], contract: DataContract) -> SchemaValidationResult:
    """Validate records for field presence, nullability, and types."""

    violations: list[SchemaViolation] = []
    expected_fields = {field.name: field for field in contract.schema}

    for record_index, record in enumerate(records):
        for field_name, contract_field in expected_fields.items():
            if field_name not in record:
                violations.append(
                    SchemaViolation(
                        field=field_name,
                        rule="missing_field",
                        message=f"Record {record_index} is missing field {field_name}",
                        expected=contract_field.field_type,
                    )
                )
                continue

            value = record[field_name]
            if value is None and not contract_field.nullable:
                violations.append(
                    SchemaViolation(
                        field=field_name,
                        rule="nullability",
                        message=f"Record {record_index} has null for non-nullable field {field_name}",
                        expected="non-null",
                        observed="null",
                    )
                )
                continue

            if value is not None and not _matches_expected_type(value, contract_field.field_type):
                violations.append(
                    SchemaViolation(
                        field=field_name,
                        rule="type_mismatch",
                        message=f"Record {record_index} field {field_name} has invalid type",
                        expected=contract_field.field_type,
                        observed=type(value).__name__,
                    )
                )

    return SchemaValidationResult(violations=violations)