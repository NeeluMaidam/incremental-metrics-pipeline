import csv
import random
from datetime import datetime, timedelta
from pathlib import Path


random.seed(42)

TOTAL_TRANSACTIONS = 50_000

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "large_events.csv"

PRODUCTS = ["P101", "P102", "P103"]

CUSTOMER_COUNT = 10_000

BASE_DATE = datetime(2026, 11, 10)

events = []

new_count = 0
update_count = 0
reversal_count = 0
late_count = 0

for i in range(1, TOTAL_TRANSACTIONS + 1):

    transaction_id = f"T{i:06d}"
    customer_id = f"C{random.randint(1, CUSTOMER_COUNT):05d}"
    product_id = random.choice(PRODUCTS)

    if random.random() < 0.10:
        transaction_date = (
            BASE_DATE - timedelta(days=random.randint(1, 9))
        ).date()
        late_count += 1
    else:
        transaction_date = BASE_DATE.date()

    amount = round(random.uniform(50, 10000), 2)

    new_timestamp = (
        BASE_DATE + timedelta(seconds=i)
    ).isoformat(timespec="seconds")

    events.append({
        "event_id": f"E{i:07d}",
        "transaction_id": transaction_id,
        "product_id": product_id,
        "customer_id": customer_id,
        "event_type": "NEW",
        "amount": f"{amount:.2f}",
        "event_version": 1,
        "transaction_date": transaction_date.isoformat(),
        "event_timestamp": new_timestamp
    })

    new_count += 1

    if i <= 25_000:

        updated_amount = round(amount + 25, 2)

        update_timestamp = (
            BASE_DATE + timedelta(days=1, seconds=i)
        ).isoformat(timespec="seconds")

        events.append({
            "event_id": f"E{TOTAL_TRANSACTIONS + i:07d}",
            "transaction_id": transaction_id,
            "product_id": product_id,
            "customer_id": customer_id,
            "event_type": "UPDATE",
            "amount": f"{updated_amount:.2f}",
            "event_version": 2,
            "transaction_date": transaction_date.isoformat(),
            "event_timestamp": update_timestamp
        })

        update_count += 1

    else:

        reversal_timestamp = (
            BASE_DATE + timedelta(days=1, seconds=i)
        ).isoformat(timespec="seconds")

        events.append({
            "event_id": f"E{TOTAL_TRANSACTIONS + i:07d}",
            "transaction_id": transaction_id,
            "product_id": product_id,
            "customer_id": customer_id,
            "event_type": "REVERSAL",
            "amount": f"{amount:.2f}",
            "event_version": 2,
            "transaction_date": transaction_date.isoformat(),
            "event_timestamp": reversal_timestamp
        })

        reversal_count += 1


events.sort(key=lambda event: event["event_timestamp"])

fieldnames = [
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

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as file:

    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(events)


print("\n=== DATA GENERATION SUMMARY ===")
print("Output file:", OUTPUT_FILE)
print("Total events:", len(events))
print("NEW events:", new_count)
print("UPDATE events:", update_count)
print("REVERSAL events:", reversal_count)
print("Transactions:", TOTAL_TRANSACTIONS)
print("Late-arriving transactions:", late_count)
print("Data generation completed successfully!")
