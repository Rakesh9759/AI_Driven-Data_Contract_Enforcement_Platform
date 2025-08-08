# AI-Driven Data Contract Enforcement Platform

A production-oriented, incrementally built data reliability platform focused on:
- data contract enforcement
- anomaly detection
- AI-assisted root cause analysis

## Phase 0 Scope
This commit establishes a src-first scaffold, baseline configuration and logging utilities, and project architecture/problem framing documentation.

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

## Operations Docs
- Architecture: docs/architecture.md
- Problem Statement: docs/problem_statement.md
- Local Runbook: docs/local_runbook.md
