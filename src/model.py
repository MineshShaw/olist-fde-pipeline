import pandas as pd
from typing import Optional
from src.config import PipelineConfig
from src.logger import PipelineLogger, default_logger

class DataModeler:
    """
    Class 7 & 8 Modeling Layer: Transforms clean operational data into 
    event-based chronologies and business KPIs.
    """
    def __init__(
        self,
        logger: Optional[PipelineLogger] = None,
        config: Optional[PipelineConfig] = None,
    ):
        self.config = config or PipelineConfig()
        self.logger = logger or default_logger()
        self.logger.info("Initialized data modeler.")

    def process_event_model(self, clean_orders: pd.DataFrame) -> pd.DataFrame:
        """Reconstructs the order workflow and calculates stage durations."""
        self.logger.info("Processing event model and calculating stage durations.")
        self.logger.info("Copying clean orders dataframe for modeling.")
        df = clean_orders.copy()
        
        # Ensure all timestamps are datetime objects
        timestamps = self.config.timestamp_columns
        cols = list(timestamps.values())
        self.logger.info("Starting loop over event timestamp columns.")
        for col in cols:
            if col in df.columns:
                self.logger.info(f"Changing data type of event column to datetime: {col}.")
                df[col] = pd.to_datetime(df[col], errors='coerce')
            else:
                self.logger.info(f"Skipping missing event timestamp column: {col}.")
                
        # Primary KPI Flag: Was it delivered past the estimated date?
        self.logger.info("Calculating late delivery flag.")
        df['is_late'] = df[timestamps["delivery"]] > df[timestamps["estimate"]]
        
        # Duration Math (in days)
        if timestamps["approval"] in df.columns and timestamps["purchase"] in df.columns:
            self.logger.info("Calculating approval duration in days.")
            df['approval_days'] = (
                df[timestamps["approval"]] - df[timestamps["purchase"]]
            ).dt.total_seconds() / self.config.seconds_per_day
        else:
            self.logger.info("Skipping approval duration because required columns are missing.")
            
        if timestamps["dispatch"] in df.columns and timestamps["approval"] in df.columns:
            self.logger.info("Calculating dispatch duration in days.")
            df['dispatch_days'] = (
                df[timestamps["dispatch"]] - df[timestamps["approval"]]
            ).dt.total_seconds() / self.config.seconds_per_day
        else:
            self.logger.info("Skipping dispatch duration because required columns are missing.")
            
        if timestamps["delivery"] in df.columns and timestamps["dispatch"] in df.columns:
            self.logger.info("Calculating transit duration in days.")
            df['transit_days'] = (
                df[timestamps["delivery"]] - df[timestamps["dispatch"]]
            ).dt.total_seconds() / self.config.seconds_per_day
        else:
            self.logger.info("Skipping transit duration because required columns are missing.")
            
        self.logger.info("Completed event model transformation.")
        return df

    def generate_kpi_dashboard(
        self,
        event_model: pd.DataFrame,
        excluded_delivered_orders: int = 0,
    ) -> pd.DataFrame:
        """Aggregates the event model into the final business KPIs."""
        self.logger.info("Generating KPI dashboard.")
        
        timestamps = self.config.timestamp_columns
        if "order_status" in event_model.columns:
            delivered_orders = (
                event_model["order_status"]
                .astype("string")
                .str.strip()
                .str.casefold()
                .eq(self.config.delivered_status.casefold())
                .fillna(False)
            )
        else:
            delivered_orders = event_model[timestamps["delivery"]].notna()

        valid_orders = (
            event_model["is_valid"].fillna(False).astype(bool)
            if "is_valid" in event_model.columns
            else pd.Series(True, index=event_model.index)
        )
        comparable_orders = (
            delivered_orders
            & valid_orders
            & event_model[timestamps["delivery"]].notna()
            & event_model[timestamps["estimate"]].notna()
        )
        excluded_count = int(excluded_delivered_orders) + int(
            (delivered_orders & ~comparable_orders).sum()
        )
        self.logger.info("Calculating comparable delivered order count.")
        total_orders = int(comparable_orders.sum())
        self.logger.info("Calculating late order count.")
        late_mask = comparable_orders & event_model["is_late"].fillna(False)
        late_orders = int(late_mask.sum())
        self.logger.info("Calculating late order percentage.")
        pct_late = (late_orders / total_orders) * 100 if total_orders > 0 else 0
        
        self.logger.info("Filtering late orders for duration metrics.")
        late_df = event_model[late_mask]
        
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
                "Delivered Orders Excluded from KPI",
                "Avg Approval Time (Late Orders) [Days]",
                "Avg Seller Dispatch Time (Late Orders) [Days]",
                "Avg Carrier Transit Time (Late Orders) [Days]"
            ],
            "Value": [
                total_orders,
                late_orders,
                round(pct_late, 2),
                excluded_count,
                round(avg_approval, 2),
                round(avg_dispatch, 2),
                round(avg_transit, 2)
            ]
        })