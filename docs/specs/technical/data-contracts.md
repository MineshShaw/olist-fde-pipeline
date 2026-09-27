# Technical specification: data contracts and KPI semantics

## Source contracts

### Orders CSV

`sources.csv.orders` resolves beneath `paths.raw_data` unless absolute. It must contain `order_status` plus the configured purchase, approval, dispatch, delivery, and estimate timestamp columns. Defaults are:

| Semantic key | Default column |
| --- | --- |
| purchase | `order_purchase_timestamp` |
| approval | `order_approved_at` |
| dispatch | `order_delivered_carrier_date` |
| delivery | `order_delivered_customer_date` |
| estimate | `order_estimated_delivery_date` |

`order_status` is compared case-insensitively after trimming against configured `validation.delivered_status` (default `delivered`).

### Reviews CSV

Loaded from configured `sources.csv.reviews`; it is returned by extraction but passes through validation and is not currently joined into the event model or KPI output.

### SQLite

`paths.sqlite_file` is joined to `paths.raw_data` unless absolute. `db.default_query` supplies the `items` dataset. `db.queries` supplies customer, seller, product, and category-translation DataFrames. Query results pass through validation and are not currently joined into pipeline KPI artifacts.

In the operational transform, order items and payments are aggregated by `order_id` before joining to order records. Customer dimension joins by `customer_id`; customer postal prefixes are normalized and joined to geolocation summaries. Seller accountability is a separate seller/order fact; product and category translation data are extracted but not currently used in the order context.

### REST API

The endpoint response must be a JSON object with:

- Configured data key (default `data`) whose value is a list of JSON objects.
- Configured page-total key (default `total_pages`) on page 1, with positive integer value.
- Optional configured record-total key (default `total_records`) with non-negative integer value if present.

Later-page page totals, when supplied, must be positive and match page 1. Any later page record total must be a non-negative integer and must remain consistent with earlier supplied totals. Final received count must match the last declared/supplied record count. Missing `total_records` is accepted; missing `total_pages` is not.

The extractor constructs the URL as configured base URL + endpoint + configured page/page-size query parameters. Retry behavior covers HTTP 429, HTTP 5xx, and request exceptions. HTTP error status that is not retried, retry exhaustion, malformed payload shape, pagination inconsistency, and final record-count mismatch abort extraction.

## Validation contract

| Input condition | Classification |
| --- | --- |
| Required column absent from orders frame | Raise `ValueError`; no row-level partition returned. |
| Non-empty timestamp cannot be parsed | Anomaly on that row, regardless of status. |
| Missing timestamp on a delivered row | Anomaly on that row, for each configured timestamp including estimate. |
| Missing timestamp on non-delivered row | Allowed for that field; reflects a not-yet-reached lifecycle event. |
| Any present delivery/dispatch/approval occurs before a prior lifecycle timestamp | Anomaly. Every pair among purchase, approval, dispatch, delivery is checked. |
| Otherwise | Row appears in clean frame. |

Timestamp parser uses Pandas coercion; it does not apply timezone conversion. Anomaly reason text is user-facing diagnostic detail and can contain multiple semicolon-separated reasons.

## Event model contract

The event model includes all clean source-order fields plus:

- `is_late`: delivery > estimate.
- `is_comparable`: order has configured delivered status and actual plus estimated delivery timestamps.
- `approval_days`: order-approved timestamp minus purchase in fractional days; not payment authorization.
- `dispatch_days`: carrier handoff minus approval in fractional days.
- `transit_days`: customer delivery minus carrier handoff in fractional days.

Configured `model.seconds_per_day` is the divisor for the duration calculations. Modeling parses timestamp columns again and does not run validation rules itself.

## Enriched order context

`clean_event_model.csv` remains order-grain (one row per clean order). It adds:

| Field | Construction |
| --- | --- |
| `item_count`, `item_revenue`, `freight_total`, `seller_count` | Aggregate order_items by order ID before join. |
| `payment_total`, `payment_count` | Aggregate payment records by order ID before join. |
| customer state/postal prefix | Many-to-one join on customer ID. |
| `geo_latitude`, `geo_longitude`, `geo_state`, `geolocation_records` | Postal-prefix summary joined on normalized five-character prefix; coordinates are arithmetic means. |

Orders missing source matches remain in the event model with null context. Order-level KPI counts do not expand with line-item/payment cardinality.

## Seller accountability

`seller_accountability.csv` has one row per seller with associated order-count, comparable delivered count, late count/rate, all-associated average dispatch duration, late-comparable average dispatch duration, and seller city/state where available. It derives from unique order/seller pairs.

The association fact intentionally duplicates multi-seller orders across participating sellers; seller rates/volumes are not exclusive allocations and should not be summed to obtain unique order counts. No carrier identity is available for carrier accountability.

## KPI artifact schema

The KPI artifact is a two-column table (`Metric`, `Value`) with the following expected rows:

| Metric | Semantics |
| --- | --- |
| `Total Orders Analyzed` | Valid, delivered rows with non-null actual and estimated delivery timestamps. |
| `Total Late Deliveries` | Denominator rows whose `is_late` is true. |
| `Percentage Late (%)` | Late count ÷ denominator × 100, rounded to 2 decimals; 0 if denominator is zero. |
| `Delivered Orders Excluded from KPI` | Delivered anomaly rows passed by pipeline plus delivered rows in event model that are invalid or incomparable. |
| `Delivered Orders Evaluated` | Valid delivered event-model rows plus delivered anomalies. |
| `Comparable Delivery Coverage (%)` | Comparable denominator divided by evaluated delivered population. |
| All-comparable stage duration rows | Mean each stage across all valid comparable delivered orders. |
| Late-only stage duration rows | Mean each stage across late valid comparable delivered orders. |
| `Avg Seller Dispatch Time (Late Orders) [Days]` | Mean dispatch duration for KPI-late rows. |
| `Avg Carrier Transit Time (Late Orders) [Days]` | Mean transit duration for KPI-late rows. |

Stage means ignore null durations according to Pandas. The output should not be interpreted as causal attribution; in particular there is no carrier ID in the pipeline KPI relation.

## Output contracts

Each run partition contains:

- `logs/pipeline.log`.
- `data/kpi_dashboard.csv`.
- `data/clean_event_model.csv`.
- `data/seller_accountability.csv`.
- Optional `data/flagged_anomalies.csv`.
- Optional configured PNG artifacts under `visualizations/`.
- `_SUCCESS.json` marking a complete published partition; dashboard ignores partitions without a matching successful manifest.

The anomaly output retains validation tracking columns. Failed staging attempts carry `_RUN_STATUS.json` and are not dashboard-visible; all-anomaly attempts persist the anomaly CSV in the attempt stage. The clean event model excludes validation tracking columns but adds event-model/context columns. The dashboard expects KPI columns `Metric` and `Value`; the data tab expects `order_id` for search.
