# Local Runbook (Phase 0)

## Prerequisites
- Python 3.10+
- PowerShell terminal

## Bootstrapping
```powershell
python -m idprp_ai_data_platform.main
```

## Optional Environment Overrides
```powershell
$env:APP_NAME = "idprp-ai-data-platform-local"
$env:APP_ENVIRONMENT = "local"
$env:APP_LOG_LEVEL = "DEBUG"
python -m idprp_ai_data_platform.main
```

## Smoke Validation With Sample Data
```powershell
python -m idprp_ai_data_platform.main --sample-data idprp_ai_data_platform/config/sample_events.jsonl
```

## Generate Synthetic Events For Local Testing
```powershell
python -m idprp_ai_data_platform.ingestion.simulators.generate_samples --count 10 --output project_files/generated/simulator_events.jsonl
python -m idprp_ai_data_platform.main --sample-data project_files/generated/simulator_events.jsonl
```

## Run Simulator Tests
```powershell
python -m unittest discover -s idprp_ai_data_platform/ingestion/simulators/tests -p "test_*.py"
```

## Publish Events Through Kafka Producer Adapter
```powershell
python -m idprp_ai_data_platform.ingestion.simulators.generate_samples --count 12 --output project_files/generated/simulator_events_phase2.jsonl
python -m idprp_ai_data_platform.ingestion.kafka.produce_from_jsonl --input project_files/generated/simulator_events_phase2.jsonl --config idprp_ai_data_platform/config/app_config.json --mock-output project_files/generated/kafka_events_phase2.jsonl
```

## Validate Curated Datasets
```powershell
python -m idprp_ai_data_platform.main --sample-data idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl
python -m idprp_ai_data_platform.main --sample-data idprp_ai_data_platform/config/datasets/simulator_drifted_sample.jsonl
```

Expected result:
- Structured JSON logs printed to stdout
- "Sample data processed successfully" event emitted with rows_processed

## Run Spark Ingestion Tests
Bronze layer ingestion with Spark Structured Streaming abstraction. Tests validate the streaming job logic without requiring Java/Spark runtime.

```powershell
python -m unittest discover -s idprp_ai_data_platform/ingestion/spark/tests -p "test_*.py" -v
```

Expected result:
- 24 tests pass (bronze writer config, writer factory, ingestion metrics, job creation, schema inference, mock Kafka reading, transformations, batch tracking, metrics aggregation)
- All tests use mocks to avoid Java dependency

## Spark Module Overview 
- **bronze_writer.py**: Abstract bronze layer writer with LocalJsonlBronzeWriter (mock mode) for local testing and future Delta/Iceberg support
- **spark_streaming_job.py**: BronzeIngestionJob class with schema inference, transformations, batch processing, and metrics tracking
- **Design Pattern**: Config-driven architecture (BronzeWriterConfig) with mock/real switch for flexibility

## Run Observability Metrics Tests
Ingestion lag and throughput metrics for SLA tracking. Tests validate lag calculation, percentile computation, and batch throughput aggregation.

```powershell
python -m unittest discover -s idprp_ai_data_platform/observability/tests -p "test_*.py" -v
```

Expected result:
- 18 tests pass (LatencyBucket, IngestionMetrics creation/serialization, LagTracker record/calculate/violation, IngestionMetricsCollector record/window/emit)
- All tests validate lag, throughput, and SLA compliance logic

## Observability Module Overview
- **ingestion_metrics.py**: IngestionMetricsCollector for tracking event lag, batch throughput, and SLA violations
- **LagTracker**: Maintains lag values, computes p50/p99, tracks SLA violations vs threshold (default 5000ms)
- **IngestionMetrics**: Time-windowed aggregated metrics (avg/max/p50/p99 lag, events/batches per sec, violation rate)
- **Integration**: BronzeIngestionJob calls `record_event_ingestion()` per event and `record_batch_completion()` per batch

## Run Contract Definition Tests
YAML-backed contract definitions validate dataset schema, quality rules, and freshness thresholds before runtime enforcement is introduced.

```powershell
python -m unittest discover -s idprp_ai_data_platform/contracts/tests -p "test_*.py" -v
```

Expected result:
- 10 tests pass covering valid contract loading, malformed YAML, missing required keys, invalid quality thresholds, invalid freshness rules, and directory loading

## Contract Module Overview
- **contracts/definitions/cdr_events.yaml**: Contract for CDR ingestion events with schema, quality rules, and freshness SLA
- **contracts/definitions/device_metrics.yaml**: Contract for telemetry metric events with schema and freshness SLA
- **contracts/definitions/loader.py**: Typed YAML loader producing DataContract, ContractField, QualityRule, and FreshnessRule objects
- **common/exceptions.py**: ContractDefinitionError for malformed or missing contracts

## SLA Configuration
Default thresholds set in [idprp_ai_data_platform/common/config.py](../idprp_ai_data_platform/common/config.py):
- Ingestion lag SLA: 5000ms (configurable via `IngestionMetricsCollector(sla_max_lag_ms=...)`
- Time window: 5 minutes (window_start/window_end passed to `get_metrics_for_window()`)

Example: To get 10-minute window metrics for 2025-08-23 12:00-12:10:
```python
from datetime import datetime
metrics = collector.get_metrics_for_window(
    datetime(2025, 8, 23, 12, 0, 0),
    datetime(2025, 8, 23, 12, 10, 0)
)
collector.emit_metrics_log(metrics)  # Emits as structured JSON log
```

## End-to-End Data Flow 
```
Simulator (CDR + metrics) → Drift injection → Kafka producer (mock JSONL) → Spark bronze ingestion → Ingestion metrics
```

Raw events: [idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl](../idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl) (16 rows)
Drifted events: [idprp_ai_data_platform/config/datasets/simulator_drifted_sample.jsonl](../idprp_ai_data_platform/config/datasets/simulator_drifted_sample.jsonl) (20 rows)
