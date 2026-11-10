import csv
import json
import sqlite3
import uuid

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.database import get_connection


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"


def now():
    return datetime.now(timezone.utc).isoformat()


def setup_products(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_name TEXT NOT NULL
        )
    """)

    products = [
        ("P101", "Laptop"),
        ("P102", "Mouse"),
        ("P103", "Keyboard")
    ]

    connection.executemany("""
        INSERT OR IGNORE INTO products
        (product_id, product_name)
        VALUES (?, ?)
    """, products)


def validate_event(row):
    required_fields = [
        "event_id",
        "transaction_id",
        "product_id",
        "customer_id",
        "event_type",
        "amount",
        "event_version",
        "transaction_date",
        "event_timestamp"
    ]

    for field in required_fields:
        if row.get(field) is None or not str(row[field]).strip():
            raise ValueError(f"Missing required field: {field}")

    event = {
        field: str(row[field]).strip()
        for field in required_fields
    }

    event["event_type"] = event["event_type"].upper()

    if event["event_type"] not in ("NEW", "UPDATE", "REVERSAL"):
        raise ValueError("Invalid event_type")

    try:
        amount = Decimal(event["amount"])
    except InvalidOperation:
        raise ValueError("Amount must be a valid number")

    if not amount.is_finite() or amount < 0:
        raise ValueError("Amount must be a finite, non-negative number")

    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Amount cannot have more than 2 decimal places")

    event["amount_cents"] = int(amount * 100)

    try:
        event["event_version"] = int(event["event_version"])
    except ValueError:
        raise ValueError("Event version must be an integer")

    if event["event_version"] < 1:
        raise ValueError("Event version must be at least 1")

    try:
        datetime.strptime(event["transaction_date"], "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid transaction_date format")

    try:
        datetime.fromisoformat(
            event["event_timestamp"].replace("Z", "+00:00")
        )
    except ValueError:
        raise ValueError("Invalid event_timestamp format")

    return event


def reject_event(connection, run_id, source_file, row, reason):
    connection.execute("""
        INSERT INTO rejected_events (
            run_id,
            source_file,
            event_data,
            reject_reason,
            rejected_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        run_id,
        str(source_file),
        json.dumps(row, default=str),
        reason,
        now()
    ))


def rebuild_transaction(connection, transaction_id):
    events = connection.execute("""
        SELECT *
        FROM raw_events
        WHERE transaction_id = ?
        ORDER BY event_version ASC
    """, (transaction_id,)).fetchall()

    state = None

    for event in events:

        if event["event_type"] == "NEW":

            state = {
                "transaction_id": transaction_id,
                "product_id": event["product_id"],
                "customer_id": event["customer_id"],
                "amount_cents": event["amount_cents"],
                "transaction_date": event["transaction_date"],
                "event_version": event["event_version"],
                "is_active": 1
            }

        elif event["event_type"] == "UPDATE":

            if state is not None and state["is_active"]:
                state["product_id"] = event["product_id"]
                state["customer_id"] = event["customer_id"]
                state["amount_cents"] = event["amount_cents"]
                state["transaction_date"] = event["transaction_date"]
                state["event_version"] = event["event_version"]

        elif event["event_type"] == "REVERSAL":

            if state is not None:
                state["is_active"] = 0
                state["event_version"] = event["event_version"]

    if state is None:
        return None

    connection.execute("""
        INSERT INTO current_transactions (
            transaction_id,
            product_id,
            customer_id,
            amount_cents,
            transaction_date,
            event_version,
            is_active,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)

        ON CONFLICT(transaction_id)
        DO UPDATE SET
            product_id = excluded.product_id,
            customer_id = excluded.customer_id,
            amount_cents = excluded.amount_cents,
            transaction_date = excluded.transaction_date,
            event_version = excluded.event_version,
            is_active = excluded.is_active,
            updated_at = excluded.updated_at
    """, (
        state["transaction_id"],
        state["product_id"],
        state["customer_id"],
        state["amount_cents"],
        state["transaction_date"],
        state["event_version"],
        state["is_active"],
        now()
    ))

    return state


def recompute_metrics(connection, affected_groups):

    for metric_date, product_id in affected_groups:

        result = connection.execute("""
            SELECT
                COUNT(*) AS total_transactions,
                COALESCE(SUM(amount_cents), 0) AS total_revenue,
                AVG(amount_cents) AS average_amount
            FROM current_transactions
            WHERE transaction_date = ?
              AND product_id = ?
              AND is_active = 1
        """, (metric_date, product_id)).fetchone()

        if result["total_transactions"] == 0:

            connection.execute("""
                DELETE FROM daily_product_metrics
                WHERE metric_date = ?
                  AND product_id = ?
            """, (metric_date, product_id))

        else:

            connection.execute("""
                INSERT INTO daily_product_metrics (
                    metric_date,
                    product_id,
                    total_transactions,
                    total_revenue_cents,
                    average_transaction_cents,
                    last_updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)

                ON CONFLICT(metric_date, product_id)
                DO UPDATE SET
                    total_transactions = excluded.total_transactions,
                    total_revenue_cents = excluded.total_revenue_cents,
                    average_transaction_cents =
                        excluded.average_transaction_cents,
                    last_updated_at = excluded.last_updated_at
            """, (
                metric_date,
                product_id,
                result["total_transactions"],
                result["total_revenue"],
                result["average_amount"],
                now()
            ))


def export_metrics(connection):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "daily_metrics.csv"

    rows = connection.execute("""
        SELECT *
        FROM daily_product_metrics
        ORDER BY metric_date, product_id
    """).fetchall()

    with open(output_file, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow([
            "metric_date",
            "product_id",
            "total_transactions",
            "total_revenue",
            "average_transaction"
        ])

        for row in rows:
            writer.writerow([
                row["metric_date"],
                row["product_id"],
                row["total_transactions"],
                row["total_revenue_cents"] / 100,
                (
                    row["average_transaction_cents"] / 100
                    if row["average_transaction_cents"] is not None
                    else 0
                )
            ])

    return output_file


def run_pipeline(file_path):

    run_id = str(uuid.uuid4())
    start_time = now()

    connection = get_connection()

    input_count = 0
    accepted_count = 0
    rejected_count = 0
    duplicate_count = 0

    affected_groups = set()

    source_file = Path(file_path)

    print("\nStarting pipeline...")
    print("Input file:", source_file)

    try:

        setup_products(connection)

        connection.execute("""
            INSERT INTO pipeline_runs (
                run_id,
                start_time,
                status,
                input_count,
                accepted_count,
                rejected_count
            )
            VALUES (?, ?, ?, 0, 0, 0)
        """, (run_id, start_time, "RUNNING"))

        connection.commit()

        if not source_file.exists():
            raise FileNotFoundError(
                f"Input file not found: {source_file}"
            )

        with open(
            source_file,
            "r",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            sample = file.read(4096)
            file.seek(0)

            try:
                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t|"
                )
            except csv.Error:
                dialect = csv.excel

            reader = csv.DictReader(file, dialect=dialect)

            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no header")

            reader.fieldnames = [
                name.strip().lower() if name else ""
                for name in reader.fieldnames
            ]

            print("\nDetected CSV headers:")
            print(reader.fieldnames)

            expected = {
                "event_id",
                "transaction_id",
                "product_id",
                "customer_id",
                "event_type",
                "amount",
                "event_version",
                "transaction_date",
                "event_timestamp"
            }

            missing = expected - set(reader.fieldnames)

            if missing:
                raise ValueError(
                    f"Missing CSV columns: {sorted(missing)}"
                )

            print("\nCSV headers validated successfully!")

            for row in reader:

                input_count += 1

                try:

                    if None in row:
                        raise ValueError(
                            "Row contains extra CSV columns"
                        )

                    event = validate_event(row)

                    product = connection.execute("""
                        SELECT product_id
                        FROM products
                        WHERE product_id = ?
                    """, (event["product_id"],)).fetchone()

                    if product is None:
                        raise ValueError(
                            f"Unknown product: {event['product_id']}"
                        )

                    existing = connection.execute("""
                        SELECT *
                        FROM raw_events
                        WHERE event_id = ?
                    """, (event["event_id"],)).fetchone()

                    if existing is not None:
                        comparison_fields = [
                            "event_id",
                            "transaction_id",
                            "product_id",
                            "customer_id",
                            "event_type",
                            "amount_cents",
                            "event_version",
                            "transaction_date",
                            "event_timestamp"
                        ]

                        if all(
                            existing[key] == event[key]
                            for key in comparison_fields
                        ):
                            duplicate_count += 1

                            print(
                                "Duplicate skipped:",
                                event["event_id"]
                            )

                            continue

                        raise ValueError(
                            "Conflicting duplicate event ID"
                        )

                    version_exists = connection.execute("""
                        SELECT event_id
                        FROM raw_events
                        WHERE transaction_id = ?
                          AND event_version = ?
                    """, (
                        event["transaction_id"],
                        event["event_version"]
                    )).fetchone()

                    if version_exists is not None:
                        raise ValueError(
                            "Duplicate transaction event version"
                        )

                    transaction_id = event["transaction_id"]

                    old_state = connection.execute("""
                        SELECT *
                        FROM current_transactions
                        WHERE transaction_id = ?
                    """, (transaction_id,)).fetchone()

                    if old_state is not None and old_state["is_active"]:
                        affected_groups.add((
                            old_state["transaction_date"],
                            old_state["product_id"]
                        ))

                    connection.execute("""
                        INSERT INTO raw_events (
                            event_id,
                            transaction_id,
                            product_id,
                            customer_id,
                            event_type,
                            amount_cents,
                            event_version,
                            transaction_date,
                            event_timestamp,
                            source_file,
                            run_id,
                            received_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event["event_id"],
                        event["transaction_id"],
                        event["product_id"],
                        event["customer_id"],
                        event["event_type"],
                        event["amount_cents"],
                        event["event_version"],
                        event["transaction_date"],
                        event["event_timestamp"],
                        str(source_file),
                        run_id,
                        now()
                    ))

                    new_state = rebuild_transaction(
                        connection,
                        transaction_id
                    )

                    if new_state is not None and new_state["is_active"]:
                        affected_groups.add((
                            new_state["transaction_date"],
                            new_state["product_id"]
                        ))

                    accepted_count += 1

                except (ValueError, sqlite3.IntegrityError) as error:

                    rejected_count += 1

                    reject_event(
                        connection,
                        run_id,
                        source_file,
                        row,
                        str(error)
                    )

                    print(
                        f"Rejected {row.get('event_id')}: {error}"
                    )

        print("\nRecomputing affected metrics...")

        recompute_metrics(connection, affected_groups)

        status = (
            "COMPLETED_WITH_REJECTS"
            if rejected_count > 0
            else "SUCCESS"
        )

        end_time = now()

        connection.execute("""
            UPDATE pipeline_runs
            SET
                end_time = ?,
                status = ?,
                input_count = ?,
                accepted_count = ?,
                rejected_count = ?
            WHERE run_id = ?
        """, (
            end_time,
            status,
            input_count,
            accepted_count,
            rejected_count,
            run_id
        ))

        connection.commit()

        metrics_file = export_metrics(connection)

        report = {
            "run_id": run_id,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "input_file": str(source_file),
            "input_count": input_count,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "duplicate_count": duplicate_count,
            "affected_groups": len(affected_groups),
            "metrics_file": str(metrics_file)
        }

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        report_file = OUTPUT_DIR / "run_report.json"

        with open(report_file, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=4)

        print("\n=== PIPELINE RUN SUMMARY ===")
        print(json.dumps(report, indent=4))

        print("\nMetrics saved:", metrics_file)
        print("Report saved:", report_file)

        return report

    except Exception as error:

        connection.rollback()

        connection.execute("""
            UPDATE pipeline_runs
            SET
                end_time = ?,
                status = ?,
                input_count = ?,
                accepted_count = ?,
                rejected_count = ?,
                error_message = ?
            WHERE run_id = ?
        """, (
            now(),
            "FAILED",
            input_count,
            accepted_count,
            rejected_count,
            str(error),
            run_id
        ))

        connection.commit()

        print("\nPIPELINE FAILED:", error)

        raise

    finally:
        connection.close()
