"""Schema drift and bad-data injector for simulator outputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from random import Random


@dataclass(frozen=True)
class DriftInjector:
    """Injects controlled schema drift and quality issues into event streams."""

    seed: int = 23

    def inject(
        self,
        rows: list[dict[str, object]],
        drift_rate: float,
        bad_data_rate: float,
        late_event_rate: float,
        duplicate_rate: float,
    ) -> list[dict[str, object]]:
        self._validate_rate("drift_rate", drift_rate)
        self._validate_rate("bad_data_rate", bad_data_rate)
        self._validate_rate("late_event_rate", late_event_rate)
        self._validate_rate("duplicate_rate", duplicate_rate)

        rng = Random(self.seed)
        output: list[dict[str, object]] = []
        for row in rows:
            candidate = dict(row)

            if rng.random() < drift_rate:
                candidate = self._apply_schema_drift(candidate, rng)

            if rng.random() < bad_data_rate:
                candidate = self._apply_bad_data(candidate, rng)

            if rng.random() < late_event_rate:
                candidate = self._apply_late_event(candidate)

            output.append(candidate)

            if rng.random() < duplicate_rate:
                output.append(dict(candidate))

        return output

    @staticmethod
    def _validate_rate(name: str, value: float) -> None:
        if value < 0 or value > 1:
            raise ValueError(f"{name} must be between 0 and 1")

    @staticmethod
    def _apply_schema_drift(row: dict[str, object], rng: Random) -> dict[str, object]:
        if "duration_sec" in row:
            scenario = rng.choice(["rename", "drop", "type_shift", "add_column"])
            if scenario == "rename" and "callee_id" in row:
                row["callee_identifier"] = row.pop("callee_id")
            elif scenario == "drop":
                row.pop("network_type", None)
            elif scenario == "type_shift" and "duration_sec" in row:
                row["duration_sec"] = str(row["duration_sec"])
            else:
                row["roaming_flag"] = rng.choice([True, False])
            return row

        if "throughput_rps" in row:
            scenario = rng.choice(["rename", "drop", "type_shift", "add_column"])
            if scenario == "rename":
                row["throughput_per_sec"] = row.pop("throughput_rps")
            elif scenario == "drop":
                row.pop("consumer_lag", None)
            elif scenario == "type_shift" and "latency_ms" in row:
                row["latency_ms"] = f"{row['latency_ms']}ms"
            else:
                row["pipeline_region"] = rng.choice(["us-east", "us-central", "us-west"])
            return row

        row["unexpected_field"] = "schema-drift"
        return row

    @staticmethod
    def _apply_bad_data(row: dict[str, object], rng: Random) -> dict[str, object]:
        if "duration_sec" in row:
            scenario = rng.choice(["null_key", "negative_duration", "blank_caller"])
            if scenario == "null_key":
                row["event_id"] = None
            elif scenario == "negative_duration":
                row["duration_sec"] = -1
            else:
                row["caller_id"] = ""
            return row

        if "throughput_rps" in row:
            scenario = rng.choice(["null_ratio", "negative_lag", "throughput_text"])
            if scenario == "null_ratio":
                row["null_ratio"] = None
            elif scenario == "negative_lag":
                row["consumer_lag"] = -3
            else:
                row["throughput_rps"] = "unknown"
            return row

        row["corrupted"] = True
        return row

    @staticmethod
    def _apply_late_event(row: dict[str, object]) -> dict[str, object]:
        event_time = row.get("event_time")
        if not isinstance(event_time, str):
            return row

        try:
            parsed = datetime.fromisoformat(event_time)
        except ValueError:
            return row

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        row["event_time"] = (parsed - timedelta(days=2)).isoformat()
        row["is_late_event"] = True
        return row
