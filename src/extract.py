import pandas as pd
import sqlite3
import requests
import time
from pathlib import Path
from typing import Dict, Optional
from src.config import PipelineConfig
from src.logger import PipelineLogger, default_logger

class ExtractionError(Exception):
    pass

class DataExtractor:
    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        logger: Optional[PipelineLogger] = None,
        data_dir: Optional[str] = None,
        api_url: Optional[str] = None,
    ):
        self.config = config or PipelineConfig(
            data_dir=Path(data_dir) if data_dir is not None else PipelineConfig().data_dir,
            api_url=api_url if api_url is not None else PipelineConfig().api_url,
        )
        self.logger = logger or default_logger()
        self.logger.info("Initialized data extractor.")

    def extract_csv(self, filename: str) -> pd.DataFrame:
        self.logger.info(f"Preparing to open CSV file: {filename}.")
        filepath = self.config.data_dir / filename
        self.logger.info(f"Reading CSV file: {filepath}.")
        try:
            df = pd.read_csv(filepath)
        except (FileNotFoundError, OSError) as error:
            self.logger.error(f"CSV extraction failed for {filename}: {error}")
            raise ExtractionError(f"CSV Extraction failed: {error}") from error
        self.logger.info(f"Extracted {len(df)} rows from {filename}.")
        return df

    def extract_sqlite(
        self,
        query_or_filename: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> pd.DataFrame:
        query = self.config.db_query
        if filename is None:
            filename = query_or_filename or "raw/ecommerce.db"
        else:
            query = query_or_filename or self.config.db_query
        self.logger.info(f"Preparing to open SQLite file: {filename}.")
        filepath = self.config.data_dir / filename
        self.logger.info(f"Opening SQLite connection: {filepath}.")
        with sqlite3.connect(filepath) as conn:
            self.logger.info(f"Executing SQLite query: {query}.")
            df = pd.read_sql_query(query, conn)
        self.logger.info("Closed SQLite connection.")
        self.logger.info(f"Extracted {len(df)} rows from SQLite DB.")
        return df

    def extract_api(self, endpoint: str) -> pd.DataFrame:
        self.logger.info(f"Starting API extraction for endpoint: {endpoint}.")
        all_data = []
        page = 1
        total_pages = 1
        expected_total_records = None
        
        while page <= total_pages:
            self.logger.info(f"Starting API page loop for page {page} of {total_pages}.")
            url = f"{self.config.api_url}{endpoint}?page={page}"
            self.logger.info(f"Requesting API URL: {url}.")
            for attempt in range(self.config.api_max_retries + 1):
                try:
                    response = requests.get(url, timeout=self.config.api_timeout)
                    self.logger.info(f"Received API response for page {page}.")
                    status_code = getattr(response, "status_code", None)
                    is_retryable_status = (
                        isinstance(status_code, int)
                        and (status_code == 429 or 500 <= status_code < 600)
                    )
                    if is_retryable_status:
                        if attempt < self.config.api_max_retries:
                            retry_after = response.headers.get("Retry-After")
                            try:
                                delay = float(retry_after) if retry_after else self.config.api_retry_backoff * (2 ** attempt)
                            except (TypeError, ValueError):
                                delay = self.config.api_retry_backoff * (2 ** attempt)
                            self.logger.warn(
                                f"API rate limit/transient failure for {endpoint} page {page} "
                                f"(status {response.status_code}); retry {attempt + 1}/"
                                f"{self.config.api_max_retries} in {delay:g}s."
                            )
                            time.sleep(delay)
                            continue
                    response.raise_for_status()
                    self.logger.info(f"Validated API response for page {page}.")
                    payload = response.json()
                    self.logger.info(f"Decoded API payload for page {page}.")
                    break
                except requests.exceptions.HTTPError as error:
                    self.logger.error(f"API request failed for {endpoint}: {error}")
                    raise ExtractionError(f"API Extraction failed: {error}") from error
                except requests.exceptions.RequestException as error:
                    if attempt < self.config.api_max_retries:
                        delay = self.config.api_retry_backoff * (2 ** attempt)
                        self.logger.warn(
                            f"API request failure for {endpoint} page {page}: {error}; "
                            f"retry {attempt + 1}/{self.config.api_max_retries} in {delay:g}s."
                        )
                        time.sleep(delay)
                        continue
                    self.logger.error(f"API request failed for {endpoint}: {error}")
                    raise ExtractionError(f"API Extraction failed: {error}") from error
            else:
                error = f"API retries exhausted for {endpoint} page {page}"
                self.logger.error(error)
                raise ExtractionError(error)

            all_data.extend(payload.get("data", []))
            self.logger.info(f"Accumulated API records through page {page}: {len(all_data)}.")

            if page == 1:
                self.logger.info("Reading API pagination metadata from the first page.")
                total_pages = payload.get("total_pages", 1)
                expected_total_records = payload.get("total_records")
                self.logger.info(f"API pagination contains {total_pages} pages and {expected_total_records} expected records.")

            page += 1
            self.logger.info(f"Advanced API page counter to {page}.")
                
        # --- DATA LOSS AUDIT ---
        self.logger.info("Calculating API data-loss audit counts.")
        actual_records = len(all_data)
        if expected_total_records is None:
            self.logger.info("API did not provide an expected record count; using received records as the audit baseline.")
            expected_total_records = actual_records
        if actual_records != expected_total_records:
            self.logger.error(f"API Data Loss in {endpoint}! Expected {expected_total_records}, got {actual_records}")
            raise ExtractionError(f"Mismatch in API payload count for {endpoint}")
            
        self.logger.info(f"Extracted {actual_records} rows completely from {endpoint}.")
        self.logger.info(f"Constructing dataframe for API endpoint: {endpoint}.")
        return pd.DataFrame(all_data)

    def run_all(self) -> Dict[str, pd.DataFrame]:
        self.logger.info("Starting Class 5 Retrieval.")
        self.logger.info("Extracting orders CSV.")
        orders = self.extract_csv("raw/orders.csv")
        self.logger.info("Extracting reviews CSV.")
        reviews = self.extract_csv("raw/reviews.csv")
        self.logger.info("Extracting SQLite items.")
        items = self.extract_sqlite()
        self.logger.info("Extracting SQLite customers table.")
        customers = self.extract_sqlite("SELECT * FROM customers", filename="raw/ecommerce.db")
        self.logger.info("Extracting SQLite sellers table.")
        sellers = self.extract_sqlite("SELECT * FROM sellers", filename="raw/ecommerce.db")
        self.logger.info("Extracting SQLite products table.")
        products = self.extract_sqlite("SELECT * FROM products", filename="raw/ecommerce.db")
        self.logger.info("Extracting SQLite category translation table.")
        category_translation = self.extract_sqlite(
            "SELECT * FROM category_translation", filename="raw/ecommerce.db"
        )
        self.logger.info("Extracting payments API data.")
        payments = self.extract_api("/payments")
        self.logger.info("Extracting geolocation API data.")
        geolocation = self.extract_api("/geolocation")
        self.logger.info("Assembling all extracted datasets.")
        return {
            "orders": orders,
            "reviews": reviews,
            "items": items,
            "customers": customers,
            "sellers": sellers,
            "products": products,
            "category_translation": category_translation,
            "payments": payments,
            "geolocation": geolocation
        }