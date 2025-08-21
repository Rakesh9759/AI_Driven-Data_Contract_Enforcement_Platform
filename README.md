# AI-Driven Data Contract Enforcement Platform

A production-oriented, incrementally built data reliability platform focused on:
- data contract enforcement
- anomaly detection
- AI-assisted root cause analysis

## Repository Layout
```text
.
|-- docs/
|   |-- architecture.md
|   |-- local_runbook.md
|   `-- problem_statement.md
|-- idprp_ai_data_platform/
|   |-- common/
|   |-- config/
|   |-- contracts/
|   |-- ingestion/
|   |-- observability/
|   `-- main.py
`-- README.md
```

Notes:
- Top-level docs improve repo homepage clarity.
- All modules are independent and located at the root level.

## Quick Start
```powershell
python -m idprp_ai_data_platform.main
```

## Bootstrap Validation (Sample Data)
```powershell
python -m idprp_ai_data_platform.main --sample-data idprp_ai_data_platform/config/sample_events.jsonl
```

## Generate Simulator Data
```powershell
python -m idprp_ai_data_platform.ingestion.simulators.generate_samples --count 10 --output project_files/generated/simulator_events.jsonl
```

## Kafka Producer Integration
```powershell
python -m idprp_ai_data_platform.ingestion.kafka.produce_from_jsonl --input project_files/generated/simulator_events.jsonl --config idprp_ai_data_platform/config/app_config.json --mock-output project_files/generated/kafka_events.jsonl
```

## Spark Bronze Ingestion
Spark Structured Streaming job for bronze layer ingestion. Note: Spark ingestion requires Java. For testing without Java, run the unit tests below.

```powershell
# Unit tests for Spark ingestion modules
python -m unittest discover -s idprp_ai_data_platform/ingestion/spark/tests -p "test_*.py"
```

Modules:
- Bronze writer abstraction: [idprp_ai_data_platform/ingestion/spark/bronze_writer.py](idprp_ai_data_platform/ingestion/spark/bronze_writer.py)
- Streaming job: [idprp_ai_data_platform/ingestion/spark/spark_streaming_job.py](idprp_ai_data_platform/ingestion/spark/spark_streaming_job.py)
- Tests: [idprp_ai_data_platform/ingestion/spark/tests/](idprp_ai_data_platform/ingestion/spark/tests/)

## Observability: Ingestion Metrics
Tracks ingestion SLA compliance, lag distribution, and throughput for streaming pipelines.

```powershell
# Unit tests for observability metrics
python -m unittest discover -s idprp_ai_data_platform/observability/tests -p "test_*.py"
```

Key metrics tracked:
- Ingestion lag: time from event occurrence to ingestion completion (p50, p99, max)
- Throughput: events/sec and batches/sec aggregated by time window
- SLA violations: events exceeding threshold lag (default 5000ms)

Module:
- Metrics collection: [idprp_ai_data_platform/observability/ingestion_metrics.py](idprp_ai_data_platform/observability/ingestion_metrics.py)
- Tests: [idprp_ai_data_platform/observability/tests/](idprp_ai_data_platform/observability/tests/)

## Data Contracts
YAML-backed dataset contracts define the expected schema, field quality rules, and freshness thresholds for streaming datasets.

```powershell
python -m unittest discover -s idprp_ai_data_platform/contracts/tests -p "test_*.py"
```

Contract assets:
- Definitions: [idprp_ai_data_platform/contracts/definitions/](idprp_ai_data_platform/contracts/definitions/)
- Loader: [idprp_ai_data_platform/contracts/definitions/loader.py](idprp_ai_data_platform/contracts/definitions/loader.py)
- Validators: [idprp_ai_data_platform/contracts/validators/](idprp_ai_data_platform/contracts/validators/)
- Tests: [idprp_ai_data_platform/contracts/tests/](idprp_ai_data_platform/contracts/tests/)

Current sample contracts:
- [idprp_ai_data_platform/contracts/definitions/cdr_events.yaml](idprp_ai_data_platform/contracts/definitions/cdr_events.yaml)
- [idprp_ai_data_platform/contracts/definitions/device_metrics.yaml](idprp_ai_data_platform/contracts/definitions/device_metrics.yaml)

Validation coverage now includes:
- Schema validation: missing fields, nullability, and type mismatches
- Quality validation: required fields, null thresholds, duplicates, and freshness lag breaches

Runtime enforcement is available through the platform entry point:

```powershell
python -m idprp_ai_data_platform.main --sample-data idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl --contract-dataset cdr_events --observed-max-lag-ms 1000
```

Runtime enforcement assets:
- Engine: [idprp_ai_data_platform/contracts/enforcement/contract_engine.py](idprp_ai_data_platform/contracts/enforcement/contract_engine.py)
- Contract-aware CLI: [idprp_ai_data_platform/main.py](idprp_ai_data_platform/main.py)

## Run Simulator Test Suite
```powershell
python -m unittest discover -s idprp_ai_data_platform/ingestion/simulators/tests -p "test_*.py"
```

## Curated Simulator Datasets
- Clean sample: [idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl](idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl)
- Drifted sample: [idprp_ai_data_platform/config/datasets/simulator_drifted_sample.jsonl](idprp_ai_data_platform/config/datasets/simulator_drifted_sample.jsonl)

## Operations Docs
- Architecture: docs/architecture.md
- Problem Statement: docs/problem_statement.md
- Local Runbook: docs/local_runbook.md
