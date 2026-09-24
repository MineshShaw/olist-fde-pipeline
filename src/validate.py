import pandas as pd
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

class DataValidator:
    """
    Class 6 Validation Layer: Enforces business rules and schema expectations.
    Anomalies are flagged and segregated rather than silently discarded.
    """
    def __init__(self):
        # In a real environment, rule thresholds could be configured here.
        pass

    def validate_orders(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Validates the orders dataframe against business rules.
        Returns a tuple of (clean_df, anomalies_df).
        """
        logger.info("Starting validation for orders data...")
        df = df.copy()
        
        # 1. Cast datetimes securely
        date_cols = ['order_purchase_timestamp', 'order_delivered_customer_date', 'order_estimated_delivery_date']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # Initialize anomaly tracking columns
        df['is_valid'] = True
        df['anomaly_reason'] = ""
        
        # Rule A: Chronological Mismatch (Time travel / Negative transit time)
        if 'order_delivered_customer_date' in df.columns and 'order_purchase_timestamp' in df.columns:
            time_travel_mask = df['order_delivered_customer_date'] < df['order_purchase_timestamp']
            df.loc[time_travel_mask, 'is_valid'] = False
            df.loc[time_travel_mask, 'anomaly_reason'] += "Delivered before purchase date; "
        
        # Rule B: Missing Status Transitions
        if 'order_status' in df.columns and 'order_delivered_customer_date' in df.columns:
            missing_transition_mask = (df['order_status'] == 'delivered') & (df['order_delivered_customer_date'].isna())
            df.loc[missing_transition_mask, 'is_valid'] = False
            df.loc[missing_transition_mask, 'anomaly_reason'] += "Status 'delivered' but missing delivery date; "

        # Segregate clean data from anomalies
        clean_df = df[df['is_valid']].drop(columns=['is_valid', 'anomaly_reason'])
        anomalies_df = df[~df['is_valid']]
        
        logger.info(f"Validation complete: {len(clean_df)} valid records, {len(anomalies_df)} anomalies found.")
        return clean_df, anomalies_df

    def run_all(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Runs validation across all extracted datasets.
        Returns a dictionary containing 'clean' and 'anomalies' for each table.
        """
        validated_data = {}
        
        if 'orders' in raw_data:
            clean, anomalies = self.validate_orders(raw_data['orders'])
            validated_data['orders'] = {'clean': clean, 'anomalies': anomalies}
        else:
            logger.warning("No 'orders' dataframe found to validate.")
            
        # Pass-through for other tables. In a full production setup, 
        # we would implement validate_payments(), validate_reviews(), etc.
        for key, df in raw_data.items():
            if key != 'orders':
                validated_data[key] = {'clean': df, 'anomalies': pd.DataFrame()}
                
        return validated_data