# Local API fixture function specification

Module: `data/api/main.py`

## Module constants and startup loading

`API_DIR` is the directory containing this module. At import, `payments.json` and `geolocation.json` are read and normalized. A missing or invalid fixture prevents module import; the service does not silently return an empty source.

`RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` are read from `OLIST_API_RATE_LIMIT` and `OLIST_API_RATE_WINDOW` at module import. Invalid numeric environment values raise during import.

## `load_json_as_list(filename, key_field) -> list[dict]`

Reads one JSON fixture from `API_DIR / filename`.

- List root: every item must be a JSON object; items are copied into dictionaries.
- Mapping root: list-valued entries expand into one row per object, while object-valued entries become one row. The mapping key is written into `key_field` and overrides any such field already present in the row.
- Scalar root, non-object list item, scalar mapping value, malformed JSON, or file error raises a clear `ValueError`/`RuntimeError`.

## `enforce_rate_limit(request) -> None`

Maintains an in-memory per-client sliding request window under a thread lock. Requests at or above the configured limit inside the configured interval raise FastAPI `HTTPException(429)` with a `Retry-After` header. The limit state is process-local and resets on restart.

## `paginate_data(data_list, page, page_size) -> dict`

Computes `total_pages` as ceiling(total records / page size), with empty data still reporting one page. For nonempty datasets, a page less than one or beyond the last page raises `HTTPException(404)`. Returns:

```json
{
  "data": [],
  "total_pages": 1,
  "current_page": 1,
  "total_records": 0
}
```

The endpoint parameters constrain page and page size to positive integers. Direct calls to `paginate_data` do not independently guard against page size zero.

## Endpoint functions

- `get_payments(request, page=1, page_size=500)`: rate-limit request, paginate fixture `payments_data`.
- `get_geolocation(request, page=1, page_size=500)`: rate-limit request, paginate fixture `geo_data`.

Both are GET routes with JSON response metadata required by the pipeline extractor. The fixture is intended for local development and tests, not production hosting or authentication.
