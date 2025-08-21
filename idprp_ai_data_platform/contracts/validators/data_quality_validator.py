"""Data-quality validation for records against loaded contract rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from idprp_ai_data_platform.contracts.definitions.loader import DataContract


@dataclass(frozen=True)
class QualityViolation:
    """Represents one data-quality validation failure."""

    field: str
    rule: str
    message: str
    expected: str = ""
    observed: str = ""


@dataclass(frozen=True)
class QualityValidationResult:
    """Collects quality validation outcome and violations."""

    violations: list[QualityViolation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.violations


def validate_quality_rules(
    records: list[dict[str, Any]],
    contract: DataContract,
    observed_max_lag_ms: float | None = None,
) -> QualityValidationResult:
    """Validate null thresholds, duplicates, required fields, and freshness."""

    violations: list[QualityViolation] = []
    total_records = len(records)

    for rule in contract.quality_rules:
        field_values = [record.get(rule.field) for record in records]
        null_count = sum(value is None for value in field_values)

        if rule.required and null_count > 0:
            violations.append(
                QualityViolation(
                    field=rule.field,
                    rule="required",
                    message=f"Field {rule.field} is required but {null_count} records are null or missing",
                    expected="0 null or missing values",
                    observed=str(null_count),
                )
            )

        if rule.max_null_ratio is not None and total_records > 0:
            null_ratio = null_count / total_records
            if null_ratio > rule.max_null_ratio:
                violations.append(
                    QualityViolation(
                        field=rule.field,
                        rule="max_null_ratio",
                        message=f"Field {rule.field} exceeded null ratio threshold",
                        expected=str(rule.max_null_ratio),
                        observed=f"{null_ratio:.4f}",
                    )
                )

        if not rule.allow_duplicates:
            non_null_values = [value for value in field_values if value is not None]
            duplicate_counts = Counter(non_null_values)
            duplicate_values = [
                value for value, count in duplicate_counts.items() if count > 1
            ]
            if duplicate_values:
                violations.append(
                    QualityViolation(
                        field=rule.field,
                        rule="duplicates",
                        message=f"Field {rule.field} contains duplicate values",
                        expected="unique values",
                        observed=str(duplicate_values[:3]),
                    )
                )

    if contract.freshness is not None and observed_max_lag_ms is not None:
        if observed_max_lag_ms > contract.freshness.max_lag_ms:
            violations.append(
                QualityViolation(
                    field="freshness",
                    rule="max_lag_ms",
                    message="Observed ingestion lag exceeded freshness threshold",
                    expected=str(contract.freshness.max_lag_ms),
                    observed=str(observed_max_lag_ms),
                )
            )

    return QualityValidationResult(violations=violations)