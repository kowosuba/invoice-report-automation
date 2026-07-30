from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import AutomationConfig


NBP_RATE_URL = (
    "https://api.nbp.pl/api/exchangerates/rates/a/{currency}/?format=json"
)


@dataclass(frozen=True)
class ExchangeRate:
    currency: str
    rate_to_pln: float
    source: str
    effective_date: str | None


def fetch_nbp_rate(
    currency: str,
    *,
    timeout: float = 5,
    opener: Callable | None = None,
) -> ExchangeRate:
    """Fetch the current NBP table A mid-rate for one currency."""
    code = currency.upper()
    if code == "PLN":
        return ExchangeRate("PLN", 1.0, "base_currency", None)

    request = Request(
        NBP_RATE_URL.format(currency=code.lower()),
        headers={
            "Accept": "application/json",
            "User-Agent": "invoice-report-automation-demo/1.0",
        },
    )
    open_url = opener or urlopen
    with open_url(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    latest_rate = payload["rates"][-1]
    return ExchangeRate(
        currency=code,
        rate_to_pln=float(latest_rate["mid"]),
        source="NBP table A",
        effective_date=str(latest_rate["effectiveDate"]),
    )


def get_exchange_rates(
    currencies: set[str],
    config: AutomationConfig,
    *,
    use_api: bool = True,
    opener: Callable | None = None,
) -> tuple[dict[str, ExchangeRate], list[str]]:
    """Resolve rates, using clearly labelled demo fallback values if needed."""
    rates: dict[str, ExchangeRate] = {}
    warnings: list[str] = []

    for code in sorted(currency.upper() for currency in currencies):
        if code == config.base_currency:
            rates[code] = ExchangeRate(code, 1.0, "base_currency", None)
            continue

        if use_api:
            try:
                rates[code] = fetch_nbp_rate(
                    code,
                    timeout=config.api_timeout_seconds,
                    opener=opener,
                )
                continue
            except (
                HTTPError,
                URLError,
                TimeoutError,
                OSError,
                ValueError,
                KeyError,
                IndexError,
            ) as error:
                warnings.append(
                    f"NBP API unavailable for {code}: {type(error).__name__}. "
                    "A demo fallback rate was used."
                )

        fallback = config.offline_exchange_rates.get(code)
        if fallback is None:
            raise ValueError(f"No exchange rate configured for currency {code}")
        rates[code] = ExchangeRate(
            currency=code,
            rate_to_pln=float(fallback),
            source="demo_fallback",
            effective_date=None,
        )

    return rates, warnings
