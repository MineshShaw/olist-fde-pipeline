import pandas as pd
from typing import Dict, Optional, Tuple
from src.logger import PipelineLogger, default_logger

class DataValidator:
    """
    Class 6 Validation Layer: Enforces business rules and schema expectations.
    Anomalies are flagged and segregated rather than silently discarded.
    """
    def __init__(self, logger: Optional[PipelineLogger] = None):
        # In a real environment, rule thresholds could be configured here.
        self.logger = logger or default_logger()
        self.logger.info("Initialized data validator.")

    def validate_orders(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Validates the orders dataframe against business rules.
        Returns a tuple of (clean_df, anomalies_df).
        """
        self.logger.info("Starting validation for orders data.")
        self.logger.info("Copying orders dataframe for validation.")
        df = df.copy()
        
        # 1. Cast datetimes securely
        date_cols = ['order_purchase_timestamp', 'order_delivered_customer_date', 'order_estimated_delivery_date']
        self.logger.info("Starting loop over order date columns.")
        for col in date_cols:
            if col in df.columns:
                self.logger.info(f"Changing data type of order column to datetime: {col}.")
                df[col] = pd.to_datetime(df[col], errors='coerce')
            else:
                self.logger.info(f"Skipping missing order date column: {col}.")
        
        # Initialize anomaly tracking columns
        self.logger.info("Adding validation status column.")
        df['is_valid'] = True
        self.logger.info("Adding anomaly reason column.")
        df['anomaly_reason'] = ""
        
        # Rule A: Chronological Mismatch (Time travel / Negative transit time)
        if 'order_delivered_customer_date' in df.columns and 'order_purchase_timestamp' in df.columns:
            self.logger.info("Calculating chronological mismatch mask.")
            time_travel_mask = df['order_delivered_customer_date'] < df['order_purchase_timestamp']
            self.logger.info("Marking chronological mismatches invalid.")
            df.loc[time_travel_mask, 'is_valid'] = False
            self.logger.info("Recording chronological mismatch reasons.")
            df.loc[time_travel_mask, 'anomaly_reason'] += "Delivered before purchase date; "
        else:
            self.logger.info("Skipping chronological mismatch rule because required columns are missing.")
        
        # Rule B: Missing Status Transitions
        if 'order_status' in df.columns and 'order_delivered_customer_date' in df.columns:
            self.logger.info("Calculating missing status transition mask.")
            missing_transition_mask = (df['order_status'] == 'delivered') & (df['order_delivered_customer_date'].isna())
            self.logger.info("Marking missing status transitions invalid.")
            df.loc[missing_transition_mask, 'is_valid'] = False
            self.logger.info("Recording missing status transition reasons.")
            df.loc[missing_transition_mask, 'anomaly_reason'] += "Status 'delivered' but missing delivery date; "
        else:
            self.logger.info("Skipping missing status transition rule because required columns are missing.")

        # Segregate clean data from anomalies
        self.logger.info("Filtering clean records and dropping validation columns.")
        clean_df = df[df['is_valid']].drop(columns=['is_valid', 'anomaly_reason'])
        self.logger.info("Filtering anomaly records.")
        anomalies_df = df[~df['is_valid']]
        
        self.logger.info(f"Validation complete: {len(clean_df)} valid records, {len(anomalies_df)} anomalies found.")
        return clean_df, anomalies_df

    def run_all(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Runs validation across all extracted datasets.
        Returns a dictionary containing 'clean' and 'anomalies' for each table.
        """
        self.logger.info("Initializing validated data collection.")
        validated_data = {}
        
        if 'orders' in raw_data:
            self.logger.info("Validating orders dataset.")
            clean, anomalies = self.validate_orders(raw_data['orders'])
            self.logger.info("Storing validated orders and anomalies.")
            validated_data['orders'] = {'clean': clean, 'anomalies': anomalies}
        else:
            self.logger.warn("No 'orders' dataframe found to validate.")
            
        # Pass-through for other tables. In a full production setup, 
        # we would implement validate_payments(), validate_reviews(), etc.
        self.logger.info("Starting loop over non-order datasets for pass-through validation.")
        for key, df in raw_data.items():
            if key != 'orders':
                self.logger.info(f"Passing through dataset without additional rules: {key}.")
                validated_data[key] = {'clean': df, 'anomalies': pd.DataFrame()}
            else:
                self.logger.info("Skipping orders dataset during pass-through loop.")
                
        self.logger.info("Completed validation for all datasets.")
        return validated_data