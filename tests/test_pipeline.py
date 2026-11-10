
import unittest
import csv
import json
import tempfile

from pathlib import Path
from unittest.mock import patch

import src.database as database
import src.pipeline as pipeline

from src.pipeline import validate_event

class TestEventValidation(unittest.TestCase):

    def setUp(self):
        self.valid_event = {
            "event_id": "E001",
            "transaction_id": "T001",
            "product_id": "P101",
            "customer_id": "C001",
            "event_type": "NEW",
            "amount": "500.00",
            "event_version": "1",
            "transaction_date": "2026-11-09",
            "event_timestamp": "2026-11-09T10:00:00"
        }

    def test_valid_event(self):
        result = validate_event(self.valid_event)

        self.assertEqual(result["event_id"], "E001")
        self.assertEqual(result["event_type"], "NEW")
        self.assertEqual(result["amount_cents"], 50000)
        self.assertEqual(result["event_version"], 1)

    def test_invalid_amount(self):
        event = self.valid_event.copy()
        event["amount"] = "abc"

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_missing_event_id(self):
        event = self.valid_event.copy()
        event["event_id"] = ""

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_missing_amount(self):
        event = self.valid_event.copy()
        event["amount"] = ""

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_invalid_event_type(self):
        event = self.valid_event.copy()
        event["event_type"] = "CANCEL"

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_negative_amount(self):
        event = self.valid_event.copy()
        event["amount"] = "-100"

        with self.assertRaises(ValueError):
            validate_event(event)

    def test_invalid_event_version(self):
        event = self.valid_event.copy()
        event["event_version"] = "zero"

        with self.assertRaises(ValueError):
            validate_event(event)




class TestPipelineIntegration(unittest.TestCase):

    def test_new_update_reversal_and_idempotency(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(temp_dir)

            db_path = temp_path / "test.db"

            output_path = temp_path / "output"
            output_path.mkdir()

            input_file = temp_path / "events.csv"

            events = [
                {
                    "event_id": "E001",
                    "transaction_id": "T001",
                    "product_id": "P101",
                    "customer_id": "C001",
                    "event_type": "NEW",
                    "amount": "100.00",
                    "event_version": "1",
                    "transaction_date": "2026-11-09",
                    "event_timestamp": "2026-11-09T10:00:00"
                },
                {
                    "event_id": "E002",
                    "transaction_id": "T001",
                    "product_id": "P101",
                    "customer_id": "C001",
                    "event_type": "UPDATE",
                    "amount": "80.00",
                    "event_version": "2",
                    "transaction_date": "2026-11-09",
                    "event_timestamp": "2026-11-09T11:00:00"
                },
                {
                    "event_id": "E003",
                    "transaction_id": "T002",
                    "product_id": "P101",
                    "customer_id": "C002",
                    "event_type": "NEW",
                    "amount": "20.00",
                    "event_version": "1",
                    "transaction_date": "2026-11-09",
                    "event_timestamp": "2026-11-09T12:00:00"
                },
                {
                    "event_id": "E004",
                    "transaction_id": "T002",
                    "product_id": "P101",
                    "customer_id": "C002",
                    "event_type": "REVERSAL",
                    "amount": "20.00",
                    "event_version": "2",
                    "transaction_date": "2026-11-09",
                    "event_timestamp": "2026-11-09T13:00:00"
                }
            ]

            
            with open(
                input_file,
                "w",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=events[0].keys()
                )

                writer.writeheader()
                writer.writerows(events)

            
            with patch.object(database, "DB_PATH", db_path):

                with patch.object(
                    pipeline,
                    "OUTPUT_DIR",
                    output_path
                ):

                    database.initialize_database()

                    
                    pipeline.run_pipeline(input_file)

                    with open(
                        output_path / "daily_metrics.csv",
                        newline="",
                        encoding="utf-8"
                    ) as file:

                        first_metrics = list(
                            csv.DictReader(file)
                        )

                    
                    pipeline.run_pipeline(input_file)

                    with open(
                        output_path / "daily_metrics.csv",
                        newline="",
                        encoding="utf-8"
                    ) as file:

                        second_metrics = list(
                            csv.DictReader(file)
                        )

                    with open(
                        output_path / "run_report.json",
                        encoding="utf-8"
                    ) as file:

                        report = json.load(file)

            
            self.assertEqual(first_metrics, second_metrics)

            self.assertEqual(report["status"], "SUCCESS")

            self.assertEqual(report["input_count"], 4)

            self.assertEqual(len(second_metrics), 1)

            self.assertEqual(
                int(second_metrics[0]["total_transactions"]),
                1
            )

            self.assertAlmostEqual(
                float(second_metrics[0]["total_revenue"]),
                80.0
            )

    def test_conflicting_duplicate_event(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(temp_dir)
            db_path = temp_path / "test.db"

            output_path = temp_path / "output"
            output_path.mkdir()

            original_file = temp_path / "original.csv"
            conflict_file = temp_path / "conflict.csv"

            original_event = {
                "event_id": "E001",
                "transaction_id": "T001",
                "product_id": "P101",
                "customer_id": "C001",
                "event_type": "NEW",
                "amount": "100.00",
                "event_version": "1",
                "transaction_date": "2026-11-09",
                "event_timestamp": "2026-11-09T10:00:00"
            }

            with open(
                original_file, "w", newline="", encoding="utf-8"
            ) as file:
                writer = csv.DictWriter(
                    file, fieldnames=original_event.keys()
                )
                writer.writeheader()
                writer.writerow(original_event)

            conflict_event = original_event.copy()
            conflict_event["amount"] = "999.00"

            with open(
                conflict_file, "w", newline="", encoding="utf-8"
            ) as file:
                writer = csv.DictWriter(
                    file, fieldnames=conflict_event.keys()
                )
                writer.writeheader()
                writer.writerow(conflict_event)

            with patch.object(database, "DB_PATH", db_path):
                with patch.object(pipeline, "OUTPUT_DIR", output_path):

                    database.initialize_database()

                    pipeline.run_pipeline(original_file)

                    pipeline.run_pipeline(conflict_file)

                    with open(
                        output_path / "run_report.json",
                        encoding="utf-8"
                    ) as file:
                        report = json.load(file)

                    with open(
                        output_path / "daily_metrics.csv",
                        newline="",
                        encoding="utf-8"
                    ) as file:
                        metrics = list(csv.DictReader(file))

            
            self.assertEqual(
                report["status"], "COMPLETED_WITH_REJECTS"
            )
            self.assertEqual(report["input_count"], 1)
            self.assertEqual(report["accepted_count"], 0)
            self.assertEqual(report["rejected_count"], 1)

            
            self.assertEqual(len(metrics), 1)
            self.assertAlmostEqual(
                float(metrics[0]["total_revenue"]), 100.0
            )

    def test_late_arriving_historical_event(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(temp_dir)
            db_path = temp_path / "test.db"

            output_path = temp_path / "output"
            output_path.mkdir()

            first_file = temp_path / "first.csv"
            late_file = temp_path / "late.csv"

            first_event = {
                "event_id": "E101",
                "transaction_id": "T101",
                "product_id": "P101",
                "customer_id": "C101",
                "event_type": "NEW",
                "amount": "100.00",
                "event_version": "1",
                "transaction_date": "2026-11-09",
                "event_timestamp": "2026-11-09T10:00:00"
            }

            late_event = {
                "event_id": "E102",
                "transaction_id": "T102",
                "product_id": "P101",
                "customer_id": "C102",
                "event_type": "NEW",
                "amount": "50.00",
                "event_version": "1",
                "transaction_date": "2026-11-08",
                "event_timestamp": "2026-11-10T09:00:00"
            }

            with open(first_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file, fieldnames=first_event.keys()
                )
                writer.writeheader()
                writer.writerow(first_event)

            with open(late_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file, fieldnames=late_event.keys()
                )
                writer.writeheader()
                writer.writerow(late_event)

            with patch.object(database, "DB_PATH", db_path):
                with patch.object(pipeline, "OUTPUT_DIR", output_path):

                    database.initialize_database()

                    pipeline.run_pipeline(first_file)

                    pipeline.run_pipeline(late_file)

                    with open(
                        output_path / "daily_metrics.csv",
                        newline="",
                        encoding="utf-8"
                    ) as file:
                        metrics = list(csv.DictReader(file))

            self.assertEqual(len(metrics), 2)

            metrics_by_date = {
                row["metric_date"]: row
                for row in metrics
            }

            self.assertIn("2026-11-08", metrics_by_date)
            self.assertIn("2026-11-09", metrics_by_date)

            self.assertAlmostEqual(
                float(metrics_by_date["2026-11-08"]["total_revenue"]),
                50.0
            )

            self.assertAlmostEqual(
                float(metrics_by_date["2026-11-09"]["total_revenue"]),
                100.0
            )

            self.assertEqual(
                int(metrics_by_date["2026-11-08"]["total_transactions"]),
                1
            )

            self.assertEqual(
                int(metrics_by_date["2026-11-09"]["total_transactions"]),
                1
            )
    
    def test_empty_input_batch(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(temp_dir)
            db_path = temp_path / "test.db"

            output_path = temp_path / "output"
            output_path.mkdir()

            input_file = temp_path / "empty.csv"

            with open(input_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow([
                    "event_id",
                    "transaction_id",
                    "product_id",
                    "customer_id",
                    "event_type",
                    "amount",
                    "event_version",
                    "transaction_date",
                    "event_timestamp"
                ])

            with patch.object(database, "DB_PATH", db_path):
                with patch.object(pipeline, "OUTPUT_DIR", output_path):

                    database.initialize_database()
                    pipeline.run_pipeline(input_file)

                    with open(
                        output_path / "run_report.json",
                        encoding="utf-8"
                    ) as file:
                        report = json.load(file)

                    with open(
                        output_path / "daily_metrics.csv",
                        newline="",
                        encoding="utf-8"
                    ) as file:
                        metrics = list(csv.DictReader(file))

            self.assertEqual(report["status"], "SUCCESS")
            self.assertEqual(report["input_count"], 0)
            self.assertEqual(report["accepted_count"], 0)
            self.assertEqual(report["rejected_count"], 0)
            self.assertEqual(report["duplicate_count"], 0)
            self.assertEqual(report["affected_groups"], 0)
            self.assertEqual(len(metrics), 0)

    def test_missing_input_file_records_failed_run(self):
            with tempfile.TemporaryDirectory() as temp_dir:

                temp_path = Path(temp_dir)
                db_path = temp_path / "test.db"

                output_path = temp_path / "output"
                output_path.mkdir()

                missing_file = temp_path / "missing.csv"

                with patch.object(database, "DB_PATH", db_path):
                    with patch.object(pipeline, "OUTPUT_DIR", output_path):

                        database.initialize_database()

                        with self.assertRaises(FileNotFoundError):
                            pipeline.run_pipeline(missing_file)

                        connection = database.get_connection()

                        run = connection.execute("""
                            SELECT status, error_message
                            FROM pipeline_runs
                        """).fetchone()

                        connection.close()

                self.assertEqual(run["status"], "FAILED")
                self.assertIn("Input file not found", run["error_message"])
    def test_duplicate_transaction_version_is_rejected(self):

        with tempfile.TemporaryDirectory() as temp_dir:

            temp_path = Path(temp_dir)
            db_path = temp_path / "test.db"

            output_path = temp_path / "output"
            output_path.mkdir()

            input_file = temp_path / "duplicate_version.csv"

            events = [
                {
                    "event_id": "E903",
                    "transaction_id": "T903",
                    "product_id": "P101",
                    "customer_id": "C903",
                    "event_type": "NEW",
                    "amount": "100.00",
                    "event_version": "1",
                    "transaction_date": "2026-11-10",
                    "event_timestamp": "2026-11-10T12:00:00"
                },
                {
                    "event_id": "E904",
                    "transaction_id": "T903",
                    "product_id": "P101",
                    "customer_id": "C903",
                    "event_type": "UPDATE",
                    "amount": "150.00",
                    "event_version": "1",
                    "transaction_date": "2026-11-10",
                    "event_timestamp": "2026-11-10T12:05:00"
                }
            ]

            with open(input_file, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(
                    file, fieldnames=events[0].keys()
                )
                writer.writeheader()
                writer.writerows(events)

            with patch.object(database, "DB_PATH", db_path):
                with patch.object(pipeline, "OUTPUT_DIR", output_path):

                    database.initialize_database()
                    pipeline.run_pipeline(input_file)

                    with open(
                        output_path / "run_report.json",
                        encoding="utf-8"
                    ) as file:
                        report = json.load(file)

                    connection = database.get_connection()

                    rejected = connection.execute("""
                        SELECT reject_reason
                        FROM rejected_events
                    """).fetchone()

                    connection.close()

            self.assertEqual(report["input_count"], 2)
            self.assertEqual(report["accepted_count"], 1)
            self.assertEqual(report["rejected_count"], 1)
            self.assertEqual(
                report["status"], "COMPLETED_WITH_REJECTS"
            )
            self.assertIn(
                "Duplicate transaction event version",
                rejected["reject_reason"]
            )
if __name__ == "__main__":
    unittest.main()
