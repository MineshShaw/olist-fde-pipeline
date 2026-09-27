# Transformation function specification

Module: `src/transform.py`

## `_require_columns(frame, dataset, columns) -> None`

Internal schema guard. Raises `ValueError` naming missing input fields; does not mutate the DataFrame.

## `_postal_prefix(values) -> pandas.Series`

Converts values to Pandas nullable strings, trims surrounding whitespace, removes a trailing `.0` from numeric-looking values, and left-pads to five characters. This keeps zeros in Brazilian postal prefixes when an upstream parser represented them as integers/floats.

## `build_order_context(orders, items, payments, customers, geolocation) -> pandas.DataFrame`

Constructs one enriched output row per order. It requires:

- Orders: `order_id`, `customer_id`, unique order IDs.
- Items: `order_id`, `order_item_id`, `seller_id`, `price`, `freight_value`.
- Payments: `order_id`, `payment_sequential`, `payment_value`.
- Customers: `customer_id`, `customer_zip_code_prefix`, `customer_state`, unique customer IDs.
- Geolocation: postal prefix, latitude, longitude, and state columns.

Before joining:

- Items aggregate by order to item count, price sum, freight sum, and distinct seller count.
- Payments aggregate by order to payment value sum and payment count.
- Geolocation normalizes postal prefix and aggregates observations by prefix: mean latitude/longitude, lexicographically minimum state as deterministic state representative, and observation count.
- Customer zip prefixes are normalized without losing leading zeroes.

Joins are left joins with Pandas `validate=` cardinality checks: order-to-item summary one-to-one; order-to-payment summary one-to-one; customer many-to-one; geolocation-prefix many-to-one. The resulting order cardinality must remain equal to input Orders. Orders with no items/payment/customer/geolocation retain null aggregate/dimension values.

### Interpretation

`item_revenue` is sum of item prices (not necessarily final order revenue or captured payments). `freight_total` is summed item freight values. `payment_total` is payment-record sum. These may differ for legitimate business reasons and are not reconciled or treated as authorization data. Geolocation coordinate means reduce multiple points per prefix; they are approximate lookup coordinates and not a measured route distance.

## `build_seller_order_facts(event_model, items, delivered_status="delivered", sellers=None) -> pandas.DataFrame`

Creates a separate seller-grain summary. Requires order ID/status on the event model and order ID/seller ID on Items. It drops duplicate order/seller relationships before a many-to-one join to the event model.

If `is_comparable` is absent, it derives it from delivered status and non-null actual/estimated delivery fields. If `is_late` is absent, defaults it to false. In the production path, both flags come from the modeler.

Per-seller outputs:

- `seller_order_count`: distinct orders with the seller, regardless of delivery status.
- `delivered_order_count`: comparable delivered order/seller associations.
- `late_order_count`: comparable late order/seller associations.
- `average_dispatch_days`: mean available dispatch durations across seller-associated orders.
- `average_late_dispatch_days`: mean dispatch duration for late comparable associations.
- `late_delivery_rate_pct`: late associations divided by comparable delivered associations × 100; null if the denominator is zero.
- Optional seller city/state dimensions when supplied; production pipeline supplies seller reference data.

### Attribution and errors

One order involving two sellers contributes to both seller rows. Counts do not sum to unique order counts across sellers; this is seller involvement, not exclusive causality. Duplicate order IDs in event model cause merge validation failure. Duplicate seller dimension IDs cause `ValueError`. Files are persisted by pipeline, not these pure transformation functions.
