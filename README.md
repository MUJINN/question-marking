# Question Marking

A batch AI grading engine designed for throughput, stability, and large-scale processing. The project focuses on concurrent grading, caching, retries, validation, and performance monitoring rather than one-off demo calls.

## What this project does

- Processes folders of question-answer JSON files in batch
- Calls AI services to generate grading results
- Caches reusable intermediate outputs
- Retries failed requests automatically
- Tracks performance metrics during long-running jobs
- Produces structured result summaries for downstream analysis

## Why it matters

The value of this repository is engineering depth. It shows how to turn grading logic into a repeatable batch system with:

- concurrency control
- caching
- retries
- validation
- monitoring

## Main files

- `marking.py`: main grading workflow
- `performance_monitor.py`: runtime metrics and monitoring
- `process_output.py`: output processing and result formatting
- `improved_path_extraction.py`: path and file handling helpers
- `config.json`: runtime configuration

## Repository structure

```text
question-marking/
├── marking.py
├── performance_monitor.py
├── process_output.py
├── improved_path_extraction.py
├── config.json
├── requirements.txt
└── test_*.py
```

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
python marking.py
```

## Key capabilities

- Concurrent batch grading
- Cache and retry mechanisms
- Configurable processing pipeline
- Performance monitoring
- Validation and fault tolerance

## Notes

This public repository is a cleaned release version. Local caches, logs, evaluation outputs, runtime folders, and private environment files were excluded.
