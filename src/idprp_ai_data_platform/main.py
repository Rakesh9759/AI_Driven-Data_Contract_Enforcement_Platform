"""Entrypoint for platform services during early project phases."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from idprp_ai_data_platform.common.config import AppConfig
from idprp_ai_data_platform.common.exceptions import ConfigurationError
from idprp_ai_data_platform.common.logging_utils import setup_logging


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the platform runtime.")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional path to app config JSON. Falls back to APP_CONFIG_PATH or default config.",
    )
    parser.add_argument(
        "--sample-data",
        type=Path,
        default=None,
        help="Optional JSONL file to parse for bootstrap smoke validation.",
    )
    return parser.parse_args(argv)


def _resolve_config_path(cli_path: Path | None = None) -> Path:
    if cli_path:
        return cli_path

    env_path = os.getenv("APP_CONFIG_PATH")
    if env_path:
        return Path(env_path)

    return Path(__file__).resolve().parent / "config" / "app_config.json"


def _process_sample_data(sample_data_path: Path) -> int:
    logger = logging.getLogger("platform.bootstrap")
    if not sample_data_path.exists():
        raise ConfigurationError(f"Sample data file not found: {sample_data_path}")

    processed_rows = 0
    with sample_data_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            content = line.strip()
            if not content:
                continue
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                raise ConfigurationError(
                    f"Invalid JSON in sample data at line {line_number}: {sample_data_path}"
                ) from exc
            processed_rows += 1

    logger.info(
        "Sample data processed successfully",
        extra={
            "sample_data_path": str(sample_data_path),
            "rows_processed": processed_rows,
        },
    )
    return processed_rows


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    config_path = _resolve_config_path(args.config)

    try:
        config = AppConfig.from_json_file(config_path).with_env_overrides()
    except ConfigurationError as exc:
        logging.basicConfig(level=logging.ERROR)
        logging.exception("Failed to load configuration: %s", exc)
        return 1

    setup_logging(
        config.log_level,
        app_name=config.app_name,
        environment=config.environment,
    )
    logger = logging.getLogger("platform.bootstrap")
    logger.info(
        "Platform scaffold initialized",
        extra={
            "app_name": config.app_name,
            "environment": config.environment,
            "config_path": str(config_path),
        },
    )

    if args.sample_data is not None:
        try:
            _process_sample_data(args.sample_data)
        except ConfigurationError as exc:
            logger.exception("Bootstrap validation failed: %s", exc)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
