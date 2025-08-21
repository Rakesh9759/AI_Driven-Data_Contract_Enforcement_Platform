"""Tests for ingestion_metrics module."""
import unittest
from datetime import datetime, timedelta

from idprp_ai_data_platform.observability.ingestion_metrics import (
    IngestionMetrics,
    LagTracker,
    LatencyBucket,
    IngestionMetricsCollector,
)


class TestLatencyBucket(unittest.TestCase):
    """Tests for LatencyBucket dataclass."""

    def test_bucket_creation(self) -> None:
        """Test creating a latency bucket."""
        bucket = LatencyBucket(min_ms=0.0, max_ms=100.0, count=5)
        self.assertEqual(bucket.min_ms, 0.0)
        self.assertEqual(bucket.max_ms, 100.0)
        self.assertEqual(bucket.count, 5)

    def test_bucket_frozen(self) -> None:
        """Test that bucket is immutable."""
        bucket = LatencyBucket(min_ms=0.0, max_ms=100.0, count=5)
        with self.assertRaises(AttributeError):
            bucket.count = 10  # type: ignore


class TestIngestionMetrics(unittest.TestCase):
    """Tests for IngestionMetrics dataclass."""

    def test_metrics_creation(self) -> None:
        """Test creating metrics."""
        start = datetime(2025, 8, 23, 12, 0, 0)
        end = datetime(2025, 8, 23, 12, 5, 0)

        metrics = IngestionMetrics(
            window_start=start,
            window_end=end,
            total_events=100,
            avg_lag_ms=150.5,
            p99_lag_ms=500.0,
            throughput_events_per_sec=20.0,
        )

        self.assertEqual(metrics.total_events, 100)
        self.assertEqual(metrics.avg_lag_ms, 150.5)

    def test_metrics_to_dict(self) -> None:
        """Test metrics JSON serialization."""
        start = datetime(2025, 8, 23, 12, 0, 0)
        end = datetime(2025, 8, 23, 12, 5, 0)

        metrics = IngestionMetrics(
            window_start=start,
            window_end=end,
            total_events=50,
            avg_lag_ms=123.456,
            sla_violations=2,
        )

        metrics_dict = metrics.to_dict()

        self.assertIn("window_start", metrics_dict)
        self.assertIn("total_events", metrics_dict)
        self.assertEqual(metrics_dict["total_events"], 50)
        self.assertEqual(metrics_dict["avg_lag_ms"], 123.46)


class TestLagTracker(unittest.TestCase):
    """Tests for LagTracker."""

    def test_lag_tracker_creation(self) -> None:
        """Test creating a lag tracker."""
        tracker = LagTracker(max_lag_threshold_ms=3000.0)
        self.assertEqual(tracker.max_lag_threshold_ms, 3000.0)
        self.assertEqual(len(tracker.lag_values), 0)

    def test_record_lag(self) -> None:
        """Test recording lag values."""
        tracker = LagTracker()
        tracker.record_lag(100.0)
        tracker.record_lag(200.0)
        tracker.record_lag(300.0)

        self.assertEqual(len(tracker.lag_values), 3)
        self.assertListEqual(tracker.lag_values, [100.0, 200.0, 300.0])

    def test_sla_violation_detection(self) -> None:
        """Test SLA violation tracking."""
        tracker = LagTracker(max_lag_threshold_ms=1000.0)
        tracker.record_lag(500.0)  # OK
        tracker.record_lag(1500.0)  # Violation
        tracker.record_lag(2000.0)  # Violation
        tracker.record_lag(900.0)  # OK

        self.assertEqual(tracker.sla_violation_count, 2)
        self.assertAlmostEqual(tracker.get_sla_violation_rate(), 0.5, places=2)

    def test_calculate_metrics(self) -> None:
        """Test lag metric calculations."""
        tracker = LagTracker()
        for lag in [100.0, 200.0, 300.0, 400.0, 500.0]:
            tracker.record_lag(lag)

        metrics = tracker.calculate_metrics()

        self.assertEqual(metrics["avg_ms"], 300.0)
        self.assertEqual(metrics["max_ms"], 500.0)
        self.assertGreaterEqual(metrics["p50_ms"], 100.0)
        self.assertLessEqual(metrics["p50_ms"], 500.0)

    def test_empty_lag_tracker(self) -> None:
        """Test metrics on empty tracker."""
        tracker = LagTracker()
        metrics = tracker.calculate_metrics()

        self.assertEqual(metrics["avg_ms"], 0.0)
        self.assertEqual(metrics["max_ms"], 0.0)
        self.assertEqual(tracker.get_sla_violation_rate(), 0.0)


class TestIngestionMetricsCollector(unittest.TestCase):
    """Tests for IngestionMetricsCollector."""

    def test_collector_creation(self) -> None:
        """Test creating a metrics collector."""
        collector = IngestionMetricsCollector(sla_max_lag_ms=4000.0)
        self.assertEqual(collector.sla_max_lag_ms, 4000.0)

    def test_record_event_ingestion(self) -> None:
        """Test recording event ingestion."""
        collector = IngestionMetricsCollector()

        event_ts = datetime(2025, 8, 23, 12, 0, 0)
        ingestion_ts = datetime(2025, 8, 23, 12, 0, 0, 150000)  # 150ms later

        lag_ms = collector.record_event_ingestion("evt_1", event_ts, ingestion_ts)

        self.assertAlmostEqual(lag_ms, 150.0, places=1)
        self.assertEqual(len(collector.events_processed), 1)

    def test_record_batch_completion(self) -> None:
        """Test recording batch processing."""
        collector = IngestionMetricsCollector()

        batch_start = datetime(2025, 8, 23, 12, 0, 0)
        batch_end = datetime(2025, 8, 23, 12, 0, 2)  # 2 seconds

        collector.record_batch_completion("batch_1", batch_start, batch_end, 100)

        self.assertEqual(len(collector.batches_processed), 1)
        batch = collector.batches_processed[0]
        self.assertEqual(batch["event_count"], 100)
        self.assertEqual(batch["duration_sec"], 2.0)
        self.assertAlmostEqual(batch["throughput_events_per_sec"], 50.0, places=1)

    def test_get_metrics_for_window(self) -> None:
        """Test metrics aggregation for time window."""
        collector = IngestionMetricsCollector(sla_max_lag_ms=500.0)

        # Record some events
        base_time = datetime(2025, 8, 23, 12, 0, 0)
        for i in range(5):
            event_ts = base_time + timedelta(seconds=i)
            ingestion_ts = event_ts + timedelta(milliseconds=100 * (i + 1))
            collector.record_event_ingestion(f"evt_{i}", event_ts, ingestion_ts)

        # Record batch
        collector.record_batch_completion("batch_1", base_time, base_time + timedelta(seconds=5), 5)

        # Get metrics for window
        window_start = base_time
        window_end = base_time + timedelta(seconds=10)
        metrics = collector.get_metrics_for_window(window_start, window_end)

        self.assertEqual(metrics.total_events, 5)
        self.assertEqual(metrics.total_batches, 1)
        self.assertGreater(metrics.avg_lag_ms, 0)
        self.assertGreater(metrics.throughput_events_per_sec, 0)

    def test_metrics_outside_window(self) -> None:
        """Test that metrics outside window are excluded."""
        collector = IngestionMetricsCollector()

        base_time = datetime(2025, 8, 23, 12, 0, 0)
        event_ts = base_time + timedelta(hours=1)  # 1 hour later
        ingestion_ts = event_ts + timedelta(milliseconds=100)

        collector.record_event_ingestion("evt_1", event_ts, ingestion_ts)

        # Query for window before the event
        window_start = base_time
        window_end = base_time + timedelta(minutes=30)

        metrics = collector.get_metrics_for_window(window_start, window_end)

        self.assertEqual(metrics.total_events, 0)

    def test_sla_violations_in_window(self) -> None:
        """Test SLA violation counting in window."""
        collector = IngestionMetricsCollector(sla_max_lag_ms=100.0)

        base_time = datetime(2025, 8, 23, 12, 0, 0)

        # Record events with varying lag
        lags = [50.0, 150.0, 75.0, 200.0, 90.0]
        for i, lag in enumerate(lags):
            event_ts = base_time + timedelta(milliseconds=i)
            ingestion_ts = event_ts + timedelta(milliseconds=lag)
            collector.record_event_ingestion(f"evt_{i}", event_ts, ingestion_ts)

        window_start = base_time
        window_end = base_time + timedelta(seconds=1)

        metrics = collector.get_metrics_for_window(window_start, window_end)

        # 2 violations out of 5 events
        self.assertEqual(metrics.sla_violations, 2)
        self.assertAlmostEqual(metrics.sla_violation_rate, 0.4, places=2)

    def test_throughput_calculation(self) -> None:
        """Test throughput metrics calculation."""
        collector = IngestionMetricsCollector()

        base_time = datetime(2025, 8, 23, 12, 0, 0)

        # Record 10 events over 1 second
        for i in range(10):
            event_ts = base_time + timedelta(milliseconds=i * 100)
            ingestion_ts = event_ts + timedelta(milliseconds=10)
            collector.record_event_ingestion(f"evt_{i}", event_ts, ingestion_ts)

        # Record batch completing in 1 second
        collector.record_batch_completion("batch_1", base_time, base_time + timedelta(seconds=1), 10)

        window_start = base_time
        window_end = base_time + timedelta(seconds=1)

        metrics = collector.get_metrics_for_window(window_start, window_end)

        self.assertEqual(metrics.total_events, 10)
        self.assertEqual(metrics.total_batches, 1)
        self.assertGreater(metrics.throughput_events_per_sec, 0)
        self.assertGreater(metrics.throughput_batches_per_sec, 0)

    def test_emit_metrics_log(self) -> None:
        """Test emitting metrics as structured log (no error)."""
        collector = IngestionMetricsCollector()

        base_time = datetime(2025, 8, 23, 12, 0, 0)
        metrics = IngestionMetrics(
            window_start=base_time,
            window_end=base_time + timedelta(minutes=5),
            total_events=100,
        )

        # Should not raise
        collector.emit_metrics_log(metrics)

    def test_reset_for_window(self) -> None:
        """Test resetting collector state."""
        collector = IngestionMetricsCollector()

        base_time = datetime(2025, 8, 23, 12, 0, 0)
        collector.record_event_ingestion("evt_1", base_time, base_time + timedelta(milliseconds=100))

        self.assertEqual(len(collector.events_processed), 1)

        collector.reset_for_window()

        self.assertEqual(len(collector.events_processed), 0)


if __name__ == "__main__":
    unittest.main()
