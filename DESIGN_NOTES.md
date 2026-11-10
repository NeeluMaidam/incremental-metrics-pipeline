# Design Notes — Incremental Metrics Pipeline

## 1. Architecture

The solution uses a modular Python and SQLite architecture.

**Processing flow:**

CSV Input → Ingestion → Schema Validation → Business Rule Validation → SQLite Raw Event Storage → Transaction State Reconstruction → Affected Metrics Recalculation → CSV and JSON Output → Independent Reconciliation

## 2. Key Design Decisions

### SQLite for Persistent Storage
SQLite was selected because it is lightweight, requires no external database server, and supports transactions, primary keys, foreign keys, and uniqueness constraints.

**Trade-off:** SQLite is suitable for this local assignment but may require a server-based database for high-concurrency production workloads.

### Event History Preservation
Incoming valid events are stored in the `raw_events` table rather than silently overwriting previous event history.

The `current_transactions` table maintains the latest transaction state, while `daily_product_metrics` stores aggregated results.

**Trade-off:** Maintaining event history requires additional storage but improves traceability and supports transaction reconstruction.

### Integer-Based Monetary Values
Transaction amounts are converted into integer cents before storage and aggregation to avoid floating-point precision errors.

### Incremental Recalculation
The pipeline identifies affected date and product combinations and recalculates only those metric groups instead of rebuilding all historical metrics.

### Late-Arriving Events
Historical events are processed using their transaction dates. The affected historical metric groups are recalculated when late events arrive.

## 3. Idempotency and Duplicate Handling

The pipeline uses database uniqueness constraints and event identifiers to prevent unintended duplicate processing.

- Previously processed event IDs are skipped.
- Conflicting duplicate event IDs are rejected.
- Duplicate transaction versions are rejected.
- Reprocessing the same input does not change existing metrics.

## 4. Data Quality and Failure Handling

Incoming events are validated for required fields, event types, amounts, versions, timestamps, and product references.

Rejected records are stored with their original event data, source file, run ID, rejection reason, and timestamp.

Pipeline execution details are recorded in `pipeline_runs` and exported through `output/run_report.json`.

A failed run records its failure status and error details. After correcting the issue, the input can be processed again.

## 5. Performance Measurement

The pipeline was tested with 100,000 generated transaction events.

| Measurement | Result |
|---|---:|
| Input events | 100,000 |
| Accepted events | 100,000 |
| Rejected events | 0 |
| First-run execution time | Approximately 4.26 seconds |
| Second-run execution time | Approximately 21.67 seconds |
| Duplicate events skipped on rerun | 100,000 |

Independent reconciliation confirmed that expected and actual transaction counts and revenue totals matched, with zero mismatched metric groups.

## 6. Optimization Opportunity

The second execution took longer because the pipeline checks previously processed events for duplicates.

A possible optimization is to improve duplicate detection through indexed batch lookups and bulk database operations.

This is identified as future work and has not been implemented in the current version.

## 7. Limitations and Future Improvements

- SQLite is intended for local execution and moderate workloads.
- Duplicate detection can be optimized for large reruns.
- Structured logging and monitoring can be expanded.
- Database schema migrations can be introduced.
- Parallel processing and cloud deployment can be considered for larger workloads.

## 8. Conclusion

The solution prioritizes correctness, traceability, incremental processing, rerun safety, and reproducible testing over unnecessary infrastructure complexity.

It demonstrates a complete local data engineering workflow using Python, SQLite, CSV, and automated tests.
