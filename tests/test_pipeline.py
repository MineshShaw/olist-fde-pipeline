import pytest
import os
import sys
import pandas as pd
from unittest.mock import patch, MagicMock
from src.pipeline import PipelineOrchestrator

@patch("src.pipeline.DataVisualizer")
@patch("src.pipeline.DataModeler")
@patch("src.pipeline.DataValidator")
@patch("src.pipeline.DataExtractor")
@patch("src.pipeline.stcli.main", return_value=0)
@patch("src.pipeline.sys.exit")
def test_pipeline_orchestrator_success(MockExit, MockStreamlitMain, MockExtractor, MockValidator, MockModeler, MockVisualizer, tmp_path, monkeypatch):
    monkeypatch.setenv("DEFAULT_RUN_DATE", "previous-run")
    original_argv = sys.argv.copy()
    monkeypatch.setattr(sys, "argv", original_argv)
    # Setup Data Mocks
    mock_extractor_instance = MockExtractor.return_value
    raw_orders = pd.DataFrame({"order_id": ["O1"], "order_status": ["delivered"]})
    mock_extractor_instance.run_all.return_value = {"orders": raw_orders}
    
    mock_validator_instance = MockValidator.return_value
    mock_clean_df = raw_orders.copy()
    mock_anomalies_df = pd.DataFrame(columns=["order_status"])
    
    mock_validator_instance.run_all.return_value = {
        "orders": {"clean": mock_clean_df, "anomalies": mock_anomalies_df}
    }
    
    # Initialize with a dummy run date and temporary output path
    orchestrator = PipelineOrchestrator(run_date="2026-09-24", base_output_dir=str(tmp_path))
    stale_anomalies = orchestrator.data_dir / "flagged_anomalies.csv"
    stale_anomalies.write_text("old anomaly\n", encoding="utf-8")
    orchestrator.run()
    
    # Verify sequence
    mock_extractor_instance.run_all.assert_called_once()
    mock_validator_instance.run_all.assert_called_once()
    
    # Verify outputs triggered
    mock_modeler_instance = MockModeler.return_value
    mock_modeler_instance.generate_kpi_dashboard.return_value.to_csv.assert_called_once()
    mock_modeler_instance.generate_kpi_dashboard.assert_called_once_with(
        mock_modeler_instance.process_event_model.return_value,
        excluded_delivered_orders=0,
    )
    assert not stale_anomalies.exists()
    
    mock_visualizer_instance = MockVisualizer.return_value
    mock_visualizer_instance.generate_insights.assert_called_once()
    MockStreamlitMain.assert_called_once_with()
    MockExit.assert_called_once_with(0)
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


@patch("src.pipeline.DataValidator")
@patch("src.pipeline.DataExtractor")
def test_pipeline_fails_without_overwriting_when_all_orders_are_anomalies(
    MockExtractor, MockValidator, tmp_path
):
    raw_orders = pd.DataFrame({"order_id": ["O1"], "order_status": ["delivered"]})
    MockExtractor.return_value.run_all.return_value = {"orders": raw_orders}
    MockValidator.return_value.run_all.return_value = {
        "orders": {
            "clean": pd.DataFrame(columns=raw_orders.columns),
            "anomalies": raw_orders,
        }
    }
    orchestrator = PipelineOrchestrator(
        run_date="2026-09-24",
        base_output_dir=str(tmp_path),
    )
    previous_kpi = orchestrator.data_dir / "kpi_dashboard.csv"
    previous_kpi.write_text("previous run\n", encoding="utf-8")

    with pytest.raises(ValueError, match="No valid orders available"):
        orchestrator.run()

    assert previous_kpi.read_text(encoding="utf-8") == "previous run\n"