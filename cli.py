from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from invoice_automation.pipeline import run_pipeline
from invoice_automation.reporting import write_reports


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate invoice CSV data, convert values to PLN and generate reports."
        )
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=str(PROJECT_ROOT / "data" / "sample_invoices.csv"),
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "output"),
        help="Directory for generated reports.",
    )
    parser.add_argument(
        "--as-of",
        dest="reporting_date",
        default=None,
        help="Reporting date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip NBP API calls and use clearly labelled demo fallback rates.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    input_path = Path(arguments.input)

    try:
        invoices = pd.read_csv(input_path)
        result = run_pipeline(
            invoices,
            reporting_date=arguments.reporting_date,
            use_api=not arguments.offline,
        )
        paths = write_reports(result, arguments.output)
    except Exception as error:
        print(f"Automation failed: {error}", file=sys.stderr)
        return 1

    print("Automation completed successfully.")
    print(f"Input rows: {result.summary['input_rows']}")
    print(f"Valid invoices: {result.summary['valid_invoices']}")
    print(f"Invalid rows: {result.summary['invalid_rows']}")
    print(f"Overdue invoices: {result.summary['overdue_invoices']}")
    print(f"Total gross value (PLN): {result.summary['total_gross_pln']:.2f}")
    if result.warnings:
        for warning in result.warnings:
            print(f"Warning: {warning}")
    print("Generated files:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
