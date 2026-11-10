from src.database import initialize_database
from src.pipeline import run_pipeline

from pathlib import Path
import sys
import time


BASE_DIR = Path(__file__).resolve().parent


def main():

    print("\n=== INCREMENTAL METRICS PIPELINE ===\n")

    initialize_database()

    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
        if not input_file.is_absolute():
            input_file = BASE_DIR / input_file
    else:
        input_file = BASE_DIR / "data" / "sample_events.csv"

    print("Selected input:", input_file)

    start_time = time.perf_counter()

    report = run_pipeline(input_file)

    end_time = time.perf_counter()

    execution_time = end_time - start_time

    print("\n=== PERFORMANCE SUMMARY ===")
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Input events: {report['input_count']}")
    print(f"Accepted events: {report['accepted_count']}")
    print(f"Rejected events: {report['rejected_count']}")
    print(f"Duplicate events: {report['duplicate_count']}")
    print(f"Pipeline status: {report['status']}")

    print("\nPipeline execution completed!")


if __name__ == "__main__":
    main()
