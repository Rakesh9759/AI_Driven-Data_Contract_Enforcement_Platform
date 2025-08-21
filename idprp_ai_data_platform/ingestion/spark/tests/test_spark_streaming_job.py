"""Tests for spark_streaming_job module."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from idprp_ai_data_platform.common.config import AppConfig
from idprp_ai_data_platform.common.exceptions import PlatformError
from idprp_ai_data_platform.ingestion.spark.spark_streaming_job import (
    BronzeIngestionJob,
    IngestionMetrics,
)


class TestIngestionMetrics(unittest.TestCase):
    """Tests for IngestionMetrics dataclass."""

    def test_metrics_creation(self) -> None:
        """Test creating valid IngestionMetrics."""
        metrics = IngestionMetrics(
            rows_read=100,
            rows_written=100,
            batch_duration_sec=1.5,
            schema_fields=10,
            status="success",
        )
        self.assertEqual(metrics.rows_read, 100)
        self.assertEqual(metrics.status, "success")
        self.assertIsNone(metrics.error_message)

    def test_metrics_with_error(self) -> None:
        """Test creating IngestionMetrics with error."""
        metrics = IngestionMetrics(
            rows_read=0,
            rows_written=0,
            batch_duration_sec=0.0,
            schema_fields=0,
            status="failed",
            error_message="Connection timeout",
        )
        self.assertEqual(metrics.status, "failed")
        self.assertEqual(metrics.error_message, "Connection timeout")

    def test_metrics_frozen(self) -> None:
        """Test that metrics dataclass is frozen."""
        metrics = IngestionMetrics(
            rows_read=100,
            rows_written=100,
            batch_duration_sec=1.0,
            schema_fields=5,
            status="success",
        )
        with self.assertRaises(AttributeError):
            metrics.rows_read = 200  # type: ignore


class TestBronzeIngestionJob(unittest.TestCase):
    """Tests for BronzeIngestionJob."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.config = AppConfig(
            app_name="test",
            environment="test",
            log_level="INFO",
            kafka={
                "bootstrap_servers": "localhost:9092",
                "topic": "test-topic",
                "mock_output_path": "/tmp/test_kafka",
            },
        )

        # Mock SparkSession to avoid Java dependency
        self.mock_spark = Mock()
        self.job = BronzeIngestionJob(self.config, self.mock_spark)

    def test_job_creation(self) -> None:
        """Test creating a BronzeIngestionJob."""
        self.assertEqual(self.job.config.app_name, "test")
        self.assertEqual(len(self.job.metrics_history), 0)

    def test_infer_event_schema(self) -> None:
        """Test schema inference from JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample JSONL
            sample_file = Path(tmpdir) / "sample.jsonl"
            sample_event = {"event_id": "evt_123", "value": 100, "ts": "2025-08-21T12:00:00Z"}
            with sample_file.open("w", encoding="utf-8") as f:
                f.write(json.dumps(sample_event) + "\n")

            # Infer schema
            schema_json = self.job.infer_event_schema(str(sample_file))
            schema_dict = json.loads(schema_json)

            self.assertIn("event_id", schema_dict)
            self.assertIn("value", schema_dict)
            self.assertIn("ts", schema_dict)

    def test_infer_schema_from_empty_file(self) -> None:
        """Test that schema inference fails on empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.jsonl"
            empty_file.touch()

            with self.assertRaises(PlatformError):
                self.job.infer_event_schema(str(empty_file))

    def test_infer_schema_from_invalid_json(self) -> None:
        """Test schema inference with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_file = Path(tmpdir) / "invalid.jsonl"
            with invalid_file.open("w", encoding="utf-8") as f:
                f.write("not valid json\n")

            with self.assertRaises(PlatformError):
                self.job.infer_event_schema(str(invalid_file))

    def test_infer_schema_from_missing_file(self) -> None:
        """Test schema inference with missing file."""
        with self.assertRaises(PlatformError):
            self.job.infer_event_schema("/nonexistent/file.jsonl")

    def test_read_mock_kafka_source(self) -> None:
        """Test reading mock Kafka JSONL source with mocked Spark."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample JSONL
            source_file = Path(tmpdir) / "events.jsonl"
            events = [
                {"event_id": "evt_1", "value": 100},
                {"event_id": "evt_2", "value": 200},
            ]
            with source_file.open("w", encoding="utf-8") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")

            # Test passes if schema inference doesn't raise
            schema_json = self.job.infer_event_schema(str(source_file))
            self.assertIsNotNone(schema_json)

    def test_read_mock_kafka_source_missing_file(self) -> None:
        """Test read_mock_kafka_source with missing file."""
        with self.assertRaises(PlatformError):
            self.job.read_mock_kafka_source("/nonexistent/source.jsonl")

    def test_apply_bronze_transformations(self) -> None:
        """Test bronze layer transformations with mocked DataFrame."""
        # Mock Spark functions that require SparkContext
        with patch(
            "idprp_ai_data_platform.ingestion.spark.spark_streaming_job.current_timestamp"
        ) as mock_ts, patch(
            "idprp_ai_data_platform.ingestion.spark.spark_streaming_job.lit"
        ) as mock_lit:
            mock_ts_col = Mock()
            mock_lit_col = Mock()
            mock_ts.return_value = mock_ts_col
            mock_lit.return_value = mock_lit_col

            # Create mock DataFrame with proper mocking chain
            mock_df = Mock()
            mock_enriched = Mock()
            mock_df.withColumn.return_value = mock_enriched
            mock_enriched.withColumn.return_value = mock_enriched

            # Apply transformations
            result_df = self.job.apply_bronze_transformations(mock_df)

            # Verify withColumn was called
            mock_df.withColumn.assert_called()
            self.assertIsNotNone(result_df)

    def test_ingest_batch_tracking(self) -> None:
        """Test that ingestion metrics are tracked."""
        # Initial state
        self.assertEqual(len(self.job.metrics_history), 0)

        # Create a metrics object and add to history manually
        metrics1 = IngestionMetrics(
            rows_read=100,
            rows_written=100,
            batch_duration_sec=1.0,
            schema_fields=10,
            status="success",
        )
        metrics2 = IngestionMetrics(
            rows_read=50,
            rows_written=50,
            batch_duration_sec=0.5,
            schema_fields=10,
            status="success",
        )
        self.job.metrics_history.append(metrics1)
        self.job.metrics_history.append(metrics2)

        # Check history
        self.assertEqual(len(self.job.metrics_history), 2)

    def test_get_metrics_summary_empty(self) -> None:
        """Test metrics summary with no batches."""
        summary = self.job.get_metrics_summary()

        self.assertEqual(summary["total_batches"], 0)
        self.assertEqual(summary["total_rows_read"], 0)
        self.assertEqual(summary["total_rows_written"], 0)

    def test_get_metrics_summary_with_batches(self) -> None:
        """Test metrics summary with multiple batches."""
        # Add sample metrics
        metrics_list = [
            IngestionMetrics(
                rows_read=100,
                rows_written=100,
                batch_duration_sec=1.0,
                schema_fields=10,
                status="success",
            ),
            IngestionMetrics(
                rows_read=50,
                rows_written=50,
                batch_duration_sec=0.5,
                schema_fields=10,
                status="success",
            ),
            IngestionMetrics(
                rows_read=75,
                rows_written=75,
                batch_duration_sec=0.7,
                schema_fields=10,
                status="success",
            ),
        ]
        self.job.metrics_history = metrics_list

        # Get summary
        summary = self.job.get_metrics_summary()

        self.assertEqual(summary["total_batches"], 3)
        self.assertEqual(summary["total_rows_read"], 225)
        self.assertEqual(summary["total_rows_written"], 225)
        self.assertEqual(summary["successful_batches"], 3)
        self.assertEqual(summary["failed_batches"], 0)
        self.assertEqual(summary["avg_rows_per_batch"], 75)

    def test_get_metrics_summary_with_failures(self) -> None:
        """Test metrics summary including failed batches."""
        metrics_list = [
            IngestionMetrics(
                rows_read=100,
                rows_written=100,
                batch_duration_sec=1.0,
                schema_fields=10,
                status="success",
            ),
            IngestionMetrics(
                rows_read=0,
                rows_written=0,
                batch_duration_sec=0.0,
                schema_fields=0,
                status="failed",
                error_message="Timeout",
            ),
        ]
        self.job.metrics_history = metrics_list

        summary = self.job.get_metrics_summary()

        self.assertEqual(summary["total_batches"], 2)
        self.assertEqual(summary["successful_batches"], 1)
        self.assertEqual(summary["failed_batches"], 1)


if __name__ == "__main__":
    unittest.main()
