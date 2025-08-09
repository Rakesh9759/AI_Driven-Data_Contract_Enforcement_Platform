"""Telemetry metric simulator used to model ingestion health signals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from random import Random


@dataclass(frozen=True)
class MetricsSimulator:
    """Generates latency and throughput metrics for pipeline monitoring."""

    seed: int = 11
    source_system: str = "metrics-simulator"

    def generate(self, count: int) -> list[dict[str, object]]:
        if count <= 0:
            raise ValueError("count must be greater than zero")

        rng = Random(self.seed)
        now = datetime.now(tz=timezone.utc)
        rows: list[dict[str, object]] = []
        for idx in range(count):
            event_time = now - timedelta(seconds=idx * 10)
            rows.append(
                {
                    "metric_id": f"met-{idx + 1:05d}",
                    "source": self.source_system,
                    "event_time": event_time.isoformat(),
                    "throughput_rps": round(rng.uniform(250.0, 480.0), 2),
                    "consumer_lag": rng.randint(0, 45),
                    "latency_ms": rng.randint(45, 320),
                    "null_ratio": round(rng.uniform(0.0, 0.04), 4),
                }
            )
        return rows
