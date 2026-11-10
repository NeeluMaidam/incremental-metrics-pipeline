# Incremental Metrics Pipeline

## Project Overview

The Incremental Metrics Pipeline is a Python-based data processing solution that processes transaction events and maintains accurate daily business metrics.

It handles NEW, UPDATE, and REVERSAL events, validates incoming records, supports late-arriving events, and recalculates only the affected date and product combinations.

The pipeline uses SQLite for persistent storage and exports calculated metrics as CSV files. It also supports safe reruns, event deduplication, rejection tracking, and independent reconciliation.

## Key Features

- Processes NEW, UPDATE, and REVERSAL transaction events.
- Maintains daily product-level metrics.
- Handles late-arriving and out-of-order events.
- Recalculates only affected date and product combinations.
- Validates incoming event data and business rules.
- Detects duplicate events and conflicting transaction versions.
- Tracks rejected records and rejection reasons.
- Supports reruns through event-level idempotency.
- Maintains run status and processing counters.
- Generates reproducible sample and large datasets.
- Reconciles calculated metrics against independently derived results.
- Includes automated unit and integration tests.

## Technology Stack

- **Language:** Python
- **Database:** SQLite
- **Data Processing:** Python CSV and JSON modules
- **Testing:** Python unittest
- **Version Control:** GitHub

## Project Structure

```text
incremental-metrics-pipeline/
│
├── data/
│   ├── sample_events.csv
│   ├── large_events.csv
│   ├── duplicate_version.csv
│   ├── empty_events.csv
│   ├── invalid_product.csv
│   └── schema_change.csv
│
├── database/
│   └── metrics.db (created automatically)
│
├── output/
│   ├── daily_metrics.csv
│   └── run_report.json
│
├── src/
│   ├── database.py
│   └── pipeline.py
│
├── tests/
│   └── test_pipeline.py
│
├── generate_data.py
├── main.py
├── reconcile_metrics.py
├── requirements.txt
├── DESIGN_NOTES.md
└── README.md
```

## Data Dictionary and Business Rules

### Source Event Schema

The source CSV contains transaction events with the following fields:

| Field | Data Type | Description |
|---|---|---|
| `event_id` | TEXT | Unique identifier for each incoming event |
| `transaction_id` | TEXT | Business identifier for a transaction |
| `product_id` | TEXT | Reference to the product associated with the transaction |
| `customer_id` | TEXT | Customer identifier associated with the transaction |
| `event_type` | TEXT | Event operation: NEW, UPDATE, or REVERSAL |
| `amount` | DECIMAL | Transaction amount, with up to two decimal places |
| `event_version` | INTEGER | Version number used to determine transaction event order |
| `transaction_date` | DATE | Business transaction date in YYYY-MM-DD format |
| `event_timestamp` | TEXT | Event creation timestamp in ISO-8601 format |

### Target Metrics

The target dataset is `daily_product_metrics`, with one record per transaction date and product.

| Metric | Description |
|---|---|
| `metric_date` | Transaction date |
| `product_id` | Product identifier |
| `total_transactions` | Number of active transactions |
| `total_revenue` | Sum of active transaction amounts |
| `average_transaction` | Average amount per active transaction |

The combination of transaction date and product ID defines the target metric grain.

### Keys and Business Rules

- `event_id` uniquely identifies an incoming event.
- `transaction_id` identifies a business transaction.
- `(transaction_id, event_version)` prevents duplicate transaction versions.
- `product_id` must reference an existing product.
- Event versions determine the order of transaction changes.
- Transaction amounts must be non-negative and have no more than two decimal places.
- Transaction dates use ISO date format.
- Event timestamps use ISO-8601 format.
- REVERSAL events exclude transactions from active daily metrics.
- Late-arriving events are processed using their original transaction dates.
- Rejected events retain source information and rejection reasons for traceability.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/NeeluMaidam/incremental-metrics-pipeline.git
cd incremental-metrics-pipeline
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate Sample Data

```bash
python generate_data.py
```

### 4. Run the Pipeline

```bash
python main.py
```

### 5. Run Reconciliation

```bash
python reconcile_metrics.py
```

### 6. Run Automated Tests

```bash
python -m unittest discover -s tests -v
```

## Output Files

| File | Description |
|---|---|
| `output/daily_metrics.csv` | Calculated daily product metrics |
| `output/run_report.json` | Processing summary, run status, and counters |
| `output/rejects.csv` | Rejected records, generated when applicable |
| `output/mismatches.csv` | Reconciliation differences, generated when applicable |

The SQLite database is created automatically when the pipeline runs.

## Testing

The project includes 13 automated unit and integration tests covering:

- Valid event processing.
- Invalid amounts.
- Missing event IDs and amounts.
- Invalid event types.
- Negative transaction amounts.
- Invalid event versions.
- NEW, UPDATE, and REVERSAL processing.
- Duplicate event handling and idempotency.
- Conflicting duplicate events.
- Duplicate transaction versions.
- Late-arriving historical events.
- Missing input files.
- Empty input batches.

Run all tests using:

```bash
python -m unittest discover -s tests -v
```

## Performance Testing

The pipeline was tested with a generated dataset containing 100,000 transaction events.

| Metric | Result |
|---|---:|
| Input events | 100,000 |
| Accepted events | 100,000 |
| Rejected events | 0 |
| Duplicate events on first run | 0 |
| Event types | 50,000 NEW, 25,000 UPDATE, 25,000 REVERSAL |
| Late-arriving transactions | 5,024 |
| Affected metric groups | 30 |
| First run execution time | Approximately 4.26 seconds |

A second run processed the same dataset and skipped all 100,000 previously processed events, demonstrating idempotent behavior.

Independent reconciliation completed with zero mismatches.

Execution times are environment-dependent and may vary.

## Design Decisions

- **SQLite:** Provides persistent local storage without requiring an external database server.
- **Event versioning:** Helps identify the correct transaction state when updates and reversals arrive.
- **Idempotency:** Prevents previously processed events from being applied again during reruns.
- **Incremental recalculation:** Limits metric recalculation to affected date and product combinations.
- **Rejection tracking:** Preserves information about invalid records for debugging and traceability.
- **Independent reconciliation:** Helps verify that calculated metrics match independently derived results.
- **Deterministic data generation:** Makes testing reproducible through a fixed random seed.

## Future Improvements

- Optimize duplicate detection for faster processing of very large batches.
- Add stronger schema evolution handling.
- Introduce more comprehensive partial-failure and recovery testing.
- Support cloud-based storage and scheduled pipeline execution.
- Add structured logging and monitoring dashboards.

## Author

**Neelu Maidam**

GitHub: https://github.com/NeeluMaidam

Project Repository: https://github.com/NeeluMaidam/incremental-metrics-pipeline
