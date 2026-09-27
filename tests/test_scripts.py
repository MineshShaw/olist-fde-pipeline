import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_wrapper_rejects_invalid_calendar_date_before_setup():
    result = subprocess.run(
        ["bash", str(PROJECT_ROOT / "run_pipeline.sh"), "2026-02-30"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "real calendar date" in result.stderr
