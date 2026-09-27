import pytest
import pandas as pd
from src.model import DataModeler

@pytest.fixture
def modeler():
    return DataModeler()

@pytest.fixture
def mock_clean_orders():
    return pd.DataFrame({
        "order_id": ["O1", "O2"],
        "order_purchase_timestamp": ["2023-01-01 10:00:00", "2023-01-01 10:00:00"],
        "order_approved_at": ["2023-01-01 12:00:00", "2023-01-02 10:00:00"],
        "order_delivered_carrier_date": ["2023-01-02 12:00:00", "2023-01-04 10:00:00"],
        "order_delivered_customer_date": ["2023-01-05 12:00:00", "2023-01-10 10:00:00"],
        "order_estimated_delivery_date": ["2023-01-08 10:00:00", "2023-01-08 10:00:00"] # O1 is On-Time, O2 is Late
    })

def test_process_event_model_durations_and_flags(modeler, mock_clean_orders):
    df = modeler.process_event_model(mock_clean_orders)
    
    # Check flags
    assert df.loc[df["order_id"] == "O1", "is_late"].iloc[0] == False
    assert df.loc[df["order_id"] == "O2", "is_late"].iloc[0] == True
    
    # Check math (O1 approval should be 2 hours = ~0.0833 days)
    approval_days = df.loc[df["order_id"] == "O1", "approval_days"].iloc[0]
    assert round(approval_days, 4) == 0.0833
    
    # Check transit time (O2 transit should be 6 days)
    transit_days = df.loc[df["order_id"] == "O2", "transit_days"].iloc[0]
    assert transit_days == 6.0

def test_generate_kpi_dashboard(modeler, mock_clean_orders):
    event_model = modeler.process_event_model(mock_clean_orders)
    dashboard = modeler.generate_kpi_dashboard(event_model)
    
    # Out of 2 orders, 1 is late (50%)
    pct_late = dashboard[dashboard["Metric"] == "Percentage Late (%)"]["Value"].iloc[0]
    assert pct_late == 50.0
    
    # The late order (O2) took 6 days in transit
    avg_transit = dashboard[dashboard["Metric"] == "Avg Carrier Transit Time (Late Orders) [Days]"]["Value"].iloc[0]
    assert avg_transit == 6.0


def test_generate_kpi_dashboard_excludes_orders_without_delivery_dates(modeler, mock_clean_orders):
    incomplete_order = mock_clean_orders.iloc[[0]].copy()
    incomplete_order["order_id"] = "O3"
    incomplete_order["order_delivered_customer_date"] = None
    incomplete_order["order_estimated_delivery_date"] = None
    event_model = modeler.process_event_model(
        pd.concat([mock_clean_orders, incomplete_order], ignore_index=True)
    )

    dashboard = modeler.generate_kpi_dashboard(event_model)
    total_orders = dashboard.loc[
        dashboard["Metric"] == "Total Orders Analyzed", "Value"
    ].iloc[0]
    percentage_late = dashboard.loc[
        dashboard["Metric"] == "Percentage Late (%)", "Value"
    ].iloc[0]

    assert total_orders == 2
    assert percentage_late == 50.0


def test_generate_kpi_dashboard_counts_only_comparable_delivered_orders(modeler):
    orders = pd.DataFrame(
        {
            "order_id": ["O1", "O2", "O3"],
            "order_status": ["delivered", "delivered", "shipped"],
            "order_purchase_timestamp": ["2023-01-01"] * 3,
            "order_approved_at": ["2023-01-01"] * 3,
            "order_delivered_carrier_date": ["2023-01-02"] * 3,
            "order_delivered_customer_date": ["2023-01-05", "2023-01-06", "2023-01-07"],
            "order_estimated_delivery_date": ["2023-01-04", None, "2023-01-10"],
        }
    )
    event_model = modeler.process_event_model(orders)

    dashboard = modeler.generate_kpi_dashboard(
        event_model,
        excluded_delivered_orders=2,
    )
    values = dict(zip(dashboard["Metric"], dashboard["Value"]))

    assert values["Total Orders Analyzed"] == 1
    assert values["Total Late Deliveries"] == 1
    assert values["Percentage Late (%)"] == 100.0
    assert values["Delivered Orders Excluded from KPI"] == 3