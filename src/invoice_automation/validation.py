from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import AutomationConfig


class MissingColumnsError(ValueError):
    """Raised when an input file does not contain the required columns."""


@dataclass
class ValidationResult:
    data: pd.DataFrame
    issues: pd.DataFrame


ISSUE_COLUMNS = [
    "row_number",
    "invoice_id",
    "field",
    "code",
    "message",
]


def validate_invoices(
    input_data: pd.DataFrame,
    config: AutomationConfig,
) -> ValidationResult:
    missing_columns = [
        column
        for column in config.required_columns
        if column not in input_data.columns
    ]
    if missing_columns:
        raise MissingColumnsError(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    data = input_data.loc[:, list(config.required_columns)].copy().reset_index(drop=True)

    for column in ["invoice_id", "client_name", "currency", "payment_status"]:
        data[column] = data[column].fillna("").astype(str).str.strip()
    data["currency"] = data["currency"].str.upper()
    data["payment_status"] = data["payment_status"].str.lower()

    for column in ["issue_date", "due_date"]:
        data[column] = pd.to_datetime(data[column], errors="coerce")
    for column in ["net_amount", "vat_rate"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    errors_by_row: dict[int, list[str]] = {index: [] for index in data.index}
    issues: list[dict] = []

    def add_issue(
        index: int,
        field: str,
        code: str,
        message: str,
    ) -> None:
        errors_by_row[index].append(message)
        invoice_id = data.at[index, "invoice_id"]
        issues.append(
            {
                "row_number": index + 2,
                "invoice_id": invoice_id,
                "field": field,
                "code": code,
                "message": message,
            }
        )

    duplicate_ids = data["invoice_id"].ne("") & data["invoice_id"].duplicated(
        keep=False
    )

    for index, row in data.iterrows():
        if not row["invoice_id"]:
            add_issue(
                index,
                "invoice_id",
                "required",
                "Invoice ID is required.",
            )
        elif bool(duplicate_ids.at[index]):
            add_issue(
                index,
                "invoice_id",
                "duplicate",
                "Invoice ID occurs more than once.",
            )

        if not row["client_name"]:
            add_issue(
                index,
                "client_name",
                "required",
                "Client name is required.",
            )

        if pd.isna(row["issue_date"]):
            add_issue(
                index,
                "issue_date",
                "invalid_date",
                "Issue date must use a valid date format.",
            )
        if pd.isna(row["due_date"]):
            add_issue(
                index,
                "due_date",
                "invalid_date",
                "Due date must use a valid date format.",
            )
        if (
            not pd.isna(row["issue_date"])
            and not pd.isna(row["due_date"])
            and row["due_date"] < row["issue_date"]
        ):
            add_issue(
                index,
                "due_date",
                "before_issue_date",
                "Due date cannot be earlier than issue date.",
            )

        if pd.isna(row["net_amount"]) or float(row["net_amount"]) <= 0:
            add_issue(
                index,
                "net_amount",
                "invalid_amount",
                "Net amount must be a positive number.",
            )

        if (
            pd.isna(row["vat_rate"])
            or float(row["vat_rate"]) not in config.allowed_vat_rates
        ):
            allowed = ", ".join(
                str(int(rate) if rate.is_integer() else rate)
                for rate in sorted(config.allowed_vat_rates)
            )
            add_issue(
                index,
                "vat_rate",
                "unsupported_vat",
                f"VAT rate must be one of: {allowed}.",
            )

        if not row["currency"]:
            add_issue(
                index,
                "currency",
                "required",
                "Currency is required.",
            )
        elif row["currency"] not in config.allowed_currencies:
            add_issue(
                index,
                "currency",
                "unsupported_currency",
                "Currency is not supported by this demo.",
            )

        if row["payment_status"] not in config.allowed_payment_statuses:
            add_issue(
                index,
                "payment_status",
                "unsupported_status",
                "Payment status must be 'paid' or 'unpaid'.",
            )

    data["is_valid"] = [
        not bool(errors_by_row[index]) for index in data.index
    ]
    data["validation_errors"] = [
        " | ".join(errors_by_row[index]) for index in data.index
    ]

    issues_frame = pd.DataFrame(issues, columns=ISSUE_COLUMNS)
    return ValidationResult(data=data, issues=issues_frame)
