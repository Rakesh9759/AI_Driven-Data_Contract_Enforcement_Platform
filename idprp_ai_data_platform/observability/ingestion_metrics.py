"""
Ingestion metrics tracking for lag, throughput, and SLA compliance.

Tracks:
- Ingestion lag: time between event timestamp and ingestion completion
- Throughput: events/sec and batches/sec
- SLA compliance: latency percentiles and violation rates
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LatencyBucket:
    """Latency histogram bucket."""

    min_ms: float
    max_ms: float
    count: int


@dataclass
class IngestionMetrics:
    """Aggregated ingestion metrics for a time window."""

    window_start: datetime
    window_end: datetime
    total_events: int = 0
    total_batches: int = 0
    avg_lag_ms: float = 0.0
    max_lag_ms: float = 0.0
    p50_lag_ms: float = 0.0
    p99_lag_ms: float = 0.0
    throughput_events_per_sec: float = 0.0
    throughput_batches_per_sec: float = 0.0
    sla_violations: int = 0
    sla_violation_rate: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "total_events": self.total_events,
            "total_batches": self.total_batches,
            "avg_lag_ms": round(self.avg_lag_ms, 2),
            "max_lag_ms": round(self.max_lag_ms, 2),
            "p50_lag_ms": round(self.p50_lag_ms, 2),
            "p99_lag_ms": round(self.p99_lag_ms, 2),
            "throughput_events_per_sec": round(self.throughput_events_per_sec, 2),
            "throughput_batches_per_sec": round(self.throughput_batches_per_sec, 2),
            "sla_violations": self.sla_violations,
            "sla_violation_rate": round(self.sla_violation_rate, 4),
        }


@dataclass
class LagTracker:
    """Tracks ingestion lag for events within a time window."""

    max_lag_threshold_ms: float = 5000.0  # SLA threshold (5 seconds default)
    lag_values: list[float] = field(default_factory=list)
    sla_violation_count: int = 0

    def record_lag(self, lag_ms: float) -> None:
        """
        Record a lag measurement.

        Args:
            lag_ms: Lag in milliseconds
        """
        self.lag_values.append(lag_ms)
        if lag_ms > self.max_lag_threshold_ms:
            self.sla_violation_count += 1

    def calculate_metrics(self) -> dict[str, float]:
        """
        Calculate lag percentiles and statistics.

        Returns:
            dict with avg, max, p50, p99 lag values
        """
        if not self.lag_values:
            return {"avg_ms": 0.0, "max_ms": 0.0, "p50_ms": 0.0, "p99_ms": 0.0}

        sorted_lags = sorted(self.lag_values)
        avg_lag = sum(sorted_lags) / len(sorted_lags)
        max_lag = max(sorted_lags)
        p50_idx = int(len(sorted_lags) * 0.5)
        p99_idx = int(len(sorted_lags) * 0.99)

        return {
            "avg_ms": avg_lag,
            "max_ms": max_lag,
            "p50_ms": sorted_lags[p50_idx] if p50_idx < len(sorted_lags) else 0.0,
            "p99_ms": sorted_lags[p99_idx] if p99_idx < len(sorted_lags) else 0.0,
        }

    def get_sla_violation_rate(self) -> float:
        """
        Get SLA violation rate (violations / total events).

        Returns:
            float between 0.0 and 1.0
        """
        if not self.lag_values:
            return 0.0
        return self.sla_violation_count / len(self.lag_values)


class IngestionMetricsCollector:
    """Collects and aggregates ingestion metrics over time windows."""

    def __init__(self, sla_max_lag_ms: float = 5000.0):
        """
        Initialize metrics collector.

        Args:
            sla_max_lag_ms: SLA threshold for lag (milliseconds)
        """
        self.sla_max_lag_ms = sla_max_lag_ms
        self.events_processed: list[dict[str, Any]] = []
        self.batches_processed: list[dict[str, Any]] = []

    def record_event_ingestion(
        self, event_id: str, event_timestamp: datetime, ingestion_timestamp: datetime
    ) -> float:
        """
        Record event ingestion with lag calculation.

        Args:
            event_id: Unique event identifier
            event_timestamp: Original event timestamp
            ingestion_timestamp: When event was ingested

        Returns:
            float: Calculated lag in milliseconds
        """
        lag_ms = (ingestion_timestamp - event_timestamp).total_seconds() * 1000
        self.events_processed.append(
            {
                "event_id": event_id,
                "event_timestamp": event_timestamp,
                "ingestion_timestamp": ingestion_timestamp,
                "lag_ms": lag_ms,
            }
        )
        return lag_ms

    def record_batch_completion(
        self, batch_id: str, batch_start: datetime, batch_end: datetime, event_count: int
    ) -> None:
        """
        Record batch processing completion.

        Args:
            batch_id: Unique batch identifier
            batch_start: Batch processing start time
            batch_end: Batch processing end time
            event_count: Number of events in batch
        """
        batch_duration_sec = (batch_end - batch_start).total_seconds()
        self.batches_processed.append(
            {
                "batch_id": batch_id,
                "batch_start": batch_start,
                "batch_end": batch_end,
                "event_count": event_count,
                "duration_sec": batch_duration_sec,
                "throughput_events_per_sec": (
                    event_count / batch_duration_sec if batch_duration_sec > 0 else 0
                ),
            }
        )

    def get_metrics_for_window(
        self, window_start: datetime, window_end: datetime
    ) -> IngestionMetrics:
        """
        Get aggregated metrics for a time window.

        Args:
            window_start: Start of time window
            window_end: End of time window

        Returns:
            IngestionMetrics with aggregated stats
        """
        # Filter events in window
        events_in_window = [
            e
            for e in self.events_processed
            if window_start <= e["event_timestamp"] <= window_end
        ]

        # Filter batches in window
        batches_in_window = [
            b
            for b in self.batches_processed
            if window_start <= b["batch_start"] <= window_end
        ]

        if not events_in_window:
            return IngestionMetrics(
                window_start=window_start, window_end=window_end, total_events=0, total_batches=0
            )

        # Calculate lag metrics
        lag_tracker = LagTracker(max_lag_threshold_ms=self.sla_max_lag_ms)
        for event in events_in_window:
            lag_tracker.record_lag(event["lag_ms"])

        lag_stats = lag_tracker.calculate_metrics()

        # Calculate throughput
        window_duration_sec = max((window_end - window_start).total_seconds(), 1)
        throughput_events_per_sec = len(events_in_window) / window_duration_sec
        throughput_batches_per_sec = len(batches_in_window) / window_duration_sec

        return IngestionMetrics(
            window_start=window_start,
            window_end=window_end,
            total_events=len(events_in_window),
            total_batches=len(batches_in_window),
            avg_lag_ms=lag_stats["avg_ms"],
            max_lag_ms=lag_stats["max_ms"],
            p50_lag_ms=lag_stats["p50_ms"],
            p99_lag_ms=lag_stats["p99_ms"],
            throughput_events_per_sec=throughput_events_per_sec,
            throughput_batches_per_sec=throughput_batches_per_sec,
            sla_violations=lag_tracker.sla_violation_count,
            sla_violation_rate=lag_tracker.get_sla_violation_rate(),
        )

    def emit_metrics_log(self, metrics: IngestionMetrics) -> None:
        """
        Emit metrics as structured JSON log.

        Args:
            metrics: IngestionMetrics to log
        """
        log_event = {
            "event": "ingestion_metrics_window_complete",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics.to_dict(),
        }
        logger.info(json.dumps(log_event))

    def reset_for_window(self) -> None:
        """Clear collected metrics for next window (optional)."""
        self.events_processed.clear()
        self.batches_processed.clear()
