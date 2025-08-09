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

Expected result:
- Structured JSON logs printed to stdout
- "Sample data processed successfully" event emitted with rows_processed
