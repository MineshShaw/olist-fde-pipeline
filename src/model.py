import pandas as pd
from typing import Optional
from src.logger import PipelineLogger, default_logger

class DataModeler:
    """
    Class 7 & 8 Modeling Layer: Transforms clean operational data into 
    event-based chronologies and business KPIs.
    """
    def __init__(self, logger: Optional[PipelineLogger] = None):
        self.logger = logger or default_logger()
        self.logger.info("Initialized data modeler.")

    def process_event_model(self, clean_orders: pd.DataFrame) -> pd.DataFrame:
        """Reconstructs the order workflow and calculates stage durations."""
        self.logger.info("Processing event model and calculating stage durations.")
        self.logger.info("Copying clean orders dataframe for modeling.")
        df = clean_orders.copy()
        
        # Ensure all timestamps are datetime objects
        cols = [
            'order_purchase_timestamp', 'order_approved_at', 
            'order_delivered_carrier_date', 'order_delivered_customer_date', 
            'order_estimated_delivery_date'
        ]
        self.logger.info("Starting loop over event timestamp columns.")
        for col in cols:
            if col in df.columns:
                self.logger.info(f"Changing data type of event column to datetime: {col}.")
                df[col] = pd.to_datetime(df[col], errors='coerce')
            else:
                self.logger.info(f"Skipping missing event timestamp column: {col}.")
                
        # Primary KPI Flag: Was it delivered past the estimated date?
        self.logger.info("Calculating late delivery flag.")
        df['is_late'] = df['order_delivered_customer_date'] > df['order_estimated_delivery_date']
        
        # Duration Math (in days)
        if 'order_approved_at' in df.columns and 'order_purchase_timestamp' in df.columns:
            self.logger.info("Calculating approval duration in days.")
            df['approval_days'] = (df['order_approved_at'] - df['order_purchase_timestamp']).dt.total_seconds() / 86400.0
        else:
            self.logger.info("Skipping approval duration because required columns are missing.")
            
        if 'order_delivered_carrier_date' in df.columns and 'order_approved_at' in df.columns:
            self.logger.info("Calculating dispatch duration in days.")
            df['dispatch_days'] = (df['order_delivered_carrier_date'] - df['order_approved_at']).dt.total_seconds() / 86400.0
        else:
            self.logger.info("Skipping dispatch duration because required columns are missing.")
            
        if 'order_delivered_customer_date' in df.columns and 'order_delivered_carrier_date' in df.columns:
            self.logger.info("Calculating transit duration in days.")
            df['transit_days'] = (df['order_delivered_customer_date'] - df['order_delivered_carrier_date']).dt.total_seconds() / 86400.0
        else:
            self.logger.info("Skipping transit duration because required columns are missing.")
            
        self.logger.info("Completed event model transformation.")
        return df

    def generate_kpi_dashboard(self, event_model: pd.DataFrame) -> pd.DataFrame:
        """Aggregates the event model into the final business KPIs."""
        self.logger.info("Generating KPI dashboard.")
        
        self.logger.info("Calculating total order count.")
        total_orders = len(event_model)
        self.logger.info("Calculating late order count.")
        late_orders = event_model['is_late'].sum()
        self.logger.info("Calculating late order percentage.")
        pct_late = (late_orders / total_orders) * 100 if total_orders > 0 else 0
        
        self.logger.info("Filtering late orders for duration metrics.")
        late_df = event_model[event_model['is_late']]
        
        # Isolating where the delay happens for late orders
        self.logger.info("Calculating average approval duration for late orders.")
        avg_approval = late_df['approval_days'].mean() if 'approval_days' in late_df else 0
        self.logger.info("Calculating average dispatch duration for late orders.")
        avg_dispatch = late_df['dispatch_days'].mean() if 'dispatch_days' in late_df else 0
        self.logger.info("Calculating average transit duration for late orders.")
        avg_transit = late_df['transit_days'].mean() if 'transit_days' in late_df else 0
        
        self.logger.info("Constructing KPI dashboard dataframe.")
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