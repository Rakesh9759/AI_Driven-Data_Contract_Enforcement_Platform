"""Kafka producer abstractions for local and CI-friendly ingestion validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from idprp_ai_data_platform.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class KafkaProducerSettings:
    """Configuration for sending events to the ingestion message bus."""

    bootstrap_servers: str
    topic: str
    client_id: str
    mock_output_path: Path

    @staticmethod
    def from_mapping(payload: Mapping[str, object]) -> "KafkaProducerSettings":
        bootstrap = str(payload.get("bootstrap_servers", "localhost:9092"))
        topic = str(payload.get("topic", "telemetry-events"))
        client_id = str(payload.get("client_id", "idprp-producer"))
        output_path = Path(
            str(payload.get("mock_output_path", "project_files/generated/kafka_events.jsonl"))
        )

        if not bootstrap.strip():
            raise ConfigurationError("bootstrap_servers cannot be empty")
        if not topic.strip():
            raise ConfigurationError("topic cannot be empty")

        return KafkaProducerSettings(
            bootstrap_servers=bootstrap,
            topic=topic,
            client_id=client_id,
            mock_output_path=output_path,
        )


@dataclass
class ProducerStats:
    """Aggregate publish stats emitted as structured logs."""

    attempted: int = 0
    published: int = 0
    failed: int = 0


class FileBackedKafkaProducer:
    """Local file sink that mimics producer semantics for incremental development."""

    def __init__(self, settings: KafkaProducerSettings) -> None:
        self._settings = settings

    @property
    def settings(self) -> KafkaProducerSettings:
        return self._settings

    def send(self, event: dict[str, object]) -> None:
        envelope = {
            "topic": self._settings.topic,
            "client_id": self._settings.client_id,
            "event": event,
        }
        output_path = self._settings.mock_output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(envelope) + "\n")
