"""Application configuration loading utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from idprp_ai_data_platform.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class AppConfig:
    """Configuration model used by all runtime modules."""

    app_name: str
    environment: str
    log_level: str

    @staticmethod
    def from_json_file(file_path: Path) -> "AppConfig":
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")

        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"Invalid JSON configuration: {file_path}") from exc

        required_keys = {"app_name", "environment", "log_level"}
        missing = sorted(required_keys.difference(payload.keys()))
        if missing:
            raise ConfigurationError(
                "Missing required configuration keys: " + ", ".join(missing)
            )

        return AppConfig(
            app_name=str(payload["app_name"]),
            environment=str(payload["environment"]),
            log_level=str(payload["log_level"]),
        )
