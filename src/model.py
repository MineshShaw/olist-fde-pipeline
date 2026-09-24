import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DataModeler:
    """
    Class 7 & 8 Modeling Layer: Transforms clean operational data into 
    event-based chronologies and business KPIs.
    """
    def process_event_model(self, clean_orders: pd.DataFrame) -> pd.DataFrame:
        """Reconstructs the order workflow and calculates stage durations."""
        logger.info("Processing event model and calculating stage durations...")
        df = clean_orders.copy()
        
        # Ensure all timestamps are datetime objects
        cols = [
            'order_purchase_timestamp', 'order_approved_at', 
            'order_delivered_carrier_date', 'order_delivered_customer_date', 
            'order_estimated_delivery_date'
        ]
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                
        # Primary KPI Flag: Was it delivered past the estimated date?
        df['is_late'] = df['order_delivered_customer_date'] > df['order_estimated_delivery_date']
        
        # Duration Math (in days)
        if 'order_approved_at' in df.columns and 'order_purchase_timestamp' in df.columns:
            df['approval_days'] = (df['order_approved_at'] - df['order_purchase_timestamp']).dt.total_seconds() / 86400.0
            
        if 'order_delivered_carrier_date' in df.columns and 'order_approved_at' in df.columns:
            df['dispatch_days'] = (df['order_delivered_carrier_date'] - df['order_approved_at']).dt.total_seconds() / 86400.0
            
        if 'order_delivered_customer_date' in df.columns and 'order_delivered_carrier_date' in df.columns:
            df['transit_days'] = (df['order_delivered_customer_date'] - df['order_delivered_carrier_date']).dt.total_seconds() / 86400.0
            
        return df

    def generate_kpi_dashboard(self, event_model: pd.DataFrame) -> pd.DataFrame:
        """Aggregates the event model into the final business KPIs."""
        logger.info("Generating KPI dashboard...")
        
        total_orders = len(event_model)
        late_orders = event_model['is_late'].sum()
        pct_late = (late_orders / total_orders) * 100 if total_orders > 0 else 0
        
        late_df = event_model[event_model['is_late']]
        
        # Isolating where the delay happens for late orders
        avg_approval = late_df['approval_days'].mean() if 'approval_days' in late_df else 0
        avg_dispatch = late_df['dispatch_days'].mean() if 'dispatch_days' in late_df else 0
        avg_transit = late_df['transit_days'].mean() if 'transit_days' in late_df else 0
        
        return pd.DataFrame({
            "Metric": [
                "Total Orders Analyzed",
                "Total Late Deliveries",
                "Percentage Late (%)",
                "Avg Approval Time (Late Orders) [Days]",
                "Avg Seller Dispatch Time (Late Orders) [Days]",
                "Avg Carrier Transit Time (Late Orders) [Days]"
            ],
            "Value": [
                total_orders,
                late_orders,
                round(pct_late, 2),
                round(avg_approval, 2),
                round(avg_dispatch, 2),
                round(avg_transit, 2)
            ]
        })