import pandas as pd
from itertools import combinations
from typing import Dict, Optional, Tuple

from src.config import PipelineConfig
from src.logger import PipelineLogger, default_logger


class DataValidator:
    """Validate order chronology while preserving anomalies for review."""

    def __init__(
        self,
        logger: Optional[PipelineLogger] = None,
        config: Optional[PipelineConfig] = None,
    ):
        self.config = config or PipelineConfig()
        self.logger = logger or default_logger()
        self.logger.info("Initialized data validator.")

    def validate_orders(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Return clean orders and invalid orders with one or more anomaly reasons."""
        self.logger.info("Starting validation for orders data.")
        df = df.copy()
        timestamp_columns = self.config.timestamp_columns
        required_columns = {"order_status", *timestamp_columns.values()}
        missing_columns = required_columns.difference(df.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Orders data is missing required validation columns: {missing}")

        original_timestamps = df[list(timestamp_columns.values())].copy()
        for column in timestamp_columns.values():
            df[column] = pd.to_datetime(df[column], errors="coerce")

        df["is_valid"] = True
        df["anomaly_reason"] = ""
        status = df["order_status"].astype("string").str.strip().str.casefold()
        delivered = status.eq(self.config.delivered_status.casefold()).fillna(False)

        labels = {
            "purchase": "purchase",
            "approval": "approval",
            "dispatch": "dispatch",
            "delivery": "delivery",
            "estimate": "estimated delivery",
        }
        for key, column in timestamp_columns.items():
            raw_value = original_timestamps[column]
            provided_value = (
                raw_value.notna()
                & raw_value.astype("string").str.strip().ne("").fillna(False)
            )
            invalid_value = provided_value & df[column].isna()
            if invalid_value.any():
                df.loc[invalid_value, "is_valid"] = False
                df.loc[invalid_value, "anomaly_reason"] += (
                    f"Invalid {labels[key]} timestamp; "
                )

            missing_delivered_value = delivered & df[column].isna()
            if missing_delivered_value.any():
                df.loc[missing_delivered_value, "is_valid"] = False
                if key == "delivery":
                    reason = "Status 'delivered' but missing delivery date; "
                else:
                    reason = (
                        f"Status 'delivered' but missing "
                        f"{labels[key]} timestamp; "
                    )
                df.loc[missing_delivered_value, "anomaly_reason"] += reason

        event_keys = ("purchase", "approval", "dispatch", "delivery")
        for earlier_key, later_key in combinations(event_keys, 2):
            earlier = timestamp_columns[earlier_key]
            later = timestamp_columns[later_key]
            reversed_order = (
                df[earlier].notna()
                & df[later].notna()
                & (df[later] < df[earlier])
            )
            if reversed_order.any():
                df.loc[reversed_order, "is_valid"] = False
                if earlier_key == "purchase" and later_key == "delivery":
                    reason = "Delivered before purchase date; "
                else:
                    reason = (
                        f"{labels[later_key].capitalize()} timestamp before "
                        f"{labels[earlier_key]} timestamp; "
                    )
                df.loc[reversed_order, "anomaly_reason"] += reason

        clean_df = df[df["is_valid"]].drop(columns=["is_valid", "anomaly_reason"])
        anomalies_df = df[~df["is_valid"]]
        self.logger.info(
            f"Validation complete: {len(clean_df)} valid records, "
            f"{len(anomalies_df)} anomalies found."
        )
        return clean_df, anomalies_df

    def run_all(self, raw_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Validate orders and pass through other extracted datasets."""
        validated_data = {}

        if "orders" in raw_data:
            clean, anomalies = self.validate_orders(raw_data["orders"])
            validated_data["orders"] = {"clean": clean, "anomalies": anomalies}
        else:
            self.logger.warn("No 'orders' dataframe found to validate.")

        for key, df in raw_data.items():
            if key != "orders":
                self.logger.info(f"Passing through dataset without additional rules: {key}.")
                validated_data[key] = {"clean": df, "anomalies": pd.DataFrame()}

        self.logger.info("Completed validation for all datasets.")
        return validated_data
