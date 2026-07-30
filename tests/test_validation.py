from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from invoice_automation.config import load_config
from invoice_automation.validation import MissingColumnsError, validate_invoices


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()

    def test_detects_duplicate_missing_client_and_negative_amount(self) -> None:
        data = pd.DataFrame(
            [
                {
                    "invoice_id": "FV-1",
                    "client_name": "Client A",
                    "issue_date": "2026-07-01",
                    "due_date": "2026-07-10",
                    "currency": "PLN",
                    "net_amount": 100,
                    "vat_rate": 23,
                    "payment_status": "paid",
                },
                {
                    "invoice_id": "FV-1",
                    "client_name": "",
                    "issue_date": "2026-07-02",
                    "due_date": "2026-07-12",
                    "currency": "PLN",
                    "net_amount": -5,
                    "vat_rate": 23,
                    "payment_status": "unpaid",
                },
            ]
        )

        result = validate_invoices(data, self.config)

        self.assertEqual(result.data["is_valid"].tolist(), [False, False])
        self.assertEqual(
            set(result.issues["code"]),
            {"duplicate", "required", "invalid_amount"},
        )
        self.assertEqual(len(result.issues), 4)

    def test_rejects_missing_columns(self) -> None:
        with self.assertRaises(MissingColumnsError):
            validate_invoices(pd.DataFrame({"invoice_id": ["FV-1"]}), self.config)


if __name__ == "__main__":
    unittest.main()
