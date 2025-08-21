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
|-- src/
|   `-- idprp_ai_data_platform/
|       |-- common/
|       |-- config/
|       |-- ingestion/
|       `-- main.py
`-- README.md
```

Notes:
- Top-level docs improve repo homepage clarity.
- Runtime Python package remains under src for clean packaging and testability.

## Quick Start
```powershell
$env:PYTHONPATH = "src"
python -m idprp_ai_data_platform.main
```

## Bootstrap Validation (Sample Data)
```powershell
$env:PYTHONPATH = "src"
python -m idprp_ai_data_platform.main --sample-data src/idprp_ai_data_platform/config/sample_events.jsonl
```

## Generate Simulator Data
```powershell
$env:PYTHONPATH = "src"
python -m idprp_ai_data_platform.ingestion.simulators.generate_samples --count 10 --output project_files/generated/simulator_events.jsonl
```

## Kafka Producer Integration
```powershell
$env:PYTHONPATH = "src"
python -m idprp_ai_data_platform.ingestion.kafka.produce_from_jsonl --input project_files/generated/simulator_events.jsonl --config src/idprp_ai_data_platform/config/app_config.json --mock-output project_files/generated/kafka_events.jsonl
```

## Spark Bronze Ingestion
Spark Structured Streaming job for bronze layer ingestion. Note: Spark ingestion requires Java. For testing without Java, run the unit tests below.

```powershell
# Unit tests for Spark ingestion modules
$env:PYTHONPATH = "src"
python -m unittest discover -s src/idprp_ai_data_platform/ingestion/spark/tests -p "test_*.py"
```

Modules:
- Bronze writer abstraction: `src/idprp_ai_data_platform/ingestion/spark/bronze_writer.py`
- Streaming job: `src/idprp_ai_data_platform/ingestion/spark/spark_streaming_job.py`
- Tests: `src/idprp_ai_data_platform/ingestion/spark/tests/`

## Observability: Ingestion Metrics
Tracks ingestion SLA compliance, lag distribution, and throughput for streaming pipelines.

```powershell
# Unit tests for observability metrics
$env:PYTHONPATH = "src"
python -m unittest discover -s src/idprp_ai_data_platform/observability/tests -p "test_*.py"
```

Key metrics tracked:
- Ingestion lag: time from event occurrence to ingestion completion (p50, p99, max)
- Throughput: events/sec and batches/sec aggregated by time window
- SLA violations: events exceeding threshold lag (default 5000ms)

Module:
- Metrics collection: `src/idprp_ai_data_platform/observability/ingestion_metrics.py`
- Tests: `src/idprp_ai_data_platform/observability/tests/`

## Run Simulator Test Suite
```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s src/idprp_ai_data_platform/ingestion/simulators/tests -p "test_*.py"
```

## Curated Simulator Datasets
- Clean sample: src/idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl
- Drifted sample: src/idprp_ai_data_platform/config/datasets/simulator_drifted_sample.jsonl

## Operations Docs
- Architecture: docs/architecture.md
- Problem Statement: docs/problem_statement.md
- Local Runbook: docs/local_runbook.md
