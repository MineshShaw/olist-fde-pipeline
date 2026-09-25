import pytest
from unittest.mock import patch, MagicMock
from src.pipeline import PipelineOrchestrator

@patch("src.pipeline.DataVisualizer")
@patch("src.pipeline.DataModeler")
@patch("src.pipeline.DataValidator")
@patch("src.pipeline.DataExtractor")
def test_pipeline_orchestrator_success(MockExtractor, MockValidator, MockModeler, MockVisualizer, tmp_path):
    # Setup Data Mocks
    mock_extractor_instance = MockExtractor.return_value
    mock_extractor_instance.run_all.return_value = {"mock": "data"}
    
    mock_validator_instance = MockValidator.return_value
    mock_clean_df = MagicMock()
    mock_clean_df.empty = False 
    mock_anomalies_df = MagicMock()
    mock_anomalies_df.empty = True
    
    mock_validator_instance.run_all.return_value = {
        "orders": {"clean": mock_clean_df, "anomalies": mock_anomalies_df}
    }
    
    # Initialize with a dummy run date and temporary output path
    orchestrator = PipelineOrchestrator(run_date="2026-09-24", base_output_dir=str(tmp_path))
    orchestrator.run()
    
    # Verify sequence
    mock_extractor_instance.run_all.assert_called_once()
    mock_validator_instance.run_all.assert_called_once()
    
    # Verify outputs triggered
    mock_modeler_instance = MockModeler.return_value
    mock_modeler_instance.generate_kpi_dashboard.return_value.to_csv.assert_called_once()
    
    mock_visualizer_instance = MockVisualizer.return_value
    mock_visualizer_instance.generate_insights.assert_called_once()