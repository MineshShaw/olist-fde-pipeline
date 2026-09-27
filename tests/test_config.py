import pytest

from src.config import PipelineConfig


def test_yaml_values_are_loaded_and_environment_overrides_them(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "api:\n  url: https://yaml.example\n  page_size: 200\n"
        "paths:\n  raw_data: yaml-data\n  output_dir: yaml-output\n"
        "ui:\n  default_theme: dark\n  port: 8600\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("OLIST_API_URL", raising=False)
    monkeypatch.delenv("OLIST_API_PAGE_SIZE", raising=False)
    monkeypatch.delenv("OLIST_DATA_DIR", raising=False)
    monkeypatch.delenv("OLIST_OUTPUT_DIR", raising=False)
    monkeypatch.delenv("OLIST_DEFAULT_THEME", raising=False)
    monkeypatch.delenv("OLIST_DASHBOARD_PORT", raising=False)

    config = PipelineConfig(config_path=config_path)

    assert config.api_url == "https://yaml.example"
    assert config.api_page_size == 200
    assert config.data_dir.name == "yaml-data"
    assert config.base_output_dir.name == "yaml-output"
    assert config.ui_default_theme == "dark"
    assert config.ui_port == 8600

    monkeypatch.setenv("OLIST_API_URL", "https://env.example")
    monkeypatch.setenv("OLIST_API_PAGE_SIZE", "300")
    overridden = PipelineConfig(config_path=config_path)
    assert overridden.api_url == "https://env.example"
    assert overridden.api_page_size == 300


def test_explicit_constructor_values_override_yaml_and_environment(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("api:\n  timeout: 30\n", encoding="utf-8")
    monkeypatch.setenv("OLIST_API_TIMEOUT", "20")

    config = PipelineConfig(config_path=config_path, api_timeout=5)

    assert config.api_timeout == 5


def test_invalid_configuration_values_are_reported(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("api:\n  timeout: 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="api.timeout"):
        PipelineConfig(config_path=config_path)


def test_invalid_yaml_section_shape_is_reported(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("api: not-a-mapping\n", encoding="utf-8")

    with pytest.raises(ValueError, match="api"):
        PipelineConfig(config_path=config_path)


@pytest.mark.parametrize(
    "yaml_text,unknown_key",
    [
        ("unknown: true\n", "unknown"),
        ("api:\n  page_sze: 100\n", "api.page_sze"),
        ("ui:\n  port: 8501\n  typo: true\n", "ui.typo"),
    ],
)
def test_unknown_yaml_keys_are_rejected(tmp_path, yaml_text, unknown_key):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml_text, encoding="utf-8")

    with pytest.raises(ValueError, match=unknown_key):
        PipelineConfig(config_path=config_path)


def test_yaml_values_must_match_expected_scalar_types(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("api:\n  timeout: fast\n", encoding="utf-8")

    with pytest.raises(ValueError, match="api.timeout.*numeric"):
        PipelineConfig(config_path=config_path)


def test_config_path_semantics_are_resolved_from_raw_data_and_run_partition(tmp_path):
    config_path = tmp_path / "config.yaml"
    raw_data = tmp_path / "source-data"
    output_dir = tmp_path / "results"
    config_path.write_text(
        f"paths:\n  raw_data: {raw_data}\n"
        f"  output_dir: {output_dir}\n"
        "  sqlite_file: raw/catalog.db\n"
        "  output_data_dir: data\n"
        "sources:\n  csv:\n    orders: raw/orders.csv\n",
        encoding="utf-8",
    )

    config = PipelineConfig(config_path=config_path)

    assert config.data_dir / config.csv_files["orders"] == raw_data / "raw/orders.csv"
    assert config.data_dir / config.sqlite_file == raw_data / "raw/catalog.db"
    assert config.base_output_dir / "2026-09-27" / config.output_data_dir == (
        output_dir / "2026-09-27" / "data"
    )
