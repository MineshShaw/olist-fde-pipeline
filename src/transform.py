"""Build order-grain context and seller-order accountability facts."""

import pandas as pd


def _require_columns(frame: pd.DataFrame, dataset: str, columns: set[str]) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise ValueError(
            f"{dataset} data is missing required columns: {', '.join(sorted(missing))}"
        )


def _postal_prefix(values: pd.Series) -> pd.Series:
    return (
        values.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(5)
    )


def build_order_context(
    orders: pd.DataFrame,
    items: pd.DataFrame,
    payments: pd.DataFrame,
    customers: pd.DataFrame,
    geolocation: pd.DataFrame,
) -> pd.DataFrame:
    """Enrich orders without changing their one-row-per-order grain."""
    _require_columns(orders, "orders", {"order_id", "customer_id"})
    _require_columns(
        items,
        "items",
        {"order_id", "order_item_id", "seller_id", "price", "freight_value"},
    )
    _require_columns(
        payments,
        "payments",
        {"order_id", "payment_sequential", "payment_value"},
    )
    _require_columns(
        customers,
        "customers",
        {"customer_id", "customer_zip_code_prefix", "customer_state"},
    )
    _require_columns(
        geolocation,
        "geolocation",
        {
            "geolocation_zip_code_prefix",
            "geolocation_lat",
            "geolocation_lng",
            "geolocation_state",
        },
    )
    if orders["order_id"].duplicated().any():
        raise ValueError("orders must contain one row per order_id")

    item_summary = items.groupby("order_id", as_index=False).agg(
        item_count=("order_item_id", "count"),
        item_revenue=("price", "sum"),
        freight_total=("freight_value", "sum"),
        seller_count=("seller_id", "nunique"),
    )
    payment_summary = payments.groupby("order_id", as_index=False).agg(
        payment_total=("payment_value", "sum"),
        payment_count=("payment_sequential", "count"),
    )

    customer_lookup = customers[
        ["customer_id", "customer_zip_code_prefix", "customer_state"]
    ].copy()
    customer_lookup["postal_prefix"] = _postal_prefix(
        customer_lookup["customer_zip_code_prefix"]
    )
    if customer_lookup["customer_id"].duplicated().any():
        raise ValueError("customers must contain at most one row per customer_id")

    geo = geolocation.copy()
    geo["postal_prefix"] = _postal_prefix(geo["geolocation_zip_code_prefix"])
    geo_summary = (
        geo.groupby("postal_prefix", as_index=False)
        .agg(
            geo_latitude=("geolocation_lat", "mean"),
            geo_longitude=("geolocation_lng", "mean"),
            geo_state=("geolocation_state", "min"),
            geolocation_records=("geolocation_zip_code_prefix", "count"),
        )
    )

    enriched = (
        orders.merge(
            item_summary,
            on="order_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            payment_summary,
            on="order_id",
            how="left",
            validate="one_to_one",
        )
        .merge(
            customer_lookup,
            on="customer_id",
            how="left",
            validate="many_to_one",
        )
        .merge(geo_summary, on="postal_prefix", how="left", validate="many_to_one")
    )
    return enriched


def build_seller_order_facts(
    event_model: pd.DataFrame,
    items: pd.DataFrame,
    delivered_status: str = "delivered",
    sellers: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return one row per order/seller and seller-level operating metrics."""
    _require_columns(event_model, "event model", {"order_id", "order_status"})
    _require_columns(items, "items", {"order_id", "seller_id"})

    relationships = items[["order_id", "seller_id"]].drop_duplicates()
    order_facts = event_model.copy()
    status = (
        order_facts["order_status"]
        .astype("string")
        .str.strip()
        .str.casefold()
    )
    order_facts["is_delivered"] = status.eq(delivered_status.casefold()).fillna(False)
    if "is_late" not in order_facts:
        order_facts["is_late"] = False
    if "is_comparable" not in order_facts:
        order_facts["is_comparable"] = (
            order_facts["is_delivered"]
            & order_facts["order_delivered_customer_date"].notna()
            & order_facts["order_estimated_delivery_date"].notna()
        )

    seller_orders = relationships.merge(
        order_facts,
        on="order_id",
        how="inner",
        validate="many_to_one",
    )
    seller_orders["is_late_comparable"] = (
        seller_orders["is_comparable"]
        & seller_orders["is_late"].fillna(False).astype(bool)
    )
    seller_summary = seller_orders.groupby("seller_id", as_index=False).agg(
        seller_order_count=("order_id", "nunique"),
        delivered_order_count=("is_comparable", "sum"),
        late_order_count=("is_late_comparable", "sum"),
        average_dispatch_days=("dispatch_days", "mean"),
        average_late_dispatch_days=(
            "dispatch_days",
            lambda values: values[seller_orders.loc[values.index, "is_late_comparable"]].mean(),
        ),
    )
    seller_summary["late_delivery_rate_pct"] = (
        seller_summary["late_order_count"]
        .div(seller_summary["delivered_order_count"].where(
            seller_summary["delivered_order_count"].ne(0)
        ))
        .mul(100)
    )
    if sellers is not None:
        _require_columns(sellers, "sellers", {"seller_id"})
        dimensions = [
            column
            for column in ("seller_id", "seller_state", "seller_city")
            if column in sellers.columns
        ]
        seller_dimensions = sellers[dimensions].drop_duplicates()
        if seller_dimensions["seller_id"].duplicated().any():
            raise ValueError("sellers must contain at most one row per seller_id")
        seller_summary = seller_summary.merge(
            seller_dimensions,
            on="seller_id",
            how="left",
            validate="one_to_one",
        )
    return seller_summary.sort_values(
        ["average_dispatch_days", "seller_order_count"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)
