import pandas as pd
import sqlite3
import requests
import logging
from pathlib import Path
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExtractionError(Exception):
    """Custom exception for Class 5 Retrieval failures."""
    pass

class DataExtractor:
    def __init__(self, data_dir: str = "data", api_url: str = "http://localhost:8000"):
        """
        Configurable extractor. In a production environment, 
        these defaults would be overridden by environment variables.
        """
        self.data_dir = Path(data_dir)
        self.api_url = api_url.rstrip("/")

    def extract_csv(self, filename: str = "raw/orders.csv") -> pd.DataFrame:
        filepath = self.data_dir / filename
        logger.info(f"Extracting CSV from {filepath}")
        try:
            # Preserving raw inputs by reading all as string/objects initially if needed, 
            # but standard parsing is fine as long as we don't drop rows.
            return pd.read_csv(filepath)
        except Exception as e:
            logger.error(f"Failed to extract CSV {filepath}: {e}")
            raise ExtractionError(f"CSV Extraction failed: {e}")

    def extract_sqlite(self, query: str, filename: str = "raw/ecommerce.db") -> pd.DataFrame:
        filepath = self.data_dir / filename
        logger.info(f"Extracting from SQLite DB at {filepath}")
        try:
            # Context manager ensures connection is safely closed even if pandas fails
            with sqlite3.connect(filepath) as conn:
                return pd.read_sql_query(query, conn)
        except sqlite3.Error as e:
            logger.error(f"SQLite extraction failed for {filepath}: {e}")
            raise ExtractionError(f"SQLite Extraction failed: {e}")

    def extract_api(self, endpoint: str = "/payments.json", timeout: int = 10) -> pd.DataFrame:
        url = f"{self.api_url}{endpoint}"
        logger.info(f"Extracting from API at {url}")
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()  # Catch HTTP errors
            
            # Assuming the API returns a JSON array of records
            data = response.json()
            return pd.DataFrame(data)
        except requests.exceptions.RequestException as e:
            logger.error(f"API extraction failed for {url}: {e}")
            raise ExtractionError(f"API Extraction failed: {e}")

    def run_all(self) -> Dict[str, pd.DataFrame]:
        """Orchestrates the Class 5 retrieval step."""
        logger.info("Starting Class 5 Retrieval...")
        
        raw_data = {
            "orders": self.extract_csv("raw/orders.csv"),
            "reviews": self.extract_csv("raw/reviews.csv"),
            "items": self.extract_sqlite("SELECT * FROM order_items", "raw/ecommerce.db"),
            "payments": self.extract_api("/payments.json"),
            "geolocation": self.extract_api("/geolocation.json")
        }
        
        logger.info("Class 5 Retrieval complete.")
        return raw_data