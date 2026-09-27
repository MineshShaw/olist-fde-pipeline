"""Executive Streamlit dashboard for Olist delivery operations."""

import os
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from src.config import PipelineConfig

CONFIG = PipelineConfig()
os.environ.setdefault("STREAMLIT_THEME_BASE", CONFIG.ui_default_theme)

import streamlit as st


OUTPUT_ROOT = CONFIG.base_output_dir
DEFAULT_RUN_DATE = os.getenv(CONFIG.default_run_date_env)

KPI_LABELS = {
    "Total Orders Analyzed": "Total Orders",
    "Total Late Deliveries": "Late Deliveries",
    "Percentage Late (%)": "Percentage Late",
}
STAGE_METRICS = {
    "Approval": "Avg Approval Time (Late Orders) [Days]",
    "Seller Dispatch": "Avg Seller Dispatch Time (Late Orders) [Days]",
    "Carrier Transit": "Avg Carrier Transit Time (Late Orders) [Days]",
}
CHARTS = (
    (CONFIG.artifacts["bottleneck_chart_file"], "Average Stage Duration for Late Orders"),
    (CONFIG.artifacts["transit_chart_file"], "Carrier Transit Time Distribution"),
)


def available_runs(output_root: Optional[Path] = None) -> list[str]:
    """Return completed output partitions, newest first."""
    root = output_root or OUTPUT_ROOT
    if not root.is_dir():
        return []
    return sorted(
        (
            directory.name
            for directory in root.iterdir()
            if directory.is_dir()
            and (
                directory
                / CONFIG.output_data_dir
                / CONFIG.artifacts["kpi_file"]
            ).is_file()
        ),
        reverse=True,
    )


@st.cache_data(show_spinner="Loading run metrics...")
def load_kpis(kpi_path: str, modified_ns: int) -> pd.DataFrame:
    """Read a run's KPI artifact; cached by file path."""
    return pd.read_csv(kpi_path)


@st.cache_data(show_spinner="Loading clean order data...")
def load_clean_data(data_path: str, modified_ns: int) -> pd.DataFrame:
    """Read the clean event model; cached by file path."""
    return pd.read_csv(data_path)


@st.cache_data(show_spinner="Loading quality exceptions...")
def load_anomalies(anomaly_path: str, modified_ns: int) -> pd.DataFrame:
    """Read the flagged anomaly artifact; cached by file path."""
    return pd.read_csv(anomaly_path)


def _load_csv(loader, path: Path) -> pd.DataFrame:
    return loader(str(path), path.stat().st_mtime_ns)


def _metric_value(metrics: Dict[str, float], key: str) -> float:
    value = metrics.get(key, 0)
    return float(value) if pd.notna(value) else 0.0


def _display_chart(run_dir: Path, filename: str, caption: str) -> None:
    image_path = run_dir / CONFIG.output_visualizations_dir / filename
    if image_path.is_file():
        st.image(str(image_path), caption=caption, use_container_width=True)
    else:
        st.info(f"{caption} is not available for this run.")


def main() -> None:
    st.set_page_config(
        page_title=CONFIG.ui_page_title,
        page_icon=CONFIG.ui_page_icon,
        layout=CONFIG.ui_layout,
    )

    st.title(CONFIG.ui_page_title)
    st.markdown(
        """
        **Operational view of the customer delivery promise.** Track late deliveries,
        investigate approval, seller dispatch, and carrier transit bottlenecks, and
        review the order-level evidence behind each run.
        """
    )

    runs = available_runs()
    if not runs:
        st.error(
            f"No completed pipeline runs were found in `{OUTPUT_ROOT}`. "
            "Run the pipeline to create dashboard artifacts."
        )
        st.stop()

    st.sidebar.markdown(
        f"""
        <style>
        /* 1. Limit the height and add a scrollbar to the list of choices */
        section[data-testid="stSidebar"] [role="radiogroup"] {{
            max-height: {CONFIG.sidebar_date_list_height_px}px;
            overflow-y: auto;
            padding-right: 0.4rem;
        }}
        
        /* 2. Change the font size of the radio button label ("Available run dates") */
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
            font-size: 1.5rem !important;
            font-weight: bold !important;
        }}

        /* 3. Change the font size of the radio options (the run dates list) */
        section[data-testid="stSidebar"] [data-testid="stRadio"] label p {{
            font-size: 1rem !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    default_index = runs.index(DEFAULT_RUN_DATE) if DEFAULT_RUN_DATE in runs else 0
    selected_run = st.sidebar.radio(
        "Available run dates",
        runs,
        index=default_index,
    )
    run_dir = OUTPUT_ROOT / selected_run
    data_dir = run_dir / CONFIG.output_data_dir

    try:
        kpis = _load_csv(load_kpis, data_dir / CONFIG.artifacts["kpi_file"])
        required_columns = {"Metric", "Value"}
        missing_columns = required_columns.difference(kpis.columns)
        if missing_columns:
            raise ValueError(
                f"KPI artifact is missing required columns: {', '.join(sorted(missing_columns))}"
            )
        metrics = dict(
            zip(kpis["Metric"], pd.to_numeric(kpis["Value"], errors="coerce"))
        )
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Unable to load KPI artifact for run {selected_run}: {error}")
        st.stop()

    summary_tab, data_tab, quality_tab = st.tabs(
        ["📊 Executive Summary", "🗃️ Full Data Explorer", "⚠️ Quality Exceptions"]
    )

    with summary_tab:
        st.subheader(f"Run {selected_run}")
        metric_columns = st.columns(3)
        for column, metric_key in zip(
            metric_columns,
            ("Total Orders Analyzed", "Total Late Deliveries", "Percentage Late (%)"),
        ):
            value = _metric_value(metrics, metric_key)
            if metric_key == "Percentage Late (%)":
                formatted_value = f"{value:.2f}%"
            else:
                formatted_value = f"{value:,.0f}"
            column.metric(KPI_LABELS[metric_key], formatted_value)

        st.subheader("Delivery bottlenecks and transit distribution")
        chart_columns = st.columns(2)
        for column, (filename, caption) in zip(chart_columns, CHARTS):
            with column:
                _display_chart(run_dir, filename, caption)

        st.subheader("Stage Duration Breakdown")
        stage_breakdown = pd.DataFrame(
            [
                {
                    "Fulfillment Stage": stage,
                    "Average Duration (Days)": _metric_value(metrics, metric_key),
                }
                for stage, metric_key in STAGE_METRICS.items()
            ]
        )
        st.dataframe(
            stage_breakdown,
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Stage averages are calculated over late orders in this pipeline run.")

    with data_tab:
        st.subheader("Clean order event model")
        clean_path = data_dir / CONFIG.artifacts["event_model_file"]
        try:
            clean_data = _load_csv(load_clean_data, clean_path)
        except (OSError, pd.errors.ParserError) as error:
            st.error(f"Unable to load the clean event model for run {selected_run}: {error}")
            st.stop()

        order_search = st.text_input(
            "Filter by order ID",
            placeholder="Enter an order_id or part of an ID",
        ).strip()
        if order_search:
            if "order_id" not in clean_data.columns:
                st.error("The clean event model does not contain an `order_id` column.")
                st.stop()
            visible_data = clean_data[
                clean_data["order_id"]
                .astype("string")
                .str.contains(order_search, case=False, na=False, regex=False)
            ]
        else:
            visible_data = clean_data

        st.caption(
            f"Showing {len(visible_data):,} of {len(clean_data):,} clean order records."
        )
        st.dataframe(visible_data, use_container_width=True)

    with quality_tab:
        st.subheader("Data Quality Exceptions")
        anomaly_path = data_dir / CONFIG.artifacts["anomalies_file"]
        if not anomaly_path.is_file():
            st.info("No data quality exceptions were flagged in this run.")
        else:
            try:
                anomalies = _load_csv(load_anomalies, anomaly_path)
            except (OSError, pd.errors.ParserError) as error:
                st.error(f"Unable to load flagged anomalies for run {selected_run}: {error}")
                st.stop()
            st.error(f"{len(anomalies):,} anomalous order record(s) flagged.")
            st.dataframe(anomalies, use_container_width=True)


if __name__ == "__main__":
    main()
