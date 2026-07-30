from __future__ import annotations

import sys
from datetime import date
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from invoice_automation.pipeline import PipelineResult, run_pipeline
from invoice_automation.reporting import (
    build_csv_report,
    build_excel_report,
    build_json_report,
)
from invoice_automation.validation import MissingColumnsError


st.set_page_config(
    page_title="Invoice Report Automation",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_demo_data() -> pd.DataFrame:
    return pd.read_csv(PROJECT_ROOT / "data" / "sample_invoices.csv")


def show_result(result: PipelineResult) -> None:
    summary = result.summary
    metric_columns = st.columns(5)
    metric_columns[0].metric("Input rows", summary["input_rows"])
    metric_columns[1].metric("Valid invoices", summary["valid_invoices"])
    metric_columns[2].metric("Invalid rows", summary["invalid_rows"])
    metric_columns[3].metric("Overdue", summary["overdue_invoices"])
    metric_columns[4].metric(
        "Total gross (PLN)",
        f"{summary['total_gross_pln']:,.2f}",
    )

    for warning in result.warnings:
        st.warning(warning)

    overview_tab, data_tab, issues_tab, rates_tab = st.tabs(
        ["Overview", "Valid invoices", "Validation issues", "Exchange rates"]
    )
    with overview_tab:
        left, right = st.columns(2)
        with left:
            st.subheader("By currency")
            st.dataframe(result.by_currency, use_container_width=True)
        with right:
            st.subheader("By client")
            st.dataframe(result.by_client, use_container_width=True)

    with data_tab:
        st.dataframe(result.valid_invoices, use_container_width=True)

    with issues_tab:
        if result.issues.empty:
            st.success("No validation issues were found.")
        else:
            st.dataframe(result.issues, use_container_width=True)

    with rates_tab:
        rates = pd.DataFrame(
            [
                {
                    "currency": code,
                    "rate_to_pln": rate.rate_to_pln,
                    "source": rate.source,
                    "effective_date": rate.effective_date,
                }
                for code, rate in sorted(result.exchange_rates.items())
            ]
        )
        st.dataframe(rates, use_container_width=True)

    st.subheader("Download generated reports")
    download_columns = st.columns(3)
    download_columns[0].download_button(
        "Download Excel report",
        data=build_excel_report(result),
        file_name="invoice_report.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True,
    )
    download_columns[1].download_button(
        "Download processed CSV",
        data=build_csv_report(result),
        file_name="processed_invoices.csv",
        mime="text/csv",
        use_container_width=True,
    )
    download_columns[2].download_button(
        "Download JSON summary",
        data=build_json_report(result),
        file_name="summary_report.json",
        mime="application/json",
        use_container_width=True,
    )


st.title("Invoice Report Automation")
st.write(
    "A portfolio demo that validates invoice data, converts currencies to PLN "
    "and generates business-ready reports."
)
st.caption(
    "All built-in records are fictional. Uploaded files are processed only "
    "during the current application session."
)

with st.sidebar:
    st.header("Automation settings")
    source = st.radio(
        "Data source",
        ["Built-in demo data", "Upload a CSV file"],
    )
    reporting_date = st.date_input("Reporting date", value=date.today())
    use_nbp_api = st.toggle(
        "Use current NBP exchange rates",
        value=True,
        help=(
            "If the API is unavailable, the app uses clearly labelled "
            "demonstration fallback rates."
        ),
    )

if source == "Built-in demo data":
    input_data = load_demo_data()
    st.info(
        "The demo file intentionally contains several incorrect rows so the "
        "validation process is visible."
    )
else:
    uploaded_file = st.file_uploader("Upload invoice data", type=["csv"])
    if uploaded_file is None:
        st.stop()
    try:
        input_data = pd.read_csv(BytesIO(uploaded_file.getvalue()))
    except Exception as error:
        st.error(f"The CSV file could not be read: {error}")
        st.stop()

with st.expander("Preview input data"):
    st.dataframe(input_data, use_container_width=True)

if st.button("Run automation", type="primary", use_container_width=True):
    try:
        st.session_state["automation_result"] = run_pipeline(
            input_data,
            reporting_date=reporting_date,
            use_api=use_nbp_api,
        )
    except MissingColumnsError as error:
        st.error(str(error))
    except Exception as error:
        st.error(f"Automation could not be completed: {error}")

if "automation_result" in st.session_state:
    show_result(st.session_state["automation_result"])
