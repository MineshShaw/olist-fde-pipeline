import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config import PipelineConfig
from src.pipeline import DataExtractor, PipelineOrchestrator


def _source_data():
    orders = pd.DataFrame(
        {
            "order_id": ["O1"],
            "customer_id": ["C1"],
            "order_status": ["delivered"],
            "order_purchase_timestamp": ["2024-01-01 10:00:00"],
            "order_approved_at": ["2024-01-01 12:00:00"],
            "order_delivered_carrier_date": ["2024-01-02 12:00:00"],
            "order_delivered_customer_date": ["2024-01-05 12:00:00"],
            "order_estimated_delivery_date": ["2024-01-04 12:00:00"],
        }
    )
    return {
        "orders": orders,
        "items": pd.DataFrame(
            {
                "order_id": ["O1"],
                "order_item_id": [1],
                "seller_id": ["S1"],
                "price": [25.0],
                "freight_value": [5.0],
            }
        ),
        "payments": pd.DataFrame(
            {
                "order_id": ["O1"],
                "payment_sequential": [1],
                "payment_value": [30.0],
            }
        ),
        "customers": pd.DataFrame(
            {
                "customer_id": ["C1"],
                "customer_zip_code_prefix": ["01234"],
                "customer_state": ["SP"],
            }
        ),
        "sellers": pd.DataFrame(
            {"seller_id": ["S1"], "seller_state": ["SP"], "seller_city": ["Sao Paulo"]}
        ),
        "geolocation": pd.DataFrame(
            {
                "geolocation_zip_code_prefix": ["01234"],
                "geolocation_lat": [-23.5],
                "geolocation_lng": [-46.6],
                "geolocation_state": ["SP"],
            }
        ),
    }


def _api_response():
    response = MagicMock(status_code=200)
    response.raise_for_status.return_value = None
    return response


@patch("src.pipeline.DataVisualizer")
@patch("src.pipeline.DataExtractor")
@patch("src.pipeline.requests.get", return_value=_api_response())
@patch("src.pipeline.stcli.main", return_value=0)
@patch("src.pipeline.sys.exit")
def test_pipeline_success_publishes_enriched_run_and_hands_off_to_dashboard(
    mock_exit,
    mock_streamlit,
    mock_api_get,
    mock_extractor_class,
    mock_visualizer_class,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("DEFAULT_RUN_DATE", "previous-run")
    monkeypatch.setattr(sys, "argv", ["python", "-m", "src.pipeline"])
    raw_data = _source_data()
    mock_extractor_class.return_value.run_all.return_value = raw_data
    mock_visualizer_class.return_value.generate_insights.return_value = None

    final_data = tmp_path / "2026-09-24" / "data"
    final_data.mkdir(parents=True)
    (final_data / "kpi_dashboard.csv").write_text(
        "old KPI\n", encoding="utf-8"
    )
    (final_data / "flagged_anomalies.csv").write_text(
        "old anomaly\n", encoding="utf-8"
    )
    orchestrator = PipelineOrchestrator(
        run_date="2026-09-24",
        base_output_dir=str(tmp_path),
    )
    stage_dir = orchestrator.stage_dir
    orchestrator.run()

    assert not stage_dir.exists()
    assert (tmp_path / "2026-09-24" / "_SUCCESS.json").is_file()
    manifest = json.loads(
        (tmp_path / "2026-09-24" / "_SUCCESS.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "completed"
    assert manifest["raw_orders"] == 1
    assert mock_api_get.call_count == 1

    output_data = tmp_path / "2026-09-24" / "data"
    event_model = pd.read_csv(output_data / "clean_event_model.csv")
    assert len(event_model) == 1
    assert event_model.loc[0, "item_revenue"] == 25.0
    assert event_model.loc[0, "payment_total"] == 30.0
    assert event_model.loc[0, "geo_state"] == "SP"
    assert (output_data / "seller_accountability.csv").is_file()
    assert not (output_data / "flagged_anomalies.csv").exists()

    mock_visualizer_class.return_value.generate_insights.assert_called_once()
    mock_streamlit.assert_called_once_with()
    mock_exit.assert_called_once_with(0)
    assert sys.argv == [
        "streamlit",
        "run",
        "src/dashboard.py",
        "--server.port",
        "8501",
        "--theme.base",
        "light",
    ]
    assert os.environ["DEFAULT_RUN_DATE"] == "2026-09-24"
    assert os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] == "false"


@patch("src.pipeline.DataExtractor")
@patch("src.pipeline.requests.get")
def test_api_preflight_fails_with_clear_incomplete_attempt(
    mock_api_get,
    mock_extractor_class,
    tmp_path,
):
    import requests

    mock_api_get.side_effect = requests.exceptions.ConnectionError("connection refused")
    orchestrator = PipelineOrchestrator("2026-09-24", base_output_dir=str(tmp_path))

    with pytest.raises(RuntimeError, match="Start the service or correct api.url"):
        orchestrator.run()

    assert not (tmp_path / "2026-09-24").exists()
    status_files = list(tmp_path.glob(".*.staging-*/_RUN_STATUS.json"))
    assert len(status_files) == 1
    assert json.loads(status_files[0].read_text())["status"] == "failed"
    mock_extractor_class.assert_not_called()


@patch("src.pipeline.DataValidator")
@patch("src.pipeline.DataExtractor")
@patch("src.pipeline.requests.get", return_value=_api_response())
def test_all_anomaly_attempt_saves_evidence_and_preserves_previous_partition(
    mock_api_get,
    mock_extractor_class,
    mock_validator_class,
    tmp_path,
):
    orders = _source_data()["orders"]
    mock_extractor_class.return_value.run_all.return_value = {"orders": orders}
    mock_validator_class.return_value.run_all.return_value = {
        "orders": {
            "clean": orders.iloc[0:0],
            "anomalies": orders,
        }
    }
    final_dir = tmp_path / "2026-09-24"
    old_kpi = final_dir / "data" / "kpi_dashboard.csv"
    old_kpi.parent.mkdir(parents=True)
    old_kpi.write_text("previous complete run\n", encoding="utf-8")
    (final_dir / "_SUCCESS.json").write_text(
        json.dumps({"status": "completed", "run_date": "2026-09-24"}),
        encoding="utf-8",
    )

    orchestrator = PipelineOrchestrator("2026-09-24", base_output_dir=str(tmp_path))
    with pytest.raises(ValueError, match="No valid orders available"):
        orchestrator.run()

    assert old_kpi.read_text(encoding="utf-8") == "previous complete run\n"
    assert json.loads((final_dir / "_SUCCESS.json").read_text())["status"] == "completed"
    attempt_dir = orchestrator.stage_dir
    assert (attempt_dir / "data" / "flagged_anomalies.csv").is_file()
    assert json.loads((attempt_dir / "_RUN_STATUS.json").read_text())["status"] == "failed"


@patch("src.pipeline.DataVisualizer")
@patch("src.pipeline.requests.get", return_value=_api_response())
def test_failed_visualization_preserves_existing_completed_run(
    mock_api_get,
    mock_visualizer_class,
    tmp_path,
):
    mock_visualizer_class.return_value.generate_insights.side_effect = RuntimeError(
        "chart failure"
    )
    final_dir = tmp_path / "2026-09-24"
    old_file = final_dir / "data" / "kpi_dashboard.csv"
    old_file.parent.mkdir(parents=True)
    old_file.write_text("old published KPI\n", encoding="utf-8")
    (final_dir / "_SUCCESS.json").write_text(
        json.dumps({"status": "completed", "run_date": "2026-09-24"}),
        encoding="utf-8",
    )

    orchestrator = PipelineOrchestrator(
        "2026-09-24",
        config=PipelineConfig(base_output_dir=tmp_path),
    )

    with patch.object(DataExtractor, "run_all", return_value=_source_data()):
        with pytest.raises(RuntimeError, match="chart failure"):
            orchestrator.run()

    assert old_file.read_text(encoding="utf-8") == "old published KPI\n"
    assert json.loads((final_dir / "_SUCCESS.json").read_text())["status"] == "completed"


@patch("src.pipeline.DataVisualizer")
@patch("src.pipeline.requests.get", return_value=_api_response())
def test_failed_partition_swap_restores_previous_published_run(
    mock_api_get,
    mock_visualizer_class,
    tmp_path,
    monkeypatch,
):
    final_dir = tmp_path / "2026-09-24"
    prior_file = final_dir / "data" / "kpi_dashboard.csv"
    prior_file.parent.mkdir(parents=True)
    prior_file.write_text("old published KPI\n", encoding="utf-8")
    (final_dir / "_SUCCESS.json").write_text(
        json.dumps({"status": "completed", "run_date": "2026-09-24"}),
        encoding="utf-8",
    )

    orchestrator = PipelineOrchestrator(
        "2026-09-24",
        config=PipelineConfig(base_output_dir=tmp_path),
    )
    with patch.object(DataExtractor, "run_all", return_value=_source_data()):
        real_replace = os.replace
        failed = False

        def fail_staging_promotion(source, destination):
            nonlocal failed
            if Path(source) == orchestrator.stage_dir and not failed:
                failed = True
                raise OSError("simulated publication error")
            return real_replace(source, destination)

        monkeypatch.setattr("src.pipeline.os.replace", fail_staging_promotion)
        with pytest.raises(OSError, match="simulated publication error"):
            orchestrator.run()

    assert prior_file.read_text(encoding="utf-8") == "old published KPI\n"
    assert json.loads((final_dir / "_SUCCESS.json").read_text())["status"] == "completed"
