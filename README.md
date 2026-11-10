# Incremental Metrics Pipeline

## Project Overview

The Incremental Metrics Pipeline is a Python-based data processing solution that processes transaction events and maintains accurate daily business metrics.

It handles NEW, UPDATE, and REVERSAL events, validates incoming records, supports late-arriving events, and recalculates only the affected date and product combinations.

The pipeline uses SQLite for persistent storage and exports calculated metrics as CSV and execution details as JSON.

## Key Features

- **Incremental Processing:** Processes incoming transaction events without rebuilding all historical metrics.
- **Event Lifecycle Management:** Supports NEW, UPDATE, and REVERSAL events.
- **Data Validation:** Identifies invalid records, missing fields, negative amounts, and invalid event versions.
- **Duplicate Detection:** Skips previously processed events and detects conflicting duplicate event IDs.
- **Late-Arriving Events:** Recalculates metrics for historical dates when delayed events arrive.
- **Daily Metrics:** Calculates transaction count, total revenue, and average transaction value by date and product.
- **Run Tracking:** Records execution status, event counters, timestamps, and errors.
- **Reject Handling:** Stores invalid events for inspection and traceability.
- **Idempotency:** Reprocessing the same input does not create duplicate records or change the metrics.
- **Independent Reconciliation:** Compares pipeline output with independently calculated metrics.

## Technology Stack

- Python
- SQLite
- SQL
- CSV
- JSON
- Python unittest

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
|-- database/
|   |-- metrics.db
|
|-- output/
|   |-- daily_metrics.csv
|   |-- run_report.json
|
|-- src/
|   |-- database.py
|   |-- pipeline.py
|
|-- tests/
|   |-- test_pipeline.py
|
|-- main.py
|-- generate_data.py
|-- reconcile_metrics.py
|-- requirements.txt
|-- README.md
```

## Event Types

| Event | Description |
|---|---|
| NEW | Creates a new transaction |
| UPDATE | Updates an existing active transaction |
| REVERSAL | Reverses a transaction so it is excluded from active metrics |

## Input Data Format

The input CSV contains the following fields:

```text
event_id,
transaction_id,
product_id,
customer_id,
event_type,
amount,
event_version,
transaction_date,
event_timestamp
```

Each event has a unique event ID and a transaction version to support event ordering and lifecycle management.

## Database Schema

The pipeline uses SQLite to store incoming events, maintain transaction states, and generate daily metrics.

### Main Tables

| Table | Purpose |
|---|---|
| products | Stores valid product reference data |
| pipeline_runs | Tracks each pipeline execution and its status |
| raw_events | Stores accepted incoming events |
| current_transactions | Maintains the latest state of each transaction |
| daily_product_metrics | Stores aggregated daily product metrics |
| rejected_events | Stores rejected records with their rejection reasons |

### Key Constraints

- `event_id` uniquely identifies an event.
- `(transaction_id, event_version)` prevents duplicate transaction versions.
- `transaction_id` identifies a transaction in the current state table.
- `(metric_date, product_id)` uniquely identifies a daily product metric.
- Foreign keys maintain relationships between pipeline runs and event records.

## Data Assumptions

- Each event must have a unique event ID.
- Each transaction is identified by a unique transaction ID.
- Transaction versions start from 1 and increase with every update or reversal.
- Event types are limited to NEW, UPDATE, and REVERSAL.
- Transaction amounts must be non-negative and have at most two decimal places.
- Transaction dates use the `YYYY-MM-DD` format.
- Event timestamps use ISO 8601 format.
- Only products present in the product reference table are accepted.
- Reversal events make transactions inactive, excluding them from daily metrics.
- Late-arriving events are processed using their transaction dates, not their arrival dates.

## Data Quality and Reject Handling

The pipeline validates every incoming event before processing it.

Records are rejected when they contain:

- Missing required fields
- Invalid or negative transaction amounts
- Unsupported event types
- Invalid transaction versions
- Invalid date or timestamp formats
- Unknown product IDs
- Conflicting duplicate event IDs
- Duplicate transaction event versions

Rejected records are stored in the `rejected_events` table with:

- Pipeline run ID
- Source file name
- Original event data
- Rejection reason
- Rejection timestamp

This allows rejected records to be traced and investigated without silently losing data.

## Pipeline Run Report

After each execution, the pipeline generates `output/run_report.json`.

The report provides:

- Run ID and execution timestamps
- Input file name
- Total input events
- Accepted event count
- Rejected event count
- Duplicate event count
- Number of affected metric groups
- Final execution status
- Error details, if any

This report helps monitor pipeline execution, identify failures, and track data quality.

## Rerun, Recovery, and Backfill

- The pipeline uses SQLite to persist previously processed events.
- Reprocessing the same input file skips already processed events.
- Duplicate events do not create duplicate transaction records or affect metrics again.
- If a run fails, its status and error details are recorded.
- After correcting an input or resolving an issue, the pipeline can be executed again.
- Historical events can be supplied through an input CSV to recalculate the affected date and product metrics.

The pipeline uses event versions to maintain transaction state and supports late-arriving events without rebuilding all historical metrics.

## Metrics Generated

The pipeline generates daily metrics grouped by transaction date and product.

| Metric | Description |
|---|---|
| total_transactions | Number of active transactions |
| total_revenue | Sum of active transaction amounts |
| average_transaction | Average amount per active transaction |

Output file: `output/daily_metrics.csv`

## Installation and Execution

### Prerequisites

- Python 3.10 or later
- SQLite (included with Python's standard library)
- A code editor such as VS Code

The project uses Python standard-library modules and SQLite. No external Python packages are currently required.

### 1. Clone the Repository

```bash
git clone <your-github-repository-url>
cd incremental-metrics-pipeline
```

### 2. Run the Sample Pipeline

```bash
python main.py
```

### 3. Generate Large-Scale Test Data

```bash
python generate_data.py
```

The generator creates a reproducible dataset containing 100,000 transaction events.

### 4. Run the Pipeline on Large Data

```bash
python main.py data/large_events.csv
```

### 5. Run Independent Reconciliation

```bash
python reconcile_metrics.py
```

This independently calculates expected metrics and compares them with the pipeline output.

### 6. Run Automated Tests

```bash
python -m unittest discover -s tests -v
```

## Performance and Testing Results

The pipeline was tested using a generated dataset containing 100,000 events.

### Large Dataset Execution

| Measurement | Result |
|---|---:|
| Input events | 100,000 |
| Accepted events | 100,000 |
| Rejected events | 0 |
| Duplicate events on first run | 0 |
| Affected metric groups | 30 |
| First-run execution time | Approximately 4.26 seconds |
| Active transactions in combined dataset | 25,004 |
| Independent reconciliation mismatches | 0 |

### Idempotency Test

The same 100,000-event input was processed a second time.

| Measurement | Result |
|---|---:|
| Input events | 100,000 |
| Newly accepted events | 0 |
| Duplicate events skipped | 100,000 |
| Affected metric groups | 0 |
| Pipeline status | SUCCESS |
| Second-run execution time | Approximately 21.67 seconds |

The second run correctly skipped all previously processed events without creating duplicate records or changing the metrics.

The second run took longer than the first run because of duplicate detection. This highlights an opportunity to optimize duplicate detection for large datasets, which is listed as a future enhancement.

### Independent Reconciliation

The reconciliation process independently reconstructed transaction states and calculated expected daily product metrics from the input files.

| Measurement | Expected | Actual |
|---|---:|---:|
| Active transactions | 25,004 | 25,004 |
| Metric groups | 30 | 30 |

Additional result:

- Input files checked: 2
- Unique accepted transactions: 50,005
- Mismatched metric groups: 0
- Transaction counts and revenue totals: Exact match

**Result: RECONCILIATION PASSED**

### Automated Tests

All 13 automated tests passed successfully using Python unittest.

Test coverage includes:

- Valid event processing
- Missing required fields
- Invalid and negative amounts
- Invalid event types and versions
- NEW, UPDATE, and REVERSAL processing
- Conflicting duplicate event IDs
- Duplicate transaction versions
- Late-arriving historical events
- Empty input batches
- Missing input file failure handling
- Idempotent processing and duplicate skipping

## Future Enhancements

- Optimize duplicate detection and large-file processing.
- Add structured logging and monitoring.
- Support additional data sources and database systems.
- Add configurable reconciliation rules.
- Introduce parallel processing for larger datasets.

## Conclusion

This project demonstrates an incremental data processing pipeline with event lifecycle management, data quality checks, persistent storage, daily metric aggregation, rerun safety, and independent reconciliation.

It provides a practical example of building a reliable and testable data processing solution using Python and SQLite.