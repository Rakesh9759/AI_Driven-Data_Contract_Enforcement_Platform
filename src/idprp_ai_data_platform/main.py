"""Entrypoint for platform services during early project phases."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from idprp_ai_data_platform.common.config import AppConfig
from idprp_ai_data_platform.common.exceptions import ConfigurationError
from idprp_ai_data_platform.common.logging_utils import setup_logging


def _resolve_config_path() -> Path:
    env_path = os.getenv("APP_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    return Path(__file__).resolve().parent / "config" / "app_config.json"


def main() -> int:
    config_path = _resolve_config_path()

    try:
        config = AppConfig.from_json_file(config_path)
    except ConfigurationError as exc:
        logging.basicConfig(level=logging.ERROR)
        logging.exception("Failed to load configuration: %s", exc)
        return 1

    setup_logging(config.log_level)
    logger = logging.getLogger("platform.bootstrap")
    logger.info(
        "Platform scaffold initialized",
        extra={
            "app_name": config.app_name,
            "environment": config.environment,
            "config_path": str(config_path),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
