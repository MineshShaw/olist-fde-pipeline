import pandas as pd
import sqlite3
import requests
import logging
from typing import Dict
from src.config import PipelineConfig

logger = logging.getLogger(__name__)

class ExtractionError(Exception):
    pass

class DataExtractor:
    def __init__(self, config: PipelineConfig):
        self.config = config

    def extract_csv(self, filename: str) -> pd.DataFrame:
        filepath = self.config.data_dir / filename
        df = pd.read_csv(filepath)
        logger.info(f"Extracted {len(df)} rows from {filename}")
        return df

    def extract_sqlite(self, filename: str = "raw/ecommerce.db") -> pd.DataFrame:
        filepath = self.config.data_dir / filename
        with sqlite3.connect(filepath) as conn:
            df = pd.read_sql_query(self.config.db_query, conn)
        logger.info(f"Extracted {len(df)} rows from SQLite DB")
        return df

    def extract_api(self, endpoint: str) -> pd.DataFrame:
        all_data = []
        page = 1
        total_pages = 1
        expected_total_records = 0
        
        while page <= total_pages:
            url = f"{self.config.api_url}{endpoint}?page={page}"
            try:
                response = requests.get(url, timeout=self.config.api_timeout)
                response.raise_for_status()
                payload = response.json()
                
                all_data.extend(payload.get("data", []))
                
                if page == 1:
                    total_pages = payload.get("total_pages", 1)
                    expected_total_records = payload.get("total_records", 0)
                
                page += 1
            except requests.exceptions.RequestException as e:
                raise ExtractionError(f"API Extraction failed: {e}")
                
        # --- DATA LOSS AUDIT ---
        actual_records = len(all_data)
        if actual_records != expected_total_records:
            logger.error(f"API Data Loss in {endpoint}! Expected {expected_total_records}, got {actual_records}")
            raise ExtractionError(f"Mismatch in API payload count for {endpoint}")
            
        logger.info(f"Extracted {actual_records} rows completely from {endpoint}")
        return pd.DataFrame(all_data)

    def run_all(self) -> Dict[str, pd.DataFrame]:
        logger.info("Starting Class 5 Retrieval...")
        return {
            "orders": self.extract_csv("raw/orders.csv"),
            "reviews": self.extract_csv("raw/reviews.csv"),
            "items": self.extract_sqlite(),
            "payments": self.extract_api("/payments"),
            "geolocation": self.extract_api("/geolocation")
        }