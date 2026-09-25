import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional
from src.logger import PipelineLogger, default_logger

class DataVisualizer:
    def __init__(self, viz_dir: Path, logger: Optional[PipelineLogger] = None):
        self.viz_dir = viz_dir
        self.logger = logger or default_logger()
        self.logger.info(f"Initialized data visualizer for directory: {viz_dir}.")
        self.logger.info("Configuring seaborn visualization theme.")
        sns.set_theme(style="whitegrid")

    def generate_insights(self, event_model: pd.DataFrame):
        self.logger.info("Generating and saving visual insights.")
        
        self.logger.info("Creating transit time figure.")
        plt.figure(figsize=(10, 6))
        if 'transit_days' in event_model.columns:
            self.logger.info("Plotting transit time histogram.")
            sns.histplot(
                data=event_model, x='transit_days', hue='is_late', 
                kde=True, bins=30, palette={False: "blue", True: "red"}
            )
            plt.title("Distribution of Carrier Transit Times")
            plt.xlabel("Transit Time (Days)")
            plt.ylabel("Order Count")
            self.logger.info("Saving transit time visualization artifact.")
            plt.savefig(self.viz_dir / "transit_times_distribution.png", bbox_inches='tight')
            self.logger.info("Closing transit time figure.")
            plt.close()
        else:
            self.logger.info("Skipping transit time visualization because the column is missing.")

        self.logger.info("Creating late-order bottleneck figure.")
        plt.figure(figsize=(8, 5))
        self.logger.info("Filtering late orders.")
        late_orders = event_model[event_model['is_late'] == True]
        if not late_orders.empty:
            self.logger.info("Calculating average late-order stage durations.")
            avg_times = {
                'Approval': late_orders['approval_days'].mean(),
                'Dispatch': late_orders['dispatch_days'].mean(),
                'Transit': late_orders['transit_days'].mean()
            }
            self.logger.info("Plotting late-order bottleneck bars.")
            sns.barplot(
                x=list(avg_times.keys()), y=list(avg_times.values()), 
                palette="viridis", hue=list(avg_times.keys()), legend=False
            )
            plt.title("Average Days Spent per Stage (Late Orders Only)")
            plt.ylabel("Average Days")
            self.logger.info("Saving late-order bottleneck visualization artifact.")
            plt.savefig(self.viz_dir / "late_order_bottlenecks.png", bbox_inches='tight')
            self.logger.info("Closing late-order bottleneck figure.")
            plt.close()
        else:
            self.logger.info("Skipping late-order bottleneck visualization because no late orders exist.")