import pytest
from unittest.mock import patch, MagicMock
from src.pipeline import PipelineOrchestrator

@patch("src.pipeline.DataModeler")
@patch("src.pipeline.DataValidator")
@patch("src.pipeline.DataExtractor")
def test_pipeline_orchestrator_success(MockExtractor, MockValidator, MockModeler, tmp_path):
    # Setup Mocks
    mock_extractor_instance = MockExtractor.return_value
    mock_extractor_instance.run_all.return_value = {"mock": "data"}
    
    mock_validator_instance = MockValidator.return_value
    
    # Ensure dataframe isn't treated as empty by mocking .empty as False
    mock_clean_df = MagicMock()
    mock_clean_df.empty = False 
    mock_anomalies_df = MagicMock()
    mock_anomalies_df.empty = True
    
    mock_validator_instance.run_all.return_value = {
        "orders": {"clean": mock_clean_df, "anomalies": mock_anomalies_df}
    }
    
    # Set output directory to a temporary pytest folder
    orchestrator = PipelineOrchestrator(output_dir=str(tmp_path))
    orchestrator.run()
    
    # Assertions
    mock_extractor_instance.run_all.assert_called_once()
    mock_validator_instance.run_all.assert_called_once()
    
    # Verify Model outputs were "saved" (to_csv called)
    mock_modeler_instance = MockModeler.return_value
    mock_modeler_instance.generate_kpi_dashboard.return_value.to_csv.assert_called_once()