"""Streamlit evidence dashboard for Olist pipeline runs."""

import os
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = Path(os.getenv("OLIST_OUTPUT_DIR", PROJECT_ROOT / "output"))
DEFAULT_RUN_DATE = os.getenv("DEFAULT_RUN_DATE")


def available_runs(output_root: Optional[Path] = None) -> list[str]:
    """Return output partitions that contain a KPI artifact, newest first."""
    root = output_root or OUTPUT_ROOT
    if not root.exists():
        return []
    return sorted(
        (
            directory.name
            for directory in root.iterdir()
            if directory.is_dir()
            and (directory / "data" / "kpi_dashboard.csv").is_file()
        ),
        reverse=True,
    )


def load_kpis(run_dir: Path) -> Dict[str, float]:
    """Load the pipeline KPI table into a metric-to-value mapping."""
    kpis = pd.read_csv(run_dir / "data" / "kpi_dashboard.csv")
    required_columns = {"Metric", "Value"}
    missing_columns = required_columns.difference(kpis.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"KPI artifact is missing required columns: {missing}")
    return dict(zip(kpis["Metric"], pd.to_numeric(kpis["Value"], errors="coerce")))


def main() -> None:
    st.set_page_config(page_title="Olist Delivery Reliability", layout="wide")
    st.title("Olist Delivery Reliability Dashboard")
    st.caption("Evidence dashboard for the dependable, date-partitioned data pipeline.")

    runs = available_runs()
    if not runs:
        st.error(
            f"No completed pipeline runs were found in {OUTPUT_ROOT}. "
            "Run the pipeline first to create a KPI artifact."
        )
        st.stop()

    default_index = runs.index(DEFAULT_RUN_DATE) if DEFAULT_RUN_DATE in runs else 0
    selected_run = st.sidebar.selectbox("Pipeline run", runs, index=default_index)
    run_dir = OUTPUT_ROOT / selected_run

    try:
        metrics = load_kpis(run_dir)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Unable to load KPI artifact for run {selected_run}: {error}")
        st.stop()

    total_orders = metrics.get("Total Orders Analyzed", 0)
    late_deliveries = metrics.get("Total Late Deliveries", 0)
    percentage_late = metrics.get("Percentage Late (%)", 0)

    first, second, third = st.columns(3)
    first.metric("Total Orders", f"{total_orders:,.0f}")
    second.metric("Late Deliveries", f"{late_deliveries:,.0f}")
    third.metric("Percentage Late", f"{percentage_late:.2f}%")

    st.subheader("Fulfillment-stage indicators")
    stage_metrics = {
        "Approval (days)": "Avg Approval Time (Late Orders) [Days]",
        "Dispatch (days)": "Avg Seller Dispatch Time (Late Orders) [Days]",
        "Transit (days)": "Avg Carrier Transit Time (Late Orders) [Days]",
    }
    stage_columns = st.columns(len(stage_metrics))
    for column, (label, key) in zip(stage_columns, stage_metrics.items()):
        column.metric(label, f"{metrics.get(key, 0):.2f}")

    st.subheader("Delivery and bottleneck visualizations")
    visualization_dir = run_dir / "visualizations"
    images = sorted(visualization_dir.glob("*.png"))
    if not images:
        st.info("No saved PNG visualizations are available for this run.")
    else:
        for image in images:
            st.image(str(image), caption=image.stem.replace("_", " ").title(), use_container_width=True)

    anomalies_path = run_dir / "data" / "flagged_anomalies.csv"
    with st.expander("Data Quality Exceptions"):
        if anomalies_path.is_file():
            anomalies = pd.read_csv(anomalies_path)
            st.dataframe(anomalies, use_container_width=True, hide_index=True)
            st.caption(f"{len(anomalies):,} flagged order record(s).")
        else:
            st.info("No data quality exceptions were flagged in this run.")


if __name__ == "__main__":
    main()
