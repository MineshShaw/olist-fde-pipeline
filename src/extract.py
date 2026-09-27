import pandas as pd
import sqlite3
import requests
import time
from collections.abc import Mapping
from urllib.parse import urlencode
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
        self.config = config or PipelineConfig(data_dir=data_dir, api_url=api_url)
        self.logger = logger or default_logger()
        self.logger.info("Initialized data extractor.")

    def extract_csv(self, filename: str) -> pd.DataFrame:
        self.logger.info(f"Preparing to open CSV file: {filename}.")
        filepath = self.config.data_dir / filename
        self.logger.info(f"Reading CSV file: {filepath}.")
        try:
            df = pd.read_csv(
                filepath,
                encoding=self.config.csv_encoding,
                sep=self.config.csv_delimiter,
            )
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
            filename = query_or_filename or self.config.sqlite_file
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
            normalized_endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}"
            query_params = urlencode(
                {
                    self.config.api_page_param: page,
                    self.config.api_page_size_param: self.config.api_page_size,
                }
            )
            url = f"{self.config.api_url}{normalized_endpoint}?{query_params}"
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
                                delay = (
                                    float(retry_after)
                                    if retry_after
                                    else self.config.api_retry_backoff
                                    * self.config.api_retry_backoff_multiplier**attempt
                                )
                            except (TypeError, ValueError):
                                delay = (
                                    self.config.api_retry_backoff
                                    * self.config.api_retry_backoff_multiplier**attempt
                                )
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
                        delay = (
                            self.config.api_retry_backoff
                            * self.config.api_retry_backoff_multiplier**attempt
                        )
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

            if not isinstance(payload, Mapping):
                error = f"Invalid API payload for {endpoint} page {page}: expected a JSON object"
                self.logger.error(error)
                raise ExtractionError(error)

            page_data = payload.get(self.config.api_response_data_key)
            if not isinstance(page_data, list):
                error = (
                    f"Invalid API payload for {endpoint} page {page}: "
                    f"'{self.config.api_response_data_key}' must be a list"
                )
                self.logger.error(error)
                raise ExtractionError(error)
            if not all(isinstance(record, Mapping) for record in page_data):
                error = (
                    f"Invalid API payload for {endpoint} page {page}: "
                    "each data record must be a JSON object"
                )
                self.logger.error(error)
                raise ExtractionError(error)

            all_data.extend(page_data)
            self.logger.info(f"Accumulated API records through page {page}: {len(all_data)}.")

            if page == 1:
                self.logger.info("Reading API pagination metadata from the first page.")
                total_pages = payload.get(self.config.api_response_total_pages_key)
                if (
                    isinstance(total_pages, bool)
                    or not isinstance(total_pages, int)
                    or total_pages < 1
                ):
                    error = (
                        f"Invalid API pagination metadata for {endpoint}: "
                        f"'{self.config.api_response_total_pages_key}' must be a positive integer"
                    )
                    self.logger.error(error)
                    raise ExtractionError(error)

                expected_total_records = payload.get(self.config.api_response_total_records_key)
                if expected_total_records is not None and (
                    isinstance(expected_total_records, bool)
                    or not isinstance(expected_total_records, int)
                    or expected_total_records < 0
                ):
                    error = (
                        f"Invalid API pagination metadata for {endpoint}: "
                        f"'{self.config.api_response_total_records_key}' must be a "
                        "non-negative integer when provided"
                    )
                    self.logger.error(error)
                    raise ExtractionError(error)
                self.logger.info(
                    f"API pagination contains {total_pages} pages and "
                    f"{expected_total_records} expected records."
                )
            else:
                response_total_pages = payload.get(self.config.api_response_total_pages_key)
                if response_total_pages is not None and (
                    isinstance(response_total_pages, bool)
                    or not isinstance(response_total_pages, int)
                    or response_total_pages < 1
                ):
                    error = (
                        f"Invalid API pagination metadata for {endpoint}: "
                        f"'{self.config.api_response_total_pages_key}' must be a "
                        "positive integer when provided"
                    )
                    self.logger.error(error)
                    raise ExtractionError(error)
                if (
                    response_total_pages is not None
                    and response_total_pages != total_pages
                ):
                    error = (
                        f"API pagination metadata changed while extracting {endpoint}: "
                        f"expected {total_pages} pages, received {response_total_pages!r}"
                    )
                    self.logger.error(error)
                    raise ExtractionError(error)

                response_total_records = payload.get(
                    self.config.api_response_total_records_key
                )
                if response_total_records is not None:
                    if (
                        isinstance(response_total_records, bool)
                        or not isinstance(response_total_records, int)
                        or response_total_records < 0
                    ):
                        error = (
                            f"Invalid API pagination metadata for {endpoint}: "
                            f"'{self.config.api_response_total_records_key}' must be a "
                            "non-negative integer when provided"
                        )
                        self.logger.error(error)
                        raise ExtractionError(error)
                    if (
                        expected_total_records is not None
                        and response_total_records != expected_total_records
                    ):
                        error = (
                            f"API record-count metadata changed while extracting {endpoint}: "
                            f"expected {expected_total_records}, "
                            f"received {response_total_records}"
                        )
                        self.logger.error(error)
                        raise ExtractionError(error)
                    expected_total_records = response_total_records

            page += 1
            self.logger.info(f"Advanced API page counter to {page}.")
                
        # --- DATA LOSS AUDIT ---
        self.logger.info("Calculating API data-loss audit counts.")
        actual_records = len(all_data)
        if expected_total_records is not None and actual_records != expected_total_records:
            self.logger.error(f"API Data Loss in {endpoint}! Expected {expected_total_records}, got {actual_records}")
            raise ExtractionError(f"Mismatch in API payload count for {endpoint}")
            
        self.logger.info(f"Extracted {actual_records} rows completely from {endpoint}.")
        self.logger.info(f"Constructing dataframe for API endpoint: {endpoint}.")
        return pd.DataFrame(all_data)

    def run_all(self) -> Dict[str, pd.DataFrame]:
        self.logger.info("Starting Class 5 Retrieval.")
        self.logger.info("Extracting orders CSV.")
        orders = self.extract_csv(self.config.csv_files["orders"])
        self.logger.info("Extracting reviews CSV.")
        reviews = self.extract_csv(self.config.csv_files["reviews"])
        self.logger.info("Extracting SQLite items.")
        items = self.extract_sqlite()
        self.logger.info("Extracting SQLite customers table.")
        customers = self.extract_sqlite(
            self.config.db_queries["customers"], filename=self.config.sqlite_file
        )
        self.logger.info("Extracting SQLite sellers table.")
        sellers = self.extract_sqlite(
            self.config.db_queries["sellers"], filename=self.config.sqlite_file
        )
        self.logger.info("Extracting SQLite products table.")
        products = self.extract_sqlite(
            self.config.db_queries["products"], filename=self.config.sqlite_file
        )
        self.logger.info("Extracting SQLite category translation table.")
        category_translation = self.extract_sqlite(
            self.config.db_queries["category_translation"],
            filename=self.config.sqlite_file,
        )
        self.logger.info("Extracting payments API data.")
        payments = self.extract_api(self.config.api_endpoints["payments"])
        self.logger.info("Extracting geolocation API data.")
        geolocation = self.extract_api(self.config.api_endpoints["geolocation"])
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