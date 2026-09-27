import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from pathlib import Path
from typing import Optional

from src.config import PipelineConfig
from src.logger import PipelineLogger, default_logger


class DataVisualizer:
    def __init__(
        self,
        viz_dir: Optional[Path] = None,
        logger: Optional[PipelineLogger] = None,
        output_dir: Optional[str] = None,
        config: Optional[PipelineConfig] = None,
    ):
        self.config = config or PipelineConfig()
        self.viz_dir = Path(output_dir) if output_dir is not None else viz_dir
        if self.viz_dir is None:
            raise ValueError("A visualization output directory is required.")
        self.logger = logger or default_logger()
        self.logger.info(f"Initialized data visualizer for directory: {self.viz_dir}.")
        sns.set_theme(
            style=self.config.visualization_style,
            palette=self.config.visualization_palette["stages"],
        )

    def generate_insights(self, event_model: pd.DataFrame) -> None:
        self.logger.info("Generating and saving visual insights.")
        transit_path = self.viz_dir / self.config.artifacts["transit_chart_file"]
        bottleneck_path = self.viz_dir / self.config.artifacts["bottleneck_chart_file"]

        if "transit_days" in event_model.columns:
            self.logger.info("Creating transit time figure.")
            figure, axis = plt.subplots(figsize=self.config.transit_figure_size)
            try:
                sns.histplot(
                    data=event_model,
                    x="transit_days",
                    hue="is_late",
                    kde=True,
                    bins=self.config.transit_bins,
                    palette={
                        False: self.config.visualization_palette["on_time"],
                        True: self.config.visualization_palette["late"],
                    },
                    ax=axis,
                )
                axis.set_title("Distribution of Carrier Transit Times")
                axis.set_xlabel("Transit Time (Days)")
                axis.set_ylabel("Order Count")
                figure.savefig(transit_path, bbox_inches="tight")
            finally:
                plt.close(figure)
        else:
            self.logger.info(
                "Removing stale transit visualization because transit duration is unavailable."
            )
            transit_path.unlink(missing_ok=True)

        if "is_late" in event_model.columns:
            late_orders = event_model[event_model["is_late"].fillna(False).astype(bool)]
        else:
            late_orders = event_model.iloc[0:0]

        if not late_orders.empty:
            stage_columns = ("approval_days", "dispatch_days", "transit_days")
            missing_columns = [column for column in stage_columns if column not in late_orders]
            if missing_columns:
                raise ValueError(
                    "Cannot create bottleneck chart; event model is missing: "
                    + ", ".join(missing_columns)
                )

            average_times = {
                "Approval": late_orders["approval_days"].mean(),
                "Dispatch": late_orders["dispatch_days"].mean(),
                "Transit": late_orders["transit_days"].mean(),
            }
            figure, axis = plt.subplots(figsize=self.config.bottleneck_figure_size)
            try:
                sns.barplot(
                    x=list(average_times.keys()),
                    y=list(average_times.values()),
                    palette=self.config.visualization_palette["stages"],
                    hue=list(average_times.keys()),
                    legend=False,
                    ax=axis,
                )
                axis.set_title("Average Days Spent per Stage (Late Orders Only)")
                axis.set_ylabel("Average Days")
                figure.savefig(bottleneck_path, bbox_inches="tight")
            finally:
                plt.close(figure)
        else:
            self.logger.info(
                "Removing stale bottleneck visualization because no late orders exist."
            )
            bottleneck_path.unlink(missing_ok=True)
