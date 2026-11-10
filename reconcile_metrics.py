import csv
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILES = [
    BASE_DIR / "data" / "sample_events.csv",
    BASE_DIR / "data" / "large_events.csv",
]

METRICS_FILE = BASE_DIR / "output" / "daily_metrics.csv"


def load_events():
    events_by_id = {}
    transactions = defaultdict(list)

    for file_path in INPUT_FILES:
        with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    event_id = row["event_id"].strip()
                    transaction_id = row["transaction_id"].strip()
                    event_type = row["event_type"].strip().upper()
                    amount = Decimal(row["amount"].strip())
                    version = int(row["event_version"])
                    product_id = row["product_id"].strip()
                    transaction_date = row["transaction_date"].strip()

                    if not event_id or not transaction_id:
                        continue

                    if event_type not in ("NEW", "UPDATE", "REVERSAL"):
                        continue

                    if amount < 0 or amount != amount.quantize(Decimal("0.01")):
                        continue

                    if version < 1:
                        continue

                    event = {
                        "event_id": event_id,
                        "transaction_id": transaction_id,
                        "event_type": event_type,
                        "amount": amount,
                        "version": version,
                        "product_id": product_id,
                        "transaction_date": transaction_date,
                    }

                    if event_id in events_by_id:
                        continue

                    events_by_id[event_id] = event
                    transactions[transaction_id].append(event)

                except (ValueError, KeyError, ArithmeticError):
                    continue

    return transactions


def calculate_expected_metrics(transactions):
    totals = defaultdict(lambda: {
        "count": 0,
        "revenue": Decimal("0.00"),
    })

    active_count = 0

    for transaction_events in transactions.values():
        transaction_events.sort(key=lambda event: event["version"])

        latest_event = transaction_events[-1]

        if latest_event["event_type"] == "REVERSAL":
            continue

        key = (
            latest_event["transaction_date"],
            latest_event["product_id"],
        )

        totals[key]["count"] += 1
        totals[key]["revenue"] += latest_event["amount"]
        active_count += 1

    return totals, active_count


def compare_with_pipeline(expected):
    actual = {}

    with open(METRICS_FILE, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            key = (row["metric_date"], row["product_id"])

            actual[key] = {
                "count": int(row["total_transactions"]),
                "revenue": Decimal(row["total_revenue"]).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
            }

    all_keys = set(expected) | set(actual)
    mismatches = []

    for key in sorted(all_keys):
        expected_count = expected.get(key, {}).get("count", 0)
        expected_revenue = expected.get(
            key, {}
        ).get("revenue", Decimal("0.00"))

        actual_count = actual.get(key, {}).get("count", 0)
        actual_revenue = actual.get(
            key, {}
        ).get("revenue", Decimal("0.00")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if (
            expected_count != actual_count
            or expected_revenue != actual_revenue
        ):
            mismatches.append({
                "date": key[0],
                "product": key[1],
                "expected_count": expected_count,
                "actual_count": actual_count,
                "expected_revenue": str(expected_revenue),
                "actual_revenue": str(actual_revenue),
            })

    print("\n=== INDEPENDENT RECONCILIATION ===")
    print("Input files checked:", len(INPUT_FILES))
    print("Expected metric groups:", len(expected))
    print("Actual metric groups:", len(actual))
    print("Expected active transactions:", sum(
        item["count"] for item in expected.values()
    ))
    print("Actual active transactions:", sum(
        item["count"] for item in actual.values()
    ))
    print("Mismatched groups:", len(mismatches))

    if mismatches:
        print("\nMISMATCH DETAILS:")
        for mismatch in mismatches[:10]:
            print(mismatch)

        print("\nRECONCILIATION FAILED")
    else:
        print("\nRECONCILIATION PASSED")
        print("All transaction counts and revenue totals match!")


def main():
    transactions = load_events()
    expected, active_count = calculate_expected_metrics(transactions)

    print("Unique accepted transactions:", len(transactions))
    print("Expected active transactions:", active_count)

    compare_with_pipeline(expected)


if __name__ == "__main__":
    main()
