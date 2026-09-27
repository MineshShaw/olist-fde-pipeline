"""YAML-backed application configuration with environment overrides."""

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Optional

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULTS: dict[str, Any] = {
    "api": {
        "url": "http://localhost:8000",
        "timeout": 10,
        "max_retries": 3,
        "retry_backoff": 1.0,
        "retry_backoff_multiplier": 2.0,
        "page_size": 500,
        "page_param": "page",
        "page_size_param": "page_size",
        "response_data_key": "data",
        "response_total_pages_key": "total_pages",
        "response_total_records_key": "total_records",
        "endpoints": {"payments": "/payments", "geolocation": "/geolocation"},
    },
    "paths": {
        "raw_data": "data",
        "output_dir": "output",
        "sqlite_file": "raw/ecommerce.db",
        "output_logs_dir": "logs",
        "output_data_dir": "data",
        "output_visualizations_dir": "visualizations",
    },
    "artifacts": {
        "kpi_file": "kpi_dashboard.csv",
        "event_model_file": "clean_event_model.csv",
        "anomalies_file": "flagged_anomalies.csv",
        "transit_chart_file": "transit_times_distribution.png",
        "bottleneck_chart_file": "late_order_bottlenecks.png",
    },
    "sources": {
        "csv": {
            "orders": "raw/orders.csv",
            "reviews": "raw/reviews.csv",
            "encoding": "utf-8",
            "delimiter": ",",
        },
    },
    "db": {
        "default_query": "SELECT * FROM order_items",
        "queries": {
            "customers": "SELECT * FROM customers",
            "sellers": "SELECT * FROM sellers",
            "products": "SELECT * FROM products",
            "category_translation": "SELECT * FROM category_translation",
        },
    },
    "model": {
        "seconds_per_day": 86400.0,
        "timestamps": {
            "purchase": "order_purchase_timestamp",
            "approval": "order_approved_at",
            "dispatch": "order_delivered_carrier_date",
            "delivery": "order_delivered_customer_date",
            "estimate": "order_estimated_delivery_date",
        },
    },
    "validation": {
        "delivered_status": "delivered",
    },
    "visualization": {
        "style": "whitegrid",
        "palette": {"on_time": "blue", "late": "red", "stages": "viridis"},
        "transit_bins": 30,
        "transit_figure_size": [10, 6],
        "bottleneck_figure_size": [8, 5],
    },
    "ui": {
        "default_theme": "light",
        "page_title": "Olist Delivery Reliability",
        "page_icon": "📦",
        "layout": "wide",
        "dashboard_script": "src/dashboard.py",
        "port": 8501,
        "default_run_date_env": "DEFAULT_RUN_DATE",
        "sidebar_date_list_height_px": 320,
    },
}

ENV_OVERRIDES: dict[str, tuple[str, type]] = {
    "OLIST_API_URL": ("api.url", str),
    "OLIST_API_TIMEOUT": ("api.timeout", float),
    "OLIST_API_MAX_RETRIES": ("api.max_retries", int),
    "OLIST_API_RETRY_BACKOFF": ("api.retry_backoff", float),
    "OLIST_API_RETRY_BACKOFF_MULTIPLIER": ("api.retry_backoff_multiplier", float),
    "OLIST_API_PAGE_SIZE": ("api.page_size", int),
    "OLIST_API_PAGE_PARAM": ("api.page_param", str),
    "OLIST_API_PAGE_SIZE_PARAM": ("api.page_size_param", str),
    "OLIST_API_ENDPOINT_PAYMENTS": ("api.endpoints.payments", str),
    "OLIST_API_ENDPOINT_GEOLOCATION": ("api.endpoints.geolocation", str),
    "OLIST_DATA_DIR": ("paths.raw_data", str),
    "OLIST_OUTPUT_DIR": ("paths.output_dir", str),
    "OLIST_SQLITE_FILE": ("paths.sqlite_file", str),
    "OLIST_OUTPUT_LOGS_DIR": ("paths.output_logs_dir", str),
    "OLIST_OUTPUT_DATA_DIR": ("paths.output_data_dir", str),
    "OLIST_OUTPUT_VISUALIZATIONS_DIR": ("paths.output_visualizations_dir", str),
    "OLIST_ORDERS_CSV": ("sources.csv.orders", str),
    "OLIST_REVIEWS_CSV": ("sources.csv.reviews", str),
    "OLIST_CSV_ENCODING": ("sources.csv.encoding", str),
    "OLIST_CSV_DELIMITER": ("sources.csv.delimiter", str),
    "OLIST_DB_QUERY": ("db.default_query", str),
    "OLIST_DB_CUSTOMERS_QUERY": ("db.queries.customers", str),
    "OLIST_DB_SELLERS_QUERY": ("db.queries.sellers", str),
    "OLIST_DB_PRODUCTS_QUERY": ("db.queries.products", str),
    "OLIST_DB_CATEGORY_TRANSLATION_QUERY": ("db.queries.category_translation", str),
    "OLIST_SECONDS_PER_DAY": ("model.seconds_per_day", float),
    "OLIST_TIMESTAMP_PURCHASE": ("model.timestamps.purchase", str),
    "OLIST_TIMESTAMP_APPROVAL": ("model.timestamps.approval", str),
    "OLIST_TIMESTAMP_DISPATCH": ("model.timestamps.dispatch", str),
    "OLIST_TIMESTAMP_DELIVERY": ("model.timestamps.delivery", str),
    "OLIST_TIMESTAMP_ESTIMATE": ("model.timestamps.estimate", str),
    "OLIST_DELIVERED_STATUS": ("validation.delivered_status", str),
    "OLIST_VISUALIZATION_STYLE": ("visualization.style", str),
    "OLIST_VISUALIZATION_ON_TIME_COLOR": ("visualization.palette.on_time", str),
    "OLIST_VISUALIZATION_LATE_COLOR": ("visualization.palette.late", str),
    "OLIST_VISUALIZATION_STAGES_PALETTE": ("visualization.palette.stages", str),
    "OLIST_TRANSIT_BINS": ("visualization.transit_bins", int),
    "OLIST_TRANSIT_FIGURE_SIZE": ("visualization.transit_figure_size", list),
    "OLIST_BOTTLENECK_FIGURE_SIZE": ("visualization.bottleneck_figure_size", list),
    "OLIST_DEFAULT_THEME": ("ui.default_theme", str),
    "OLIST_UI_PAGE_TITLE": ("ui.page_title", str),
    "OLIST_UI_PAGE_ICON": ("ui.page_icon", str),
    "OLIST_UI_LAYOUT": ("ui.layout", str),
    "OLIST_DASHBOARD_SCRIPT": ("ui.dashboard_script", str),
    "OLIST_DASHBOARD_PORT": ("ui.port", int),
    "OLIST_DEFAULT_RUN_DATE_ENV": ("ui.default_run_date_env", str),
    "OLIST_SIDEBAR_DATE_LIST_HEIGHT_PX": ("ui.sidebar_date_list_height_px", int),
    "OLIST_KPI_FILE": ("artifacts.kpi_file", str),
    "OLIST_EVENT_MODEL_FILE": ("artifacts.event_model_file", str),
    "OLIST_ANOMALIES_FILE": ("artifacts.anomalies_file", str),
    "OLIST_TRANSIT_CHART_FILE": ("artifacts.transit_chart_file", str),
    "OLIST_BOTTLENECK_CHART_FILE": ("artifacts.bottleneck_chart_file", str),
}


def _merge_mapping(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, Mapping) and isinstance(target.get(key), dict):
            _merge_mapping(target[key], value)
        else:
            target[key] = value


def _set_nested(target: dict[str, Any], dotted_key: str, value: Any) -> None:
    keys = dotted_key.split(".")
    current = target
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = value


def _convert_environment_value(converter: type, value: str) -> Any:
    if converter is list:
        converted = [float(part.strip()) for part in value.split(",")]
        if len(converted) != 2:
            raise ValueError("expected two comma-separated numbers")
        return converted
    return converter(value)


class PipelineConfig:
    """Configuration view shared by extraction, modeling, UI, and output layers.

    Values are loaded in this order (later sources take precedence):
    defaults, ``config.yaml``, environment variables, explicit constructor values.
    Raw-data and output roots resolve from the repository root; source filenames
    resolve from the raw-data root and output subdirectories from each run partition.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        base_output_dir: Optional[Path] = None,
        api_url: Optional[str] = None,
        api_timeout: Optional[int] = None,
        api_max_retries: Optional[int] = None,
        api_retry_backoff: Optional[float] = None,
        db_query: Optional[str] = None,
        api_page_size: Optional[int] = None,
        config_path: Optional[Path] = None,
    ):
        self.project_root = PROJECT_ROOT
        configured_path = (
            Path(config_path)
            if config_path is not None
            else Path(os.getenv("OLIST_CONFIG_FILE", self.project_root / "config.yaml"))
        )
        if not configured_path.is_absolute():
            configured_path = self.project_root / configured_path

        settings = _copy_mapping(DEFAULTS)
        if configured_path.is_file():
            try:
                loaded = yaml.safe_load(configured_path.read_text(encoding="utf-8")) or {}
            except (OSError, yaml.YAMLError) as error:
                raise ValueError(f"Unable to load configuration file {configured_path}: {error}") from error
            if not isinstance(loaded, Mapping):
                raise ValueError(f"Configuration file must contain a YAML mapping: {configured_path}")
            _validate_mapping_shape(DEFAULTS, loaded)
            _merge_mapping(settings, loaded)
        self.config_path = configured_path

        for env_name, (key, converter) in ENV_OVERRIDES.items():
            if env_name in os.environ:
                try:
                    value = _convert_environment_value(converter, os.environ[env_name])
                except (TypeError, ValueError) as error:
                    raise ValueError(f"Invalid value for {env_name}: {os.environ[env_name]!r}") from error
                _set_nested(settings, key, value)

        explicit_values = {
            "paths.raw_data": data_dir,
            "paths.output_dir": base_output_dir,
            "api.url": api_url,
            "api.timeout": api_timeout,
            "api.max_retries": api_max_retries,
            "api.retry_backoff": api_retry_backoff,
            "api.page_size": api_page_size,
            "db.default_query": db_query,
        }
        for key, value in explicit_values.items():
            if value is not None:
                _set_nested(settings, key, str(value) if key.startswith("paths.") else value)

        self.settings = settings
        self._validate()

        paths = settings["paths"]
        self.data_dir = self._path(paths["raw_data"])
        self.base_output_dir = self._path(paths["output_dir"])
        self.sqlite_file = str(paths["sqlite_file"])

        api = settings["api"]
        self.api_url = str(api["url"]).rstrip("/")
        self.api_timeout = float(api["timeout"])
        self.api_max_retries = int(api["max_retries"])
        self.api_retry_backoff = float(api["retry_backoff"])
        self.api_retry_backoff_multiplier = float(api["retry_backoff_multiplier"])
        self.api_page_size = int(api["page_size"])
        self.api_page_param = str(api["page_param"])
        self.api_page_size_param = str(api["page_size_param"])
        self.api_response_data_key = str(api["response_data_key"])
        self.api_response_total_pages_key = str(api["response_total_pages_key"])
        self.api_response_total_records_key = str(api["response_total_records_key"])
        self.api_endpoints = dict(api["endpoints"])

        self.csv_files = dict(settings["sources"]["csv"])
        self.csv_encoding = str(settings["sources"]["csv"]["encoding"])
        self.csv_delimiter = str(settings["sources"]["csv"]["delimiter"])
        self.db_query = str(settings["db"]["default_query"])
        self.db_queries = dict(settings["db"]["queries"])
        self.seconds_per_day = float(settings["model"]["seconds_per_day"])
        self.timestamp_columns = dict(settings["model"]["timestamps"])
        self.delivered_status = str(settings["validation"]["delivered_status"])

        self.output_logs_dir = str(paths["output_logs_dir"])
        self.output_data_dir = str(paths["output_data_dir"])
        self.output_visualizations_dir = str(paths["output_visualizations_dir"])
        self.artifacts = dict(settings["artifacts"])

        visualization = settings["visualization"]
        self.visualization_style = str(visualization["style"])
        self.visualization_palette = dict(visualization["palette"])
        self.transit_bins = int(visualization["transit_bins"])
        self.transit_figure_size = tuple(visualization["transit_figure_size"])
        self.bottleneck_figure_size = tuple(visualization["bottleneck_figure_size"])

        ui = settings["ui"]
        self.ui_default_theme = str(ui["default_theme"])
        self.ui_page_title = str(ui["page_title"])
        self.ui_page_icon = str(ui["page_icon"])
        self.ui_layout = str(ui["layout"])
        self.dashboard_script = str(ui["dashboard_script"])
        self.ui_port = int(ui["port"])
        self.default_run_date_env = str(ui["default_run_date_env"])
        self.sidebar_date_list_height_px = int(ui["sidebar_date_list_height_px"])

    def _path(self, value: Any) -> Path:
        path = Path(value).expanduser()
        return path if path.is_absolute() else self.project_root / path

    def _validate(self) -> None:
        api = self.settings["api"]
        for key in ("timeout", "page_size"):
            if float(api[key]) <= 0:
                raise ValueError(f"api.{key} must be greater than zero")
        for key in ("max_retries", "retry_backoff"):
            if float(api[key]) < 0:
                raise ValueError(f"api.{key} cannot be negative")
        for key in ("max_retries", "page_size"):
            if int(api[key]) != float(api[key]):
                raise ValueError(f"api.{key} must be an integer")
        if float(api["retry_backoff_multiplier"]) < 1:
            raise ValueError("api.retry_backoff_multiplier must be at least one")
        if int(self.settings["ui"]["port"]) < 1 or int(self.settings["ui"]["port"]) > 65535:
            raise ValueError("ui.port must be between 1 and 65535")
        if self.settings["ui"]["default_theme"] not in {"light", "dark"}:
            raise ValueError("ui.default_theme must be either 'light' or 'dark'")
        for setting in ("transit_figure_size", "bottleneck_figure_size"):
            size = self.settings["visualization"][setting]
            if (
                not isinstance(size, (list, tuple))
                or len(size) != 2
                or any(float(dimension) <= 0 for dimension in size)
            ):
                raise ValueError(f"visualization.{setting} must contain two positive dimensions")
        if int(self.settings["visualization"]["transit_bins"]) < 1:
            raise ValueError("visualization.transit_bins must be greater than zero")
        if float(self.settings["model"]["seconds_per_day"]) <= 0:
            raise ValueError("model.seconds_per_day must be greater than zero")
        if int(self.settings["ui"]["sidebar_date_list_height_px"]) < 1:
            raise ValueError("ui.sidebar_date_list_height_px must be greater than zero")


def _copy_mapping(mapping: Mapping[str, Any]) -> dict[str, Any]:
    return deepcopy(dict(mapping))


def _validate_mapping_shape(
    expected: Mapping[str, Any],
    supplied: Mapping[str, Any],
    prefix: str = "",
) -> None:
    for key, value in supplied.items():
        dotted_key = f"{prefix}.{key}" if prefix else str(key)
        if key not in expected:
            raise ValueError(f"Unknown configuration key {dotted_key!r}")
        if isinstance(expected[key], Mapping):
            if not isinstance(value, Mapping):
                raise ValueError(f"Configuration section {dotted_key!r} must be a YAML mapping")
            _validate_mapping_shape(expected[key], value, dotted_key)
        elif isinstance(value, Mapping):
            raise ValueError(f"Configuration value {dotted_key!r} must not be a YAML mapping")
        elif isinstance(expected[key], bool) and not isinstance(value, bool):
            raise ValueError(f"Configuration value {dotted_key!r} must be a boolean")
        elif isinstance(expected[key], (int, float)) and (
            isinstance(value, bool) or not isinstance(value, (int, float))
        ):
            raise ValueError(f"Configuration value {dotted_key!r} must be numeric")
        elif isinstance(expected[key], str) and not isinstance(value, str):
            raise ValueError(f"Configuration value {dotted_key!r} must be a string")
        elif isinstance(expected[key], list) and not isinstance(value, list):
            raise ValueError(f"Configuration value {dotted_key!r} must be a YAML list")
