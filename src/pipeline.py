import argparse
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Optional

import requests
from streamlit.web import cli as stcli

from src.config import PipelineConfig
from src.extract import DataExtractor
from src.logger import PipelineLogger
from src.model import DataModeler
from src.transform import build_order_context, build_seller_order_facts
from src.validate import DataValidator
from src.visualize import DataVisualizer


SUCCESS_MANIFEST = "_SUCCESS.json"


class PipelineOrchestrator:
    def __init__(
        self,
        run_date: str,
        config: Optional[PipelineConfig] = None,
        base_output_dir: Optional[str] = None,
    ):
        self.run_date = run_date
        self.config = config or PipelineConfig(base_output_dir=base_output_dir)
        self.final_run_dir = self.config.base_output_dir / self.run_date
        self.config.base_output_dir.mkdir(parents=True, exist_ok=True)
        self.stage_dir = self.config.base_output_dir / (
            f".{self.run_date}.staging-{uuid.uuid4().hex}"
        )
        self.stage_dir.mkdir()
        self._set_run_paths(self.stage_dir)
        self.logger = PipelineLogger(
            self.config,
            run_date,
            log_dir=self.logs_dir,
        )
        self.logger.info(
            f"Initializing staged pipeline run {run_date} at {self.stage_dir}."
        )

    def _set_run_paths(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.logs_dir = self.run_dir / self.config.output_logs_dir
        self.data_dir = self.run_dir / self.config.output_data_dir
        self.viz_dir = self.run_dir / self.config.output_visualizations_dir
        for directory in (self.logs_dir, self.data_dir, self.viz_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def _check_api_reachable(self) -> None:
        endpoint = self.config.api_endpoints["payments"]
        url = f"{self.config.api_url}{endpoint if endpoint.startswith('/') else '/' + endpoint}"
        try:
            response = requests.get(
                url,
                params={
                    self.config.api_page_param: 1,
                    self.config.api_page_size_param: self.config.api_page_size,
                },
                timeout=min(self.config.api_timeout, 5.0),
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                f"Configured API is not reachable at {url}. Start the service or "
                f"correct api.url in config.yaml / OLIST_API_URL. Details: {error}"
            ) from error

    def _write_failure_state(self, error: Exception) -> None:
        state = {
            "status": "failed",
            "run_date": self.run_date,
            "error_type": type(error).__name__,
            "error": str(error),
        }
        status_path = self.stage_dir / "_RUN_STATUS.json"
        status_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _publish(self, raw_orders: int, valid_orders: int, anomaly_orders: int) -> None:
        manifest = {
            "status": "completed",
            "run_date": self.run_date,
            "raw_orders": raw_orders,
            "valid_orders": valid_orders,
            "anomaly_orders": anomaly_orders,
            "artifacts": {
                "kpi": self.config.artifacts["kpi_file"],
                "event_model": self.config.artifacts["event_model_file"],
                "seller_accountability": self.config.artifacts["seller_accountability_file"],
                "anomalies": self.config.artifacts["anomalies_file"],
            },
        }
        (self.stage_dir / SUCCESS_MANIFEST).write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8",
        )

        backup_dir = self.config.base_output_dir / (
            f".{self.run_date}.previous-{uuid.uuid4().hex}"
        )
        had_previous = self.final_run_dir.exists()
        try:
            if had_previous:
                os.replace(self.final_run_dir, backup_dir)
            os.replace(self.stage_dir, self.final_run_dir)
        except OSError:
            if had_previous and backup_dir.exists() and not self.final_run_dir.exists():
                os.replace(backup_dir, self.final_run_dir)
            raise

        self._set_run_paths(self.final_run_dir)
        if backup_dir.exists():
            try:
                shutil.rmtree(backup_dir)
            except OSError as error:
                self.logger.warn(
                    f"Published run successfully but could not remove backup "
                    f"partition {backup_dir}: {error}"
                )

    def run(self) -> None:
        published = False
        try:
            self.logger.info(
                f"--- Starting Dependable Olist Pipeline for {self.run_date} ---"
            )
            self._check_api_reachable()

            extractor = DataExtractor(self.config, self.logger)
            raw_data = extractor.run_all()
            raw_orders_count = len(raw_data["orders"])

            validator = DataValidator(self.logger, config=self.config)
            validated_data = validator.run_all(raw_data)
            clean_orders = validated_data["orders"]["clean"]
            anomaly_orders = validated_data["orders"]["anomalies"]

            reconciled_count = len(clean_orders) + len(anomaly_orders)
            if reconciled_count != raw_orders_count:
                raise ValueError(
                    f"Validation reconciliation failed: raw={raw_orders_count}, "
                    f"clean+anomalies={reconciled_count}"
                )

            anomaly_path = self.data_dir / self.config.artifacts["anomalies_file"]
            if not anomaly_orders.empty:
                anomaly_orders.to_csv(anomaly_path, index=False)
            else:
                anomaly_path.unlink(missing_ok=True)

            if clean_orders.empty:
                raise ValueError(
                    "No valid orders available; anomaly evidence is retained in "
                    "this incomplete run attempt. No published KPI was changed."
                )

            modeler = DataModeler(self.logger, config=self.config)
            event_model = modeler.process_event_model(clean_orders)
            delivered_anomalies = (
                anomaly_orders["order_status"]
                .astype("string")
                .str.strip()
                .str.casefold()
                .eq(self.config.delivered_status.casefold())
                .fillna(False)
            )
            kpi_dashboard = modeler.generate_kpi_dashboard(
                event_model,
                excluded_delivered_orders=int(delivered_anomalies.sum()),
            )

            enriched_orders = build_order_context(
                event_model,
                raw_data["items"],
                raw_data["payments"],
                raw_data["customers"],
                raw_data["geolocation"],
            )
            seller_accountability = build_seller_order_facts(
                event_model,
                raw_data["items"],
                self.config.delivered_status,
                raw_data["sellers"],
            )

            visualizer = DataVisualizer(
                viz_dir=self.viz_dir,
                logger=self.logger,
                config=self.config,
            )
            visualizer.generate_insights(event_model)

            kpi_dashboard.to_csv(
                self.data_dir / self.config.artifacts["kpi_file"],
                index=False,
            )
            enriched_orders.to_csv(
                self.data_dir / self.config.artifacts["event_model_file"],
                index=False,
            )
            seller_accountability.to_csv(
                self.data_dir / self.config.artifacts["seller_accountability_file"],
                index=False,
            )
            self._publish(
                raw_orders_count,
                len(clean_orders),
                len(anomaly_orders),
            )
            published = True
            self.logger.info(
                f"Pipeline succeeded. Published complete run to {self.final_run_dir}."
            )

            os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
            os.environ[self.config.default_run_date_env] = self.run_date
            os.environ["STREAMLIT_THEME_BASE"] = self.config.ui_default_theme
            self.logger.info("Handing over process to Streamlit dashboard...")
            sys.argv = [
                "streamlit",
                "run",
                self.config.dashboard_script,
                "--server.port",
                str(self.config.ui_port),
                "--theme.base",
                self.config.ui_default_theme,
            ]
            sys.exit(stcli.main())
        except Exception as error:
            self.logger.error(f"Pipeline failed: {error}")
            if not published:
                self._write_failure_state(error)
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run-date",
        type=str,
        required=True,
        help="Run date in YYYY-MM-DD",
    )
    arguments = parser.parse_args()
    PipelineOrchestrator(
        run_date=arguments.run_date,
        config=PipelineConfig(),
    ).run()
