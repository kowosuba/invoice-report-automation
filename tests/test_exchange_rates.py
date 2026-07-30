from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from urllib.error import URLError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from invoice_automation.config import load_config
from invoice_automation.exchange_rates import fetch_nbp_rate, get_exchange_rates


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class ExchangeRateTests(unittest.TestCase):
    def test_parses_nbp_json_response(self) -> None:
        observed: dict = {}

        def fake_opener(request, timeout):
            observed["url"] = request.full_url
            observed["timeout"] = timeout
            return FakeResponse(
                {
                    "table": "A",
                    "currency": "euro",
                    "code": "EUR",
                    "rates": [
                        {
                            "no": "145/A/NBP/2026",
                            "effectiveDate": "2026-07-29",
                            "mid": 4.321,
                        }
                    ],
                }
            )

        rate = fetch_nbp_rate("eur", timeout=3, opener=fake_opener)

        self.assertEqual(rate.currency, "EUR")
        self.assertEqual(rate.rate_to_pln, 4.321)
        self.assertEqual(rate.source, "NBP table A")
        self.assertEqual(rate.effective_date, "2026-07-29")
        self.assertTrue(observed["url"].startswith("https://api.nbp.pl/"))
        self.assertEqual(observed["timeout"], 3)

    def test_uses_labelled_fallback_when_api_is_unavailable(self) -> None:
        def failing_opener(request, timeout):
            raise URLError("simulated outage")

        rates, warnings = get_exchange_rates(
            {"EUR", "PLN"},
            load_config(),
            use_api=True,
            opener=failing_opener,
        )

        self.assertEqual(rates["EUR"].source, "demo_fallback")
        self.assertEqual(rates["PLN"].source, "base_currency")
        self.assertEqual(len(warnings), 1)
        self.assertIn("NBP API unavailable for EUR", warnings[0])


if __name__ == "__main__":
    unittest.main()
