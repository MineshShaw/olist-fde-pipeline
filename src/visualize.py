import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DataVisualizer:
    def __init__(self, viz_dir: Path):
        self.viz_dir = viz_dir
        sns.set_theme(style="whitegrid")

    def generate_insights(self, event_model: pd.DataFrame):
        logger.info("Generating and saving visual insights...")
        
        plt.figure(figsize=(10, 6))
        if 'transit_days' in event_model.columns:
            sns.histplot(
                data=event_model, x='transit_days', hue='is_late', 
                kde=True, bins=30, palette={False: "blue", True: "red"}
            )
            plt.title("Distribution of Carrier Transit Times")
            plt.xlabel("Transit Time (Days)")
            plt.ylabel("Order Count")
            plt.savefig(self.viz_dir / "transit_times_distribution.png", bbox_inches='tight')
            plt.close()

        plt.figure(figsize=(8, 5))
        late_orders = event_model[event_model['is_late'] == True]
        if not late_orders.empty:
            avg_times = {
                'Approval': late_orders['approval_days'].mean(),
                'Dispatch': late_orders['dispatch_days'].mean(),
                'Transit': late_orders['transit_days'].mean()
            }
            sns.barplot(
                x=list(avg_times.keys()), y=list(avg_times.values()), 
                palette="viridis", hue=list(avg_times.keys()), legend=False
            )
            plt.title("Average Days Spent per Stage (Late Orders Only)")
            plt.ylabel("Average Days")
            plt.savefig(self.viz_dir / "late_order_bottlenecks.png", bbox_inches='tight')
            plt.close()