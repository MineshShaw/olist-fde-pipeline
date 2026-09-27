# Validation function specification

Module: `src/validate.py`

## `DataValidator(logger=None, config=None)`

Creates a validator using the supplied config/logger or repository defaults.

## `validate_orders(df) -> (clean_df, anomalies_df)`

Validates and partitions an orders DataFrame without silently dropping input rows.

### Required columns

The input must contain `order_status` and all five configured timestamp fields: purchase, approval, dispatch, delivery, and estimate. A missing required column raises `ValueError` naming the missing fields. The required schema applies even to non-delivered orders.

### Parsing and classification

- Copy the input; do not mutate caller-owned data.
- Apply `pandas.to_datetime(..., errors="coerce")` to each configured timestamp column.
- A non-empty original timestamp that becomes `NaT` is an invalid timestamp anomaly for any order status.
- For statuses matching configured delivered status after trim/case-fold, every missing timestamp field is a data-quality anomaly, including estimated delivery.
- For other statuses, empty/missing timestamps are allowed unless a supplied value is malformed.
- Compare every pair of present purchase, approval, dispatch, and delivery timestamps. If a later lifecycle event precedes an earlier one, classify the row as anomalous.
- Multiple issues append distinct human-readable reasons to `anomaly_reason`.

### Outputs

- `clean_df`: rows with no detected anomaly; drops internal `is_valid` and `anomaly_reason` columns. Timestamp columns are parsed datetimes.
- `anomalies_df`: invalid rows including `is_valid=False` and the concatenated `anomaly_reason`; timestamp columns are parsed datetimes.
- The two frames partition the source rows without intentional deduplication or removal.

### Errors and side effects

Raises `ValueError` for missing required columns. Logs start/end counts. Unknown order statuses are treated as non-delivered for missing-timestamp rules; the validator does not reject status values or validate other tables.

## `run_all(raw_data) -> dict[str, dict[str, pandas.DataFrame]]`

Validates the `orders` entry if present. Each input dataset is represented as:

```python
{
    "dataset_name": {
        "clean": pandas.DataFrame,
        "anomalies": pandas.DataFrame,
    }
}
```

For non-order datasets, `clean` is the original DataFrame reference and `anomalies` is an empty DataFrame; no validation is performed. If orders is missing, the validator logs a warning and passes through the other datasets. The pipeline itself expects an `orders` result and will fail if absent.
