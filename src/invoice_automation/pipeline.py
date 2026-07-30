from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from .config import AutomationConfig, load_config
from .exchange_rates import ExchangeRate, get_exchange_rates
from .validation import ValidationResult, validate_invoices


@dataclass
class PipelineResult:
    processed_data: pd.DataFrame
    valid_invoices: pd.DataFrame
    issues: pd.DataFrame
    summary: dict
    by_currency: pd.DataFrame
    by_client: pd.DataFrame
    exchange_rates: dict[str, ExchangeRate]
    warnings: list[str]
    reporting_date: str


def _parse_reporting_date(value: str | date | None) -> pd.Timestamp:
    if value is None:
        return pd.Timestamp(date.today())
    parsed = pd.Timestamp(value)
    if pd.isna(parsed):
        raise ValueError("Reporting date is invalid.")
    return parsed.normalize()


def run_pipeline(
    input_data: pd.DataFrame,
    *,
    config: AutomationConfig | None = None,
    reporting_date: str | date | None = None,
    use_api: bool = True,
    opener=None,
) -> PipelineResult:
    active_config = config or load_config()
    as_of = _parse_reporting_date(reporting_date)
    validation: ValidationResult = validate_invoices(input_data, active_config)

    processed = validation.data.copy()
    valid_mask = processed["is_valid"]
    currencies = set(processed.loc[valid_mask, "currency"].dropna().unique())
    exchange_rates, warnings = get_exchange_rates(
        currencies,
        active_config,
        use_api=use_api,
        opener=opener,
    )

    processed["exchange_rate_to_pln"] = processed["currency"].map(
        {code: rate.rate_to_pln for code, rate in exchange_rates.items()}
    )
    processed["rate_source"] = processed["currency"].map(
        {code: rate.source for code, rate in exchange_rates.items()}
    )
    processed["vat_amount"] = (
        processed["net_amount"] * processed["vat_rate"] / 100
    ).round(2)
    processed["gross_amount"] = (
        processed["net_amount"] + processed["vat_amount"]
    ).round(2)
    processed["gross_amount_pln"] = (
        processed["gross_amount"] * processed["exchange_rate_to_pln"]
    ).round(2)

    processed["is_overdue"] = (
        valid_mask
        & processed["payment_status"].eq("unpaid")
        & processed["due_date"].lt(as_of)
    )
    processed["days_overdue"] = 0
    overdue_mask = processed["is_overdue"]
    processed.loc[overdue_mask, "days_overdue"] = (
        as_of - processed.loc[overdue_mask, "due_date"]
    ).dt.days

    calculation_columns = [
        "exchange_rate_to_pln",
        "rate_source",
        "vat_amount",
        "gross_amount",
        "gross_amount_pln",
    ]
    processed.loc[~valid_mask, calculation_columns] = pd.NA

    valid = processed.loc[valid_mask].copy()
    overdue = valid.loc[valid["is_overdue"]]
    summary = {
        "input_rows": int(len(processed)),
        "valid_invoices": int(valid_mask.sum()),
        "invalid_rows": int((~valid_mask).sum()),
        "validation_issues": int(len(validation.issues)),
        "unique_clients": int(valid["client_name"].nunique()),
        "overdue_invoices": int(valid["is_overdue"].sum()),
        "total_gross_pln": round(float(valid["gross_amount_pln"].sum()), 2),
        "overdue_gross_pln": round(
            float(overdue["gross_amount_pln"].sum()),
            2,
        ),
    }

    if valid.empty:
        by_currency = pd.DataFrame(
            columns=[
                "currency",
                "invoice_count",
                "gross_amount_original",
                "gross_amount_pln",
            ]
        )
        by_client = pd.DataFrame(
            columns=[
                "client_name",
                "invoice_count",
                "gross_amount_pln",
                "overdue_invoices",
            ]
        )
    else:
        by_currency = (
            valid.groupby("currency", as_index=False)
            .agg(
                invoice_count=("invoice_id", "count"),
                gross_amount_original=("gross_amount", "sum"),
                gross_amount_pln=("gross_amount_pln", "sum"),
            )
            .sort_values("currency")
        )
        by_client = (
            valid.groupby("client_name", as_index=False)
            .agg(
                invoice_count=("invoice_id", "count"),
                gross_amount_pln=("gross_amount_pln", "sum"),
                overdue_invoices=("is_overdue", "sum"),
            )
            .sort_values("gross_amount_pln", ascending=False)
        )

    return PipelineResult(
        processed_data=processed,
        valid_invoices=valid,
        issues=validation.issues,
        summary=summary,
        by_currency=by_currency,
        by_client=by_client,
        exchange_rates=exchange_rates,
        warnings=warnings,
        reporting_date=as_of.date().isoformat(),
    )
