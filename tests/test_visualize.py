import pytest
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from src.visualize import DataVisualizer

# Force matplotlib to use a non-interactive backend so tests don't halt opening windows
matplotlib.use('Agg')

@pytest.fixture
def mock_event_model():
    """Provides a mocked output of the Class 7 & 8 modeling layer."""
    return pd.DataFrame({
        "order_id": ["O1", "O2", "O3"],
        "is_late": [False, True, True],
        "approval_days": [0.1, 0.5, 1.2],
        "dispatch_days": [1.0, 2.5, 3.0],
        "transit_days": [3.0, 8.0, 12.0]
    })

def test_generate_insights_creates_files(tmp_path, mock_event_model):
    # tmp_path is a built-in pytest fixture that provides a unique temporary directory
    visualizer = DataVisualizer(output_dir=str(tmp_path))
    visualizer.generate_insights(mock_event_model)
    
    # Assert that the PNG files were successfully written to disk
    assert (tmp_path / "transit_times_distribution.png").exists()
    assert (tmp_path / "late_order_bottlenecks.png").exists()
    assert plt.get_fignums() == []

def test_generate_insights_handles_no_late_orders(tmp_path):
    # Edge Case: What if the pipeline runs on a perfect day with zero late orders?
    perfect_day_df = pd.DataFrame({
        "order_id": ["O1", "O2"],
        "is_late": [False, False],
        "approval_days": [0.1, 0.2],
        "dispatch_days": [1.0, 1.5],
        "transit_days": [2.0, 2.5]
    })
    
    visualizer = DataVisualizer(output_dir=str(tmp_path))
    stale_chart = tmp_path / "late_order_bottlenecks.png"
    stale_chart.write_text("stale chart", encoding="utf-8")
    visualizer.generate_insights(perfect_day_df)
    
    # The general distribution chart should still be created
    assert (tmp_path / "transit_times_distribution.png").exists()
    assert not stale_chart.exists()
    assert plt.get_fignums() == []


def test_generate_insights_removes_stale_transit_chart_when_duration_missing(tmp_path):
    stale_chart = tmp_path / "transit_times_distribution.png"
    stale_chart.write_text("stale chart", encoding="utf-8")
    event_model = pd.DataFrame({"order_id": ["O1"], "is_late": [False]})

    DataVisualizer(output_dir=str(tmp_path)).generate_insights(event_model)

    assert not stale_chart.exists()