# Architecture Overview (Phase 0)

## Intent
Build an incremental, production-grade data reliability platform with clear module boundaries and operational visibility.

## High-Level Flow
1. Simulation and ingestion modules generate and capture streaming events.
2. Contract modules validate schema and quality constraints.
3. Observability modules expose reliability metrics and violations.
4. ML modules detect anomalous behavior.
5. AI modules generate root cause guidance and contract evolution suggestions.

## Baseline Module Layout
- idprp_ai_data_platform/common: shared config, logging, and exception utilities.
- idprp_ai_data_platform/config: environment-driven runtime configuration.
- idprp_ai_data_platform/contracts: YAML contract definitions and typed loading utilities.
- idprp_ai_data_platform/ingestion/simulators: CDR, metrics, and drift simulators for data generation.
- idprp_ai_data_platform/ingestion/kafka: Kafka producer abstraction with mock JSONL output.
- idprp_ai_data_platform/ingestion/spark: Spark Structured Streaming for bronze layer ingestion.
- idprp_ai_data_platform/observability: Ingestion metrics tracking (lag, throughput, SLA compliance).
- docs: architecture and problem framing docs tracked as part of Phase 0.

## Streaming Ingestion Layer

### Kafka Producer
Abstracted producer interface with mock JSONL output for local development, enabling testing without infrastructure.

### Spark Bronze Ingestion
Structured Streaming job consuming from Kafka mock, applying basic transformations, writing to bronze layer with metrics tracking.

### Spark Ingestion Design
- **BronzeWriterConfig**: Frozen dataclass controlling writer mode (jsonl/delta/iceberg) and output path.
- **BronzeWriter**: Abstract base class with factory pattern for extensibility.
- **LocalJsonlBronzeWriter**: Mock implementation writing to local JSONL (no Java required).
- **BronzeIngestionJob**: Main streaming job class orchestrating schema inference, transformations, and metrics.
- **IngestionMetrics**: Dataclass tracking rows_read, rows_written, batch_duration, schema_fields, status.

Metrics aggregation via `get_metrics_summary()` provides total_batches, total_rows, success/failure counts, and avg throughput.

## Observability: SLA Metrics

### Ingestion Metrics Module
Tracks time-windowed ingestion performance and SLA compliance for bronze layer ingest jobs.

### Observability Design
- **LagTracker**: Records individual event lags (ms from event occurrence to ingestion), computes p50/p99 percentiles, counts SLA violations against threshold.
- **IngestionMetrics**: Frozen dataclass aggregating window metrics: avg/max/p50/p99 lag, throughput (events/sec, batches/sec), violation count and rate.
- **IngestionMetricsCollector**: Main collector class with methods to record individual events and batch completion, retrieve window-scoped metrics, emit structured logs.
- **SLA Threshold**: Default 5000ms configurable per collector instance; violations counted when lag_ms > threshold.

Integration:
- BronzeIngestionJob instantiates IngestionMetricsCollector(sla_max_lag_ms) in __init__.
- For each ingested batch, job calls record_batch_completion(batch_id, batch_start, batch_end, event_count).
- Metrics retrieved via get_metrics_for_window(window_start, window_end) returning IngestionMetrics.
- Structured logs emitted via emit_metrics_log(metrics) with p50/p99 lag percentiles.

## Contract Definitions

### YAML Contract Layer
Contract definitions are stored as YAML so schema expectations and governance rules remain declarative and versionable.

### Contract Model
- **DataContract**: Root contract object containing dataset name, version, owners, schema, quality rules, and freshness requirements.
- **ContractField**: Field-level schema definition with name, type, nullability, and description.
- **QualityRule**: Field-level data quality expectations, including required fields, null thresholds, and duplicate tolerance.
- **FreshnessRule**: Dataset-level freshness expectation expressed as maximum ingestion lag in milliseconds.

### Loading and Validation
- **load_contract_from_yaml**: Parses one YAML contract file into a typed DataContract.
- **load_contracts_from_directory**: Loads all YAML contract definitions in a directory keyed by dataset name.
- **ContractDefinitionError**: Raised for missing files, invalid YAML, missing required keys, empty schema definitions, and invalid rule thresholds.

Initial contract coverage includes `cdr_events` and `device_metrics`, which will be consumed by schema and quality validators in the next commit.

## Design Principles
- Config-driven behavior over hardcoded runtime values.
- Structured logging for machine parsing.
- Small, testable modules and iterative delivery.
