"""
Bronze layer writer abstraction for Spark Structured Streaming.

Supports local JSONL output (mock mode) and future Delta/Iceberg implementations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pyspark.sql import DataFrame


@dataclass(frozen=True)
class BronzeWriterConfig:
    """Configuration for bronze layer writer."""

    mode: str  # "jsonl" (local), "delta" (Delta Lake), "iceberg" (Apache Iceberg)
    output_path: str  # Local path or URI to bronze table/directory
    mode_write: str = "append"  # "append" or "overwrite"
    checkpoint_path: str | None = None  # For streaming checkpoints


class BronzeWriter(ABC):
    """Abstract base class for bronze layer writers."""

    def __init__(self, config: BronzeWriterConfig):
        self.config = config

    @abstractmethod
    def write(self, df: DataFrame) -> dict[str, Any]:
        """
        Write DataFrame to bronze layer.

        Args:
            df: Spark DataFrame to write

        Returns:
            dict with write metrics (rows_written, duration_sec, status)
        """
        pass


class LocalJsonlBronzeWriter(BronzeWriter):
    """Mock bronze writer that outputs to local JSONL files (for testing/local dev)."""

    def __init__(self, config: BronzeWriterConfig):
        super().__init__(config)
        if config.mode != "jsonl":
            raise ValueError(f"LocalJsonlBronzeWriter requires mode='jsonl', got {config.mode}")

    def write(self, df: DataFrame) -> dict[str, Any]:
        """
        Write DataFrame to local JSONL file.

        Args:
            df: Spark DataFrame to write

        Returns:
            dict with write metrics
        """
        output_path = Path(self.config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            row_count = df.count()
            df.write.format("json").mode(self.config.mode_write).save(str(output_path))

            return {
                "rows_written": row_count,
                "output_path": str(output_path),
                "status": "success",
                "writer_type": "local_jsonl",
            }
        except Exception as exc:
            return {
                "rows_written": 0,
                "output_path": str(output_path),
                "status": "failed",
                "error": str(exc),
                "writer_type": "local_jsonl",
            }


def create_bronze_writer(config: BronzeWriterConfig) -> BronzeWriter:
    """
    Factory function to create appropriate bronze writer.

    Args:
        config: BronzeWriterConfig instance

    Returns:
        BronzeWriter implementation based on config.mode
    """
    if config.mode == "jsonl":
        return LocalJsonlBronzeWriter(config)
    else:
        raise ValueError(f"Unsupported bronze writer mode: {config.mode}")
