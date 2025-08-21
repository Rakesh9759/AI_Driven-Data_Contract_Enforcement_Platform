"""CLI entrypoint to publish JSONL events via the Kafka producer adapter."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from idprp_ai_data_platform.common.config import AppConfig
from idprp_ai_data_platform.common.exceptions import ConfigurationError
from idprp_ai_data_platform.common.logging_utils import setup_logging
from idprp_ai_data_platform.ingestion.kafka.producer import (
    FileBackedKafkaProducer,
    KafkaProducerSettings,
    ProducerStats,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish JSONL events through producer adapter.")
    parser.add_argument("--input", type=Path, required=True, help="Input JSONL path")
    parser.add_argument("--config", type=Path, required=True, help="App config JSON path")
    parser.add_argument("--topic", default=None, help="Override target topic")
    parser.add_argument(
        "--bootstrap-servers",
        default=None,
        help="Override bootstrap servers for logging/metadata",
    )
    parser.add_argument(
        "--mock-output",
        type=Path,
        default=None,
        help="File sink to emulate producer writes",
    )
    parser.add_argument("--max-records", type=int, default=0, help="Optional limit")
    return parser.parse_args(argv)


def _load_kafka_settings(config_path: Path, args: argparse.Namespace) -> KafkaProducerSettings:
    app_config = AppConfig.from_json_file(config_path).with_env_overrides()
    kafka_payload = app_config.kafka

    if args.topic:
        kafka_payload = {**kafka_payload, "topic": args.topic}
    if args.bootstrap_servers:
        kafka_payload = {**kafka_payload, "bootstrap_servers": args.bootstrap_servers}
    if args.mock_output:
        kafka_payload = {**kafka_payload, "mock_output_path": str(args.mock_output)}

    return KafkaProducerSettings.from_mapping(kafka_payload)


def _iterate_jsonl(path: Path):
    if not path.exists():
        raise ConfigurationError(f"Input JSONL file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            payload = line.strip()
            if not payload:
                continue
            try:
                yield json.loads(payload)
            except json.JSONDecodeError as exc:
                raise ConfigurationError(
                    f"Invalid JSON at line {line_number}: {path}"
                ) from exc


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        settings = _load_kafka_settings(args.config, args)
    except ConfigurationError as exc:
        logging.basicConfig(level=logging.ERROR)
        logging.exception("Producer configuration failed: %s", exc)
        return 1

    setup_logging("INFO", app_name="idprp-ai-data-platform", environment="dev")
    logger = logging.getLogger("ingestion.kafka.producer")

    producer = FileBackedKafkaProducer(settings)
    stats = ProducerStats()

    try:
        for event in _iterate_jsonl(args.input):
            if args.max_records > 0 and stats.published >= args.max_records:
                break
            stats.attempted += 1
            try:
                producer.send(event)
                stats.published += 1
            except OSError:
                stats.failed += 1
                logger.exception("Failed to publish event")
    except ConfigurationError as exc:
        logger.exception("Producer execution failed: %s", exc)
        return 1

    logger.info(
        "Producer run completed",
        extra={
            "topic": settings.topic,
            "bootstrap_servers": settings.bootstrap_servers,
            "mock_output_path": str(settings.mock_output_path),
            "attempted": stats.attempted,
            "published": stats.published,
            "failed": stats.failed,
        },
    )

    if stats.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
