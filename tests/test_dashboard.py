import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from src import dashboard


def test_available_runs_only_lists_published_complete_runs(tmp_path):
    completed = tmp_path / "2026-09-27"
    data_dir = completed / dashboard.CONFIG.output_data_dir
    data_dir.mkdir(parents=True)
    (data_dir / dashboard.CONFIG.artifacts["kpi_file"]).write_text(
        "Metric,Value\n", encoding="utf-8"
    )
    (completed / "_SUCCESS.json").write_text(
        json.dumps({"status": "completed", "run_date": "2026-09-27"}),
        encoding="utf-8",
    )

    incomplete = tmp_path / "2026-09-28"
    incomplete_data = incomplete / dashboard.CONFIG.output_data_dir
    incomplete_data.mkdir(parents=True)
    (incomplete_data / dashboard.CONFIG.artifacts["kpi_file"]).write_text(
        "Metric,Value\n", encoding="utf-8"
    )
    (incomplete / "_RUN_STATUS.json").write_text(
        json.dumps({"status": "failed", "run_date": "2026-09-28"}),
        encoding="utf-8",
    )

    malformed = tmp_path / "2026-09-29"
    malformed_data = malformed / dashboard.CONFIG.output_data_dir
    malformed_data.mkdir(parents=True)
    (malformed_data / dashboard.CONFIG.artifacts["kpi_file"]).touch()
    (malformed / "_SUCCESS.json").write_text("{invalid", encoding="utf-8")

    assert dashboard.available_runs(tmp_path) == ["2026-09-27"]


def test_dashboard_loads_default_run_and_renders_operational_tabs(tmp_path, monkeypatch):
    run_dir = tmp_path / "2026-09-27"
    data_dir = run_dir / "data"
    data_dir.mkdir(parents=True)
    (run_dir / "visualizations").mkdir()
    (run_dir / "_SUCCESS.json").write_text(
        json.dumps({"status": "completed", "run_date": run_dir.name}),
        encoding="utf-8",
    )
    metrics = {
        "Total Orders Analyzed": 1,
        "Total Late Deliveries": 1,
        "Percentage Late (%)": 100,
        "Delivered Orders Excluded from KPI": 0,
        "Delivered Orders Evaluated": 1,
        "Comparable Delivery Coverage (%)": 100,
        "Avg Order Approval Time (All Comparable Delivered) [Days]": 0.1,
        "Avg Seller Dispatch Time (All Comparable Delivered) [Days]": 0.2,
        "Avg Carrier Transit Time (All Comparable Delivered) [Days]": 0.3,
        "Avg Order Approval Time (Late Orders) [Days]": 0.1,
        "Avg Seller Dispatch Time (Late Orders) [Days]": 0.2,
        "Avg Carrier Transit Time (Late Orders) [Days]": 0.3,
    }
    pd.DataFrame(
        {"Metric": list(metrics), "Value": list(metrics.values())}
    ).to_csv(data_dir / "kpi_dashboard.csv", index=False)
    pd.DataFrame({"order_id": ["O1"]}).to_csv(
        data_dir / "clean_event_model.csv", index=False
    )
    pd.DataFrame(
        {"seller_id": ["S1"], "seller_order_count": [1]}
    ).to_csv(data_dir / "seller_accountability.csv", index=False)
    monkeypatch.setenv("OLIST_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("DEFAULT_RUN_DATE", run_dir.name)

    dashboard_script = Path(__file__).resolve().parents[1] / "src" / "dashboard.py"
    app = AppTest.from_file(dashboard_script).run()

    assert not app.exception
    assert len(app.tabs) == 4
    assert app.radio[0].value == run_dir.name
