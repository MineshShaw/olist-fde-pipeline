import pytest
import pandas as pd
from src.validate import DataValidator

@pytest.fixture
def validator():
    return DataValidator()

@pytest.fixture
def sample_orders():
    """
    Mock dataset containing both valid records and intentional business-rule violations.
    """
    return pd.DataFrame({
        "order_id": ["O1", "O2", "O3", "O4"],
        "order_status": ["delivered", "delivered", "shipped", "delivered"],
        "order_purchase_timestamp": [
            "2023-01-01 10:00:00",  # O1: Valid
            "2023-01-05 10:00:00",  # O2: Invalid (Delivered before purchase)
            "2023-01-10 10:00:00",  # O3: Valid (Shipped, no delivery date yet)
            "2023-01-15 10:00:00"   # O4: Invalid (Delivered but missing date)
        ],
        "order_approved_at": [
            "2023-01-01 11:00:00",
            "2023-01-05 11:00:00",
            None,
            "2023-01-15 11:00:00",
        ],
        "order_delivered_carrier_date": [
            "2023-01-02 10:00:00",
            "2023-01-06 10:00:00",
            None,
            "2023-01-16 10:00:00",
        ],
        "order_delivered_customer_date": [
            "2023-01-04 10:00:00",  # O1
            "2023-01-02 10:00:00",  # O2 (Time travel)
            None,                   # O3
            None                    # O4 (Missing transition)
        ],
        "order_estimated_delivery_date": [
            "2023-01-10 10:00:00",
            "2023-01-10 10:00:00",
            "2023-01-20 10:00:00",
            "2023-01-20 10:00:00"
        ]
    })

def test_validate_orders_separates_clean_and_anomalies(validator, sample_orders):
    clean_df, anomalies_df = validator.validate_orders(sample_orders)
    
    # Check that records O1 and O3 passed cleanly
    assert len(clean_df) == 2
    assert set(clean_df["order_id"]) == {"O1", "O3"}
    assert "is_valid" not in clean_df.columns  # Clean df shouldn't have tracking metadata
    
    # Check that records O2 and O4 were flagged as anomalies
    assert len(anomalies_df) == 2
    assert set(anomalies_df["order_id"]) == {"O2", "O4"}
    
def test_validate_orders_flags_correct_reasons(validator, sample_orders):
    _, anomalies_df = validator.validate_orders(sample_orders)
    
    # Validate Rule A (Time travel)
    o2_anomaly = anomalies_df[anomalies_df["order_id"] == "O2"].iloc[0]
    assert "Delivered before purchase date" in o2_anomaly["anomaly_reason"]
    
    # Validate Rule B (Missing status transition)
    o4_anomaly = anomalies_df[anomalies_df["order_id"] == "O4"].iloc[0]
    assert "missing delivery date" in o4_anomaly["anomaly_reason"]


def test_validate_orders_flags_missing_delivered_stages(validator, sample_orders):
    sample_orders.loc[
        sample_orders["order_id"] == "O1", "order_approved_at"
    ] = None
    _, anomalies = validator.validate_orders(sample_orders)

    o1 = anomalies[anomalies["order_id"] == "O1"].iloc[0]
    assert "missing approval timestamp" in o1["anomaly_reason"]


def test_validate_orders_flags_malformed_dates_for_any_status(validator, sample_orders):
    sample_orders.loc[
        sample_orders["order_id"] == "O3", "order_approved_at"
    ] = "not-a-timestamp"
    _, anomalies = validator.validate_orders(sample_orders)

    o3 = anomalies[anomalies["order_id"] == "O3"].iloc[0]
    assert "Invalid approval timestamp" in o3["anomaly_reason"]


def test_validate_orders_flags_stage_order_reversals(validator, sample_orders):
    sample_orders.loc[
        sample_orders["order_id"] == "O1", "order_delivered_carrier_date"
    ] = "2022-12-31 10:00:00"
    _, anomalies = validator.validate_orders(sample_orders)

    o1 = anomalies[anomalies["order_id"] == "O1"].iloc[0]
    assert "Dispatch timestamp before purchase timestamp" in o1["anomaly_reason"]


def test_validate_orders_requires_timestamp_schema(validator, sample_orders):
    sample_orders = sample_orders.drop(columns=["order_approved_at"])

    with pytest.raises(ValueError, match="order_approved_at"):
        validator.validate_orders(sample_orders)


def test_run_all_structure(validator, sample_orders):
    raw_data = {
        "orders": sample_orders,
        "payments": pd.DataFrame({"payment_id": ["P1"]})
    }
    
    result = validator.run_all(raw_data)
    
    assert "orders" in result
    assert "clean" in result["orders"]
    assert "anomalies" in result["orders"]
    
    assert "payments" in result
    assert len(result["payments"]["clean"]) == 1
    assert len(result["payments"]["anomalies"]) == 0