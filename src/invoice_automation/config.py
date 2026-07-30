from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.json"


@dataclass(frozen=True)
class AutomationConfig:
    required_columns: tuple[str, ...]
    allowed_currencies: frozenset[str]
    allowed_vat_rates: frozenset[float]
    allowed_payment_statuses: frozenset[str]
    base_currency: str
    api_timeout_seconds: float
    offline_exchange_rates: dict[str, float]

    @classmethod
    def from_dict(cls, values: dict) -> "AutomationConfig":
        return cls(
            required_columns=tuple(values["required_columns"]),
            allowed_currencies=frozenset(
                str(value).upper() for value in values["allowed_currencies"]
            ),
            allowed_vat_rates=frozenset(
                float(value) for value in values["allowed_vat_rates"]
            ),
            allowed_payment_statuses=frozenset(
                str(value).lower() for value in values["allowed_payment_statuses"]
            ),
            base_currency=str(values.get("base_currency", "PLN")).upper(),
            api_timeout_seconds=float(values.get("api_timeout_seconds", 5)),
            offline_exchange_rates={
                str(code).upper(): float(rate)
                for code, rate in values["offline_exchange_rates"].items()
            },
        )


def load_config(path: str | Path | None = None) -> AutomationConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as stream:
        values = json.load(stream)
    return AutomationConfig.from_dict(values)
