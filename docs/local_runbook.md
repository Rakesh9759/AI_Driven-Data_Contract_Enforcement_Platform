# Local Runbook (Phase 0)

## Prerequisites
- Python 3.10+
- PowerShell terminal

## Bootstrapping
```powershell
$env:PYTHONPATH = "src"
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
$env:PYTHONPATH = "src"
python -m idprp_ai_data_platform.main --sample-data src/idprp_ai_data_platform/config/sample_events.jsonl
```

## Generate Synthetic Events For Local Testing
```powershell
$env:PYTHONPATH = "src"
python -m idprp_ai_data_platform.ingestion.simulators.generate_samples --count 10 --output project_files/generated/simulator_events.jsonl
python -m idprp_ai_data_platform.main --sample-data project_files/generated/simulator_events.jsonl
```

## Run Simulator Tests
```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s src/idprp_ai_data_platform/ingestion/simulators/tests -p "test_*.py"
```

## Publish Events Through Kafka Producer Adapter
```powershell
$env:PYTHONPATH = "src"
python -m idprp_ai_data_platform.ingestion.simulators.generate_samples --count 12 --output project_files/generated/simulator_events_phase2.jsonl
python -m idprp_ai_data_platform.ingestion.kafka.produce_from_jsonl --input project_files/generated/simulator_events_phase2.jsonl --config src/idprp_ai_data_platform/config/app_config.json --mock-output project_files/generated/kafka_events_phase2.jsonl
```

## Validate Curated Datasets
```powershell
$env:PYTHONPATH = "src"
python -m idprp_ai_data_platform.main --sample-data src/idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl
python -m idprp_ai_data_platform.main --sample-data src/idprp_ai_data_platform/config/datasets/simulator_drifted_sample.jsonl
```

Expected result:
- Structured JSON logs printed to stdout
- "Sample data processed successfully" event emitted with rows_processed

## Run Spark Ingestion Tests (Phase 2, C07)
Bronze layer ingestion with Spark Structured Streaming abstraction. Tests validate the streaming job logic without requiring Java/Spark runtime.

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s src/idprp_ai_data_platform/ingestion/spark/tests -p "test_*.py" -v
```

Expected result:
- 24 tests pass (bronze writer config, writer factory, ingestion metrics, job creation, schema inference, mock Kafka reading, transformations, batch tracking, metrics aggregation)
- All tests use mocks to avoid Java dependency

## Spark Module Overview (C07)
- **bronze_writer.py**: Abstract bronze layer writer with LocalJsonlBronzeWriter (mock mode) for local testing and future Delta/Iceberg support
- **spark_streaming_job.py**: BronzeIngestionJob class with schema inference, transformations, batch processing, and metrics tracking
- **Design Pattern**: Config-driven architecture (BronzeWriterConfig) with mock/real switch for flexibility

## End-to-End Data Flow (C01-C07)
```
Simulator (CDR + metrics) → Drift injection → Kafka producer (mock JSONL) → Spark bronze ingestion
```

Raw events: `src/idprp_ai_data_platform/config/datasets/simulator_clean_sample.jsonl` (16 rows)
Drifted events: `src/idprp_ai_data_platform/config/datasets/simulator_drifted_sample.jsonl` (20 rows)
