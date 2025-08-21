"""CLI to generate simulator output for local validation workflows."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from idprp_ai_data_platform.common.logging_utils import setup_logging
from idprp_ai_data_platform.ingestion.simulators.cdr_simulator import CDREventSimulator
from idprp_ai_data_platform.ingestion.simulators.drift_injector import DriftInjector
from idprp_ai_data_platform.ingestion.simulators.metrics_simulator import MetricsSimulator


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic simulator events.")
    parser.add_argument("--count", type=int, default=25, help="Rows per simulator.")
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Target JSONL file path where merged simulator output is written.",
    )
    parser.add_argument("--seed-cdr", type=int, default=7)
    parser.add_argument("--seed-metrics", type=int, default=11)
    parser.add_argument("--seed-drift", type=int, default=23)
    parser.add_argument("--drift-rate", type=float, default=0.0)
    parser.add_argument("--bad-data-rate", type=float, default=0.0)
    parser.add_argument("--late-event-rate", type=float, default=0.0)
    parser.add_argument("--duplicate-rate", type=float, default=0.0)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    setup_logging(args.log_level, app_name="idprp-ai-data-platform", environment="dev")
    logger = logging.getLogger("simulator.bootstrap")

    if args.count <= 0:
        logger.error("Invalid simulator count", extra={"count": args.count})
        return 1

    try:
        cdr_rows = CDREventSimulator(seed=args.seed_cdr).generate(args.count)
        metrics_rows = MetricsSimulator(seed=args.seed_metrics).generate(args.count)
        injector = DriftInjector(seed=args.seed_drift)
    except ValueError as exc:
        logger.exception("Simulator generation failed: %s", exc)
        return 1

    base_rows = cdr_rows + metrics_rows
    try:
        merged_rows = injector.inject(
            base_rows,
            drift_rate=args.drift_rate,
            bad_data_rate=args.bad_data_rate,
            late_event_rate=args.late_event_rate,
            duplicate_rate=args.duplicate_rate,
        )
    except ValueError as exc:
        logger.exception("Drift injection failed: %s", exc)
        return 1

    _write_jsonl(args.output, merged_rows)

    anomaly_rows = len(merged_rows) - len(base_rows)

    logger.info(
        "Simulator output generated",
        extra={
            "output_path": str(args.output),
            "row_count": len(merged_rows),
            "cdr_count": len(cdr_rows),
            "metrics_count": len(metrics_rows),
            "drift_rate": args.drift_rate,
            "bad_data_rate": args.bad_data_rate,
            "late_event_rate": args.late_event_rate,
            "duplicate_rate": args.duplicate_rate,
            "extra_rows_from_duplicates": anomaly_rows,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
