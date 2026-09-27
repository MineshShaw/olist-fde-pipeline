import pandas as pd
import pytest

from src.transform import build_order_context, build_seller_order_facts


@pytest.fixture
def source_frames():
    orders = pd.DataFrame(
        {
            "order_id": ["O1", "O2"],
            "customer_id": ["C1", "C2"],
            "order_status": ["delivered", "delivered"],
            "order_delivered_customer_date": pd.to_datetime(
                ["2024-01-05", "2024-01-12"]
            ),
            "order_estimated_delivery_date": pd.to_datetime(
                ["2024-01-04", "2024-01-10"]
            ),
        }
    )
    items = pd.DataFrame(
        {
            "order_id": ["O1", "O1", "O2"],
            "order_item_id": [1, 2, 1],
            "seller_id": ["S1", "S2", "S1"],
            "price": [10.0, 20.0, 15.0],
            "freight_value": [2.0, 3.0, 4.0],
        }
    )
    payments = pd.DataFrame(
        {
            "order_id": ["O1", "O1", "O2"],
            "payment_sequential": [1, 2, 1],
            "payment_value": [15.0, 20.0, 19.0],
        }
    )
    customers = pd.DataFrame(
        {
            "customer_id": ["C1", "C2"],
            "customer_zip_code_prefix": [1234, 98765],
            "customer_state": ["SP", "RJ"],
        }
    )
    geo = pd.DataFrame(
        {
            "geolocation_zip_code_prefix": ["01234", "01234", "98765"],
            "geolocation_lat": [-23.5, -23.7, -22.9],
            "geolocation_lng": [-46.6, -46.8, -43.2],
            "geolocation_state": ["SP", "SP", "RJ"],
        }
    )
    return orders, items, payments, customers, geo


def test_order_context_aggregates_one_to_many_sources_before_join(source_frames):
    orders, items, payments, customers, geo = source_frames

    enriched = build_order_context(orders, items, payments, customers, geo)

    assert len(enriched) == len(orders)
    assert enriched["order_id"].is_unique
    o1 = enriched.set_index("order_id").loc["O1"]
    assert o1["item_count"] == 2
    assert o1["item_revenue"] == 30
    assert o1["freight_total"] == 5
    assert o1["seller_count"] == 2
    assert o1["payment_count"] == 2
    assert o1["payment_total"] == 35
    assert o1["postal_prefix"] == "01234"
    assert o1["geo_latitude"] == pytest.approx(-23.6)
    assert o1["geo_longitude"] == pytest.approx(-46.7)


def test_order_context_rejects_duplicate_order_grain(source_frames):
    orders, items, payments, customers, geo = source_frames
    duplicated = pd.concat([orders, orders.iloc[[0]]], ignore_index=True)

    with pytest.raises(ValueError, match="one row per order_id"):
        build_order_context(duplicated, items, payments, customers, geo)


def test_seller_facts_count_order_seller_pairs_without_changing_order_facts(source_frames):
    orders, items, _, _, _ = source_frames
    event = orders.assign(
        dispatch_days=[1.0, 3.0],
        is_late=[True, True],
        is_comparable=[True, True],
    )

    result = build_seller_order_facts(event, items)
    seller1 = result.set_index("seller_id").loc["S1"]
    seller2 = result.set_index("seller_id").loc["S2"]

    assert seller1["seller_order_count"] == 2
    assert seller1["delivered_order_count"] == 2
    assert seller1["late_order_count"] == 2
    assert seller1["average_dispatch_days"] == 2
    assert seller2["seller_order_count"] == 1
    assert seller2["late_delivery_rate_pct"] == 100
