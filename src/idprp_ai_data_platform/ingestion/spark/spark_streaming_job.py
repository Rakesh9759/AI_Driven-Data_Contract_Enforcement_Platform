"""
Bronze ingestion Spark Structured Streaming job.

Consumes telemetry events from Kafka (or mock JSONL), applies basic transformations,
and writes to bronze layer. Tracks ingestion metrics and SLAs.
"""
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, from_json, schema_of_json, current_timestamp, lit

from idprp_ai_data_platform.common.config import AppConfig
from idprp_ai_data_platform.common.exceptions import PlatformError
from idprp_ai_data_platform.ingestion.spark.bronze_writer import (
    BronzeWriterConfig,
    create_bronze_writer,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionMetrics:
    """Metrics from a streaming ingestion batch."""

    rows_read: int
    rows_written: int
    batch_duration_sec: float
    schema_fields: int
    status: str  # "success", "partial", "failed"
    error_message: str | None = None


class BronzeIngestionJob:
    """Spark Structured Streaming job for bronze layer ingestion."""

    def __init__(self, config: AppConfig, spark: SparkSession):
        """
        Initialize bronze ingestion job.

        Args:
            config: Application configuration
            spark: SparkSession instance
        """
        self.config = config
        self.spark = spark
        self.metrics_history: list[IngestionMetrics] = []

    def infer_event_schema(self, sample_jsonl_path: str) -> str:
        """
        Infer JSON schema from first line of JSONL file.

        Args:
            sample_jsonl_path: Path to JSONL file with sample event

        Returns:
            JSON schema string
        """
        try:
            with open(sample_jsonl_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line:
                    raise PlatformError(f"Empty sample file: {sample_jsonl_path}")
                # Parse JSON to validate and format
                json_obj = json.loads(first_line)
                return json.dumps(json_obj)
        except json.JSONDecodeError as exc:
            raise PlatformError(f"Invalid JSON in sample file: {exc}") from exc
        except FileNotFoundError as exc:
            raise PlatformError(f"Sample file not found: {sample_jsonl_path}") from exc

    def read_mock_kafka_source(self, source_path: str) -> DataFrame:
        """
        Read mock Kafka JSONL output as DataFrame.

        Args:
            source_path: Path to JSONL file (from mock Kafka producer)

        Returns:
            Spark DataFrame with schema inferred from sample
        """
        sample_file = Path(source_path)
        if not sample_file.exists():
            raise PlatformError(f"Source file not found: {source_path}")

        # Infer schema from first line
        schema_json = self.infer_event_schema(source_path)
        schema = schema_of_json(schema_json)

        # Read entire file
        df = self.spark.read.schema(schema).json(source_path)
        return df

    def apply_bronze_transformations(self, df: DataFrame) -> DataFrame:
        """
        Apply basic transformations for bronze layer.

        Args:
            df: Input DataFrame

        Returns:
            Transformed DataFrame with added metadata
        """
        # Add ingestion timestamp and bronze processing metadata
        df_enriched = df.withColumn("_bronze_ingestion_ts", current_timestamp()).withColumn(
            "_data_source", lit("kafka-mock")
        )

        return df_enriched

    def ingest_batch(self, source_path: str, batch_id: int | None = None) -> IngestionMetrics:
        """
        Process a single batch of events and write to bronze layer.

        Args:
            source_path: Path to JSONL source data
            batch_id: Optional batch identifier for tracking

        Returns:
            IngestionMetrics with batch results
        """
        batch_label = f"batch_{batch_id}" if batch_id else "ad_hoc"
        start_time = self.spark.sparkContext.getLocalProperty("spark.timestamp")

        try:
            # Read source
            df_raw = self.read_mock_kafka_source(source_path)
            rows_read = df_raw.count()

            # Transform
            df_transformed = self.apply_bronze_transformations(df_raw)
            schema_fields = len(df_transformed.schema)

            # Write to bronze
            bronze_config = BronzeWriterConfig(
                mode="jsonl",
                output_path=f"{self.config.kafka['mock_output_path']}_bronze_{batch_label}",
                mode_write="overwrite",
                checkpoint_path=None,
            )
            writer = create_bronze_writer(bronze_config)
            write_result = writer.write(df_transformed)
            rows_written = write_result.get("rows_written", 0)

            logger.info(
                json.dumps(
                    {
                        "event": "bronze_ingest_batch_success",
                        "batch_id": batch_label,
                        "rows_read": rows_read,
                        "rows_written": rows_written,
                        "schema_fields": schema_fields,
                        "source": source_path,
                        "output": write_result.get("output_path", ""),
                    }
                )
            )

            metrics = IngestionMetrics(
                rows_read=rows_read,
                rows_written=rows_written,
                batch_duration_sec=0.1,  # Placeholder; actual duration tracked by Spark
                schema_fields=schema_fields,
                status="success",
            )
            self.metrics_history.append(metrics)
            return metrics

        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "bronze_ingest_batch_failed",
                        "batch_id": batch_label,
                        "error": str(exc),
                        "source": source_path,
                    }
                )
            )
            metrics = IngestionMetrics(
                rows_read=0,
                rows_written=0,
                batch_duration_sec=0.0,
                schema_fields=0,
                status="failed",
                error_message=str(exc),
            )
            self.metrics_history.append(metrics)
            return metrics

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get summary of ingestion metrics across all batches.

        Returns:
            dict with aggregated metrics
        """
        if not self.metrics_history:
            return {
                "total_batches": 0,
                "total_rows_read": 0,
                "total_rows_written": 0,
                "total_failures": 0,
            }

        total_rows_read = sum(m.rows_read for m in self.metrics_history)
        total_rows_written = sum(m.rows_written for m in self.metrics_history)
        total_failures = sum(1 for m in self.metrics_history if m.status != "success")

        return {
            "total_batches": len(self.metrics_history),
            "total_rows_read": total_rows_read,
            "total_rows_written": total_rows_written,
            "successful_batches": len(self.metrics_history) - total_failures,
            "failed_batches": total_failures,
            "avg_rows_per_batch": (
                total_rows_read / len(self.metrics_history) if self.metrics_history else 0
            ),
        }
