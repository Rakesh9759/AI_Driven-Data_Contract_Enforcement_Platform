"""Base CDR-style event simulator used in early ingestion phases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from random import Random


@dataclass(frozen=True)
class CDREventSimulator:
    """Generates deterministic call-detail-like events for local validation."""

    seed: int = 7
    source_system: str = "cdr-simulator"

    def generate(self, count: int) -> list[dict[str, object]]:
        if count <= 0:
            raise ValueError("count must be greater than zero")

        rng = Random(self.seed)
        now = datetime.now(tz=timezone.utc)
        rows: list[dict[str, object]] = []
        for idx in range(count):
            event_time = now - timedelta(seconds=idx * 15)
            duration_sec = rng.randint(20, 360)
            rows.append(
                {
                    "event_id": f"cdr-{idx + 1:05d}",
                    "source": self.source_system,
                    "event_time": event_time.isoformat(),
                    "caller_id": f"+1-555-{rng.randint(1000, 9999)}",
                    "callee_id": f"+1-555-{rng.randint(1000, 9999)}",
                    "duration_sec": duration_sec,
                    "network_type": rng.choice(["5g", "4g", "lte"]),
                    "status": rng.choice(["ok", "ok", "warn"]),
                }
            )
        return rows
