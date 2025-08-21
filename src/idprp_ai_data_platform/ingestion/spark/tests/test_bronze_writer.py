"""Tests for bronze_writer module."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock

from idprp_ai_data_platform.ingestion.spark.bronze_writer import (
    BronzeWriterConfig,
    LocalJsonlBronzeWriter,
    create_bronze_writer,
)


class TestBronzeWriterConfig(unittest.TestCase):
    """Tests for BronzeWriterConfig dataclass."""

    def test_config_creation(self) -> None:
        """Test creating a valid BronzeWriterConfig."""
        config = BronzeWriterConfig(
            mode="jsonl", output_path="/tmp/bronze", mode_write="append"
        )
        self.assertEqual(config.mode, "jsonl")
        self.assertEqual(config.output_path, "/tmp/bronze")
        self.assertEqual(config.mode_write, "append")

    def test_config_frozen(self) -> None:
        """Test that config is immutable (frozen)."""
        config = BronzeWriterConfig(mode="jsonl", output_path="/tmp/bronze")
        with self.assertRaises(AttributeError):
            config.mode = "delta"  # type: ignore

    def test_config_defaults(self) -> None:
        """Test config default values."""
        config = BronzeWriterConfig(mode="jsonl", output_path="/tmp/bronze")
        self.assertEqual(config.mode_write, "append")
        self.assertIsNone(config.checkpoint_path)


class TestLocalJsonlBronzeWriter(unittest.TestCase):
    """Tests for LocalJsonlBronzeWriter."""

    def test_writer_creation(self) -> None:
        """Test creating a LocalJsonlBronzeWriter."""
        config = BronzeWriterConfig(mode="jsonl", output_path="/tmp/bronze")
        writer = LocalJsonlBronzeWriter(config)
        self.assertEqual(writer.config.mode, "jsonl")

    def test_writer_rejects_wrong_mode(self) -> None:
        """Test that writer rejects non-jsonl mode."""
        config = BronzeWriterConfig(mode="delta", output_path="/tmp/bronze")
        with self.assertRaises(ValueError):
            LocalJsonlBronzeWriter(config)

    def test_write_to_local_jsonl_mock(self) -> None:
        """Test write method with mocked DataFrame."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "bronze" / "output"

            config = BronzeWriterConfig(mode="jsonl", output_path=str(output_path))
            writer = LocalJsonlBronzeWriter(config)

            # Create mock DataFrame
            mock_df = Mock()
            mock_df.count.return_value = 5
            mock_write_obj = Mock()
            mock_save_obj = Mock()
            mock_df.write = mock_write_obj
            mock_write_obj.format.return_value = mock_save_obj
            mock_save_obj.mode.return_value = mock_save_obj

            # Write
            result = writer.write(mock_df)

            # Verify result structure
            self.assertIn("status", result)
            self.assertIn("rows_written", result)
            self.assertIn("writer_type", result)
            self.assertEqual(result["writer_type"], "local_jsonl")

    def test_write_failure_handling(self) -> None:
        """Test error handling in write method."""
        config = BronzeWriterConfig(mode="jsonl", output_path="/tmp/bronze")
        writer = LocalJsonlBronzeWriter(config)

        # Create mock DataFrame that raises error on count
        mock_df = Mock()
        mock_df.count.side_effect = Exception("Connection error")

        result = writer.write(mock_df)

        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)


class TestBronzeWriterFactory(unittest.TestCase):
    """Tests for create_bronze_writer factory function."""

    def test_factory_creates_jsonl_writer(self) -> None:
        """Test factory creates LocalJsonlBronzeWriter for jsonl mode."""
        config = BronzeWriterConfig(mode="jsonl", output_path="/tmp/bronze")
        writer = create_bronze_writer(config)
        self.assertIsInstance(writer, LocalJsonlBronzeWriter)

    def test_factory_rejects_unknown_mode(self) -> None:
        """Test factory raises error for unknown mode."""
        config = BronzeWriterConfig(mode="unknown", output_path="/tmp/bronze")
        with self.assertRaises(ValueError):
            create_bronze_writer(config)


if __name__ == "__main__":
    unittest.main()
