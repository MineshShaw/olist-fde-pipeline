# Modeling function specification

Module: `src/model.py`

## `DataModeler(logger=None, config=None)`

Creates a modeler bound to configuration timestamp names and seconds-per-day conversion.

## `process_event_model(clean_orders) -> pandas.DataFrame`

Copies the supplied order DataFrame, parses each configured timestamp column if present, and derives the late flag and stage durations.

| Output field | Calculation |
| --- | --- |
| `is_late` | Actual delivery timestamp > estimated delivery timestamp; null comparison yields a missing/falsey result according to Pandas semantics. |
| `is_comparable` | Normalized delivered status and both actual/estimated delivery timestamps are present. |
| `approval_days` | Order approved timestamp − purchase timestamp, in days. This is order approval latency, not payment authorization latency. |
| `dispatch_days` | (carrier handoff − approval) total seconds ÷ configured seconds/day. |
| `transit_days` | (customer delivery − carrier handoff) total seconds ÷ configured seconds/day. |

Duration output is created only when both source timestamp columns are present. The function does not enforce chronology; that is the validator's responsibility. Negative durations should not occur on validated data because reversed event order is rejected. If a timestamp is absent, `is_late` currently indexes the configured delivery/estimate fields and may raise `KeyError`; pipeline inputs are expected to have the required schema established by validation.

## `generate_kpi_dashboard(event_model, excluded_delivered_orders=0) -> pandas.DataFrame`

Returns a two-column `Metric`, `Value` DataFrame used by pipeline persistence and dashboard rendering.

### Denominator

- When `order_status` exists, only rows whose normalized status matches configured delivered status are candidates.
- Otherwise, delivery timestamp non-null is used as a compatibility fallback.
- If `is_valid` exists, it must be true.
- Actual delivery and estimate timestamps must both be non-null.
- `Total Orders Analyzed` equals the resulting comparable row count.
- `Delivered Orders Excluded from KPI` is the passed count of delivered anomalies plus delivered rows within `event_model` that fail comparability/validity.
- `Delivered Orders Evaluated` is the delivered clean-row count plus the delivered anomaly count.
- `Comparable Delivery Coverage (%)` is comparable rows divided by evaluated delivered rows, or zero when none were evaluated.
- The pipeline passes delivered-anomaly count explicitly because anomaly rows are not included in the clean event model.

### Metrics

| Metric label | Value |
| --- | --- |
| `Total Orders Analyzed` | Comparable denominator count. |
| `Total Late Deliveries` | Comparable rows where `is_late` is true. |
| `Percentage Late (%)` | Late count / denominator × 100, rounded to 2 decimals; zero when denominator is zero. |
| `Delivered Orders Excluded from KPI` | Explicit delivered anomaly count plus excluded delivered rows in event model. |
| `Delivered Orders Evaluated` | Delivered clean rows plus delivered anomaly rows. |
| `Comparable Delivery Coverage (%)` | Comparable denominator / evaluated delivered population × 100. |
| `Avg Order Approval Time (All Comparable Delivered) [Days]` | Mean purchase-to-approved duration across all denominator rows. |
| `Avg Seller Dispatch Time (All Comparable Delivered) [Days]` | Mean approval-to-handoff duration across all denominator rows. |
| `Avg Carrier Transit Time (All Comparable Delivered) [Days]` | Mean handoff-to-customer duration across all denominator rows. |
| `Avg Order Approval Time (Late Orders) [Days]` | Mean order-approval duration across KPI-late rows. |
| `Avg Seller Dispatch Time (Late Orders) [Days]` | Mean dispatch duration across KPI-late rows, or zero if column unavailable. |
| `Avg Carrier Transit Time (Late Orders) [Days]` | Mean transit duration across KPI-late rows, or zero if column unavailable. |

Duration means ignore null values per Pandas. All-comparable stage metrics are descriptive averages over the KPI denominator; late-only metrics use the late subset. Missing `is_late`/delivery/estimate fields may raise a Pandas/KeyError failure rather than returning a success-shaped result.
