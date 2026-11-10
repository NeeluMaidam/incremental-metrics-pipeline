import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / "database" / "metrics.db"


def get_connection():
    """Create and return a SQLite database connection."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """Create all required database tables."""

    connection = get_connection()

    try:
        connection.executescript("""

        CREATE TABLE IF NOT EXISTS pipeline_runs (
            run_id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT NOT NULL,
            input_count INTEGER DEFAULT 0,
            accepted_count INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0,
            error_message TEXT
        );


        CREATE TABLE IF NOT EXISTS raw_events (
            event_id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            event_type TEXT NOT NULL
                CHECK (event_type IN ('NEW', 'UPDATE', 'REVERSAL')),
            amount_cents INTEGER NOT NULL,
            event_version INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            source_file TEXT NOT NULL,
            run_id TEXT NOT NULL,
            received_at TEXT NOT NULL,
            UNIQUE (transaction_id, event_version),
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
        );


        CREATE TABLE IF NOT EXISTS current_transactions (
            transaction_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            event_version INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );


        CREATE TABLE IF NOT EXISTS daily_product_metrics (
            metric_date TEXT NOT NULL,
            product_id TEXT NOT NULL,
            total_transactions INTEGER NOT NULL,
            total_revenue_cents INTEGER NOT NULL,
            average_transaction_cents REAL,
            last_updated_at TEXT NOT NULL,
            PRIMARY KEY (metric_date, product_id)
        );


        CREATE TABLE IF NOT EXISTS rejected_events (
            reject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            source_file TEXT NOT NULL,
            event_data TEXT NOT NULL,
            reject_reason TEXT NOT NULL,
            rejected_at TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
        );


        CREATE INDEX IF NOT EXISTS idx_events_transaction
        ON raw_events(transaction_id);


        CREATE INDEX IF NOT EXISTS idx_transactions_date
        ON current_transactions(transaction_date);


        """)

        connection.commit()
        print("Database initialized successfully!")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
