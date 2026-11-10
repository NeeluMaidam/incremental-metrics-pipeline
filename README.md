# Incremental Metrics Pipeline

## Project Overview

The **Incremental Metrics Pipeline** is a Python-based data processing solution that processes transaction events and maintains accurate daily business metrics.

It handles `NEW`, `UPDATE`, and `REVERSAL` events, validates incoming records, supports late-arriving events, and recalculates only the affected date and product combinations.

The pipeline uses SQLite for persistent storage and exports calculated metrics as CSV files. It also generates run reports, tracks processing statistics, and supports safe reruns without processing the same events more than once.

## Key Features

- **Event Processing:** Supports NEW, UPDATE, and REVERSAL transaction events.
- **Data Validation:** Validates required fields, event types, amounts, and event versions.
- **Duplicate Handling:** Detects duplicate events and conflicting transaction versions.
- **Incremental Processing:** Recalculates only the affected date and product combinations.
- **Late-Arriving Events:** Handles historical events received after newer events.
- **Idempotency:** Prevents already processed events from being applied again during reruns.
- **Data Persistence:** Stores raw events, processing information, and calculated metrics in SQLite.
- **Run Tracking:** Maintains processing status, counters, and execution details.
- **Reconciliation:** Independently verifies calculated metrics against accepted transaction data.
- **Scalable Test Data:** Includes a generator for creating large transaction datasets.

## Technology Stack

- Python 3.10+
- SQLite
- CSV
- JSON
- Python unittest

No external Python packages are required.

## Project Structure

```text
incremental-metrics-pipeline/
|
|-- data/
|   |-- sample_events.csv
|   |-- large_events.csv
|   |-- duplicate_version.csv
|   |-- empty_events.csv
|   |-- invalid_product.csv
|   |-- schema_change.csv
|
|-- src/
|   |-- database.py
|   |-- pipeline.py
|
|-- tests/
|   |-- test_pipeline.py
|
|-- output/
|   |-- daily_metrics.csv
|   |-- run_report.json
|
|-- database/                 (created automatically)
|
|-- main.py
|-- generate_data.py
|-- reconcile_metrics.py
|-- requirements.txt
|-- DESIGN_NOTES.md
|-- README.md
|-- .gitignore
```

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/NeeluMaidam/incremental-metrics-pipeline.git
cd incremental-metrics-pipeline
```

### 2. Check Python Version

Python 3.10 or later is required.

```bash
python --version
```

### 3. Run the Pipeline

Process the sample transaction events:

```bash
python main.py data/sample_events.csv
```

The pipeline initializes the SQLite database, validates incoming events, processes valid records, updates daily metrics, and generates output reports.

### 4. Generate Large Test Data

To generate a larger transaction dataset:

```bash
python generate_data.py
```

This generates test data for evaluating the pipeline with a larger number of transaction events.

### 5. Run the Pipeline with Large Data

```bash
python main.py data/large_events.csv
```

### 6. Run Reconciliation

```bash
python reconcile_metrics.py
```

The reconciliation process independently verifies the generated metrics against the accepted transaction data and reports any differences.

## Output Files

The pipeline generates the following output files:

| File | Description |
|---|---|
| `output/daily_metrics.csv` | Calculated daily metrics grouped by transaction date and product |
| `output/run_report.json` | Processing status, counters, and run details |
| `output/rejects.csv` | Invalid or rejected transaction events, when generated |

The SQLite database is created automatically when the pipeline runs and stores the data required for incremental processing.

## Testing

Run the automated test suite using:

```bash
python -m unittest discover -s tests -v
```

The test suite covers:

- Event validation
- Invalid amounts and event types
- Missing required fields
- Invalid event versions
- NEW, UPDATE, and REVERSAL processing
- Duplicate event handling
- Conflicting transaction versions
- Late-arriving events
- Missing input files
- Empty input batches
- Idempotent reruns

**Test result:** 13 automated tests passed.

## Performance Testing

The project includes a generated dataset containing 100,000 transaction events to evaluate processing performance and incremental execution.

The large-data test demonstrated:

- 100,000 input events processed successfully.
- 0 rejected events.
- 100,000 events skipped during an identical rerun.
- 0 affected groups during the rerun.
- Successful independent reconciliation with 0 mismatches.

## Design Decisions

The pipeline uses SQLite to maintain persistent processing state and calculated metrics.

Instead of rebuilding every metric after each input batch, it identifies the affected date and product combinations and recalculates only those groups.

Event versions help determine the latest valid transaction state. Reversal events remove transactions from active business metrics, while late-arriving events trigger recalculation of the relevant historical groups.

Additional implementation details, assumptions, trade-offs, and possible improvements are documented in [DESIGN_NOTES.md](DESIGN_NOTES.md).

## Future Improvements

- Optimize large-batch duplicate detection.
- Add database indexing and query optimization.
- Support scheduled and automated pipeline execution.
- Add structured logging and monitoring.
- Extend the pipeline to cloud-based storage and processing.

## Author

**Neelu Maidam**

GitHub: [NeeluMaidam](https://github.com/NeeluMaidam)

Repository: [Incremental Metrics Pipeline](https://github.com/NeeluMaidam/incremental-metrics-pipeline)
