import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class PipelineConfig:
    # Environment variables with safe local defaults
    api_url: str = os.getenv("OLIST_API_URL", "http://localhost:8000")
    data_dir: Path = Path(os.getenv("OLIST_DATA_DIR", "data"))
    base_output_dir: Path = Path(os.getenv("OLIST_OUTPUT_DIR", "output"))
    api_timeout: int = int(os.getenv("OLIST_API_TIMEOUT", "10"))
    db_query: str = os.getenv("OLIST_DB_QUERY", "SELECT * FROM order_items")