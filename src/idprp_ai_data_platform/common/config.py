"""Application configuration loading utilities."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from idprp_ai_data_platform.common.exceptions import ConfigurationError


@dataclass(frozen=True)
class AppConfig:
    """Configuration model used by all runtime modules."""

    app_name: str
    environment: str
    log_level: str

    @staticmethod
    def _from_mapping(payload: Mapping[str, object]) -> "AppConfig":
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

    @staticmethod
    def from_json_file(file_path: Path) -> "AppConfig":
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")

        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigurationError(f"Invalid JSON configuration: {file_path}") from exc

        return AppConfig._from_mapping(payload)

    def with_env_overrides(self, env: Mapping[str, str] | None = None) -> "AppConfig":
        source = env or os.environ
        return AppConfig(
            app_name=source.get("APP_NAME", self.app_name),
            environment=source.get("APP_ENVIRONMENT", self.environment),
            log_level=source.get("APP_LOG_LEVEL", self.log_level),
        )
