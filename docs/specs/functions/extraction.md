# Extraction function specification

Module: `src/extract.py`

## `ExtractionError`

Domain exception raised when CSV extraction cannot open its file or API extraction fails, returns an invalid payload, has invalid pagination metadata, or fails record-count reconciliation. SQLite errors currently propagate from `sqlite3`/Pandas rather than being wrapped.

## `DataExtractor(config=None, logger=None, data_dir=None, api_url=None)`

Creates an extractor. A supplied `PipelineConfig` is used as-is; otherwise a new configuration is made with optional data-root and API URL overrides. A default run-scoped logger is created if no logger is supplied.

## `extract_csv(filename) -> pandas.DataFrame`

Reads a configured-delimited/encoded CSV at `config.data_dir / filename`.

- **Input:** configured path relative to raw-data root, or an absolute path.
- **Output:** DataFrame containing all parsed rows and columns.
- **Errors:** wraps `FileNotFoundError` and `OSError` as `ExtractionError`; Pandas parse/encoding errors may propagate unwrapped.
- **Side effects:** logs the path and number of extracted rows; no mutation of source.

## `extract_sqlite(query_or_filename=None, filename=None) -> pandas.DataFrame`

Reads a configured SQLite query using a connection at `config.data_dir / filename`.

- If `filename` is omitted, `query_or_filename` is interpreted as the database filename; otherwise the configured SQLite file is used. The configured default query is run.
- If `filename` is supplied, `query_or_filename` is interpreted as the SQL query, or the configured default query is used.
- **Output:** query result as a DataFrame.
- **Side effects:** opens and context-manages a SQLite connection; logs query and row count.
- **Errors:** connection, missing-file, SQL, and Pandas errors propagate to the orchestrator.

## `extract_api(endpoint) -> pandas.DataFrame`

Fetches every page declared by the configured API response metadata.

1. Normalize endpoint to have a leading slash and construct query parameters from configured page-number and page-size names.
2. Issue GET requests with configured timeout and retry policy.
3. Retry HTTP 429 and 5xx responses using `Retry-After` if convertible to a float, otherwise configured exponential backoff. Retry request exceptions using exponential backoff.
4. Require each response body to decode to an object containing a list at `api.response_data_key`; every list item must be a mapping.
5. On page 1, require positive integer `total_pages`; accept optional non-negative integer `total_records`.
6. On later pages, validate pagination metadata when present; record-count metadata must remain consistent where it was provided.
7. If a record total was supplied, compare the final accumulated count with it.

- **Input:** endpoint string configured for payments/geolocation or an equivalent endpoint.
- **Output:** DataFrame constructed from accumulated object records. Empty data produces an empty DataFrame if pagination is otherwise valid.
- **Errors:** `ExtractionError` for HTTP failures, retries exhausted, invalid payload/data shape, invalid or inconsistent metadata, and a final count mismatch. JSON decoding errors are not currently explicitly translated to `ExtractionError`.
- **Memory:** all records from every page are accumulated in memory before DataFrame construction.
- **Side effects:** network calls, sleeps between retries, progress/error logs.

## `run_all() -> dict[str, pandas.DataFrame]`

Extracts and returns a mapping with keys `orders`, `reviews`, `items`, `customers`, `sellers`, `products`, `category_translation`, `payments`, and `geolocation`.

- Orders and reviews use configured CSV filenames.
- `items` uses the default SQLite query.
- Customer/seller/product/category reference tables use their configured SQL queries.
- Payments and geolocation use their configured API endpoint names.
- **Failure behavior:** fail-fast; a failing source prevents a complete mapping from being returned.

## Dependency assumptions

CSV definitions currently provide orders/reviews names; table queries and entity names are expected by `run_all`. Changing key names in configuration does not change the output mapping or downstream pipeline contract.
