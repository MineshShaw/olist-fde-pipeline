import argparse
from src.config import PipelineConfig
from src.extract import DataExtractor
from src.logger import PipelineLogger
from src.validate import DataValidator
from src.model import DataModeler
from src.visualize import DataVisualizer

class PipelineOrchestrator:
    def __init__(self, run_date: str, config: PipelineConfig):
        self.run_date = run_date
        self.config = config
        self.logger = PipelineLogger(config, run_date)
        self.logger.info(f"Initializing pipeline orchestrator for run date {run_date}.")
        
        # 1. Define Subdirectories
        self.logger.info("Defining pipeline output subdirectories.")
        self.run_dir = self.config.base_output_dir / self.run_date
        self.logs_dir = self.run_dir / "logs"
        self.data_dir = self.run_dir / "data"
        self.viz_dir = self.run_dir / "visualizations"
        
        # 2. Create them safely
        self.logger.info("Starting loop to create pipeline output directories.")
        for directory in [self.logs_dir, self.data_dir, self.viz_dir]:
            self.logger.info(f"Creating output directory if missing: {directory}.")
            directory.mkdir(parents=True, exist_ok=True)
        self.logger.info("Completed pipeline output directory setup.")

    def run(self):
        try:
            self.logger.info(f"--- Starting Dependable Olist Pipeline for {self.run_date} ---")
            
            # Extract
            self.logger.info("Initializing extraction stage.")
            extractor = DataExtractor(self.config, self.logger)
            self.logger.info("Running extraction stage.")
            raw_data = extractor.run_all()
            
            self.logger.info("Counting raw orders for reconciliation.")
            raw_orders_count = len(raw_data['orders'])
            
            # Validate
            self.logger.info("Initializing validation stage.")
            validator = DataValidator(self.logger)
            self.logger.info("Running validation stage.")
            validated_data = validator.run_all(raw_data)
            
            self.logger.info("Retrieving clean orders from validation output.")
            clean_orders = validated_data['orders']['clean']
            self.logger.info("Retrieving anomalous orders from validation output.")
            anomaly_orders = validated_data['orders']['anomalies']
            
            # --- DATA RECONCILIATION CHECK ---
            self.logger.info("Calculating reconciled order count.")
            reconciled_count = len(clean_orders) + len(anomaly_orders)
            if reconciled_count != raw_orders_count:
                self.logger.error(f"Data leak detected! Raw: {raw_orders_count}, Clean+Anomaly: {reconciled_count}")
                raise ValueError("Validation layer dropped records silently.")
            self.logger.info(f"Reconciliation successful: {len(clean_orders)} clean + {len(anomaly_orders)} anomalies == {raw_orders_count} raw.")
            
            if clean_orders.empty:
                self.logger.error("No valid orders available. Halting.")
                return
            
            # Model & Visualize
            self.logger.info("Initializing modeling stage.")
            modeler = DataModeler(self.logger)
            self.logger.info("Creating event model.")
            event_model = modeler.process_event_model(clean_orders)
            self.logger.info("Creating KPI dashboard.")
            kpi_dashboard = modeler.generate_kpi_dashboard(event_model)
            
            self.logger.info("Initializing visualization stage.")
            visualizer = DataVisualizer(viz_dir=self.viz_dir, logger=self.logger)
            self.logger.info("Generating visualization insights.")
            visualizer.generate_insights(event_model)
            
            # Save Outputs to /data
            self.logger.info("Saving KPI dashboard artifact.")
            kpi_dashboard.to_csv(self.data_dir / "kpi_dashboard.csv", index=False)
            self.logger.info("Saving clean event model artifact.")
            event_model.to_csv(self.data_dir / "clean_event_model.csv", index=False)
            if not anomaly_orders.empty:
                self.logger.info("Saving flagged anomaly artifact.")
                anomaly_orders.to_csv(self.data_dir / "flagged_anomalies.csv", index=False)
            else:
                self.logger.info("Skipping flagged anomaly artifact because no anomalies exist.")
            
            self.logger.info(f"Pipeline succeeded. Artifacts routed to {self.run_dir}.")
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", type=str, required=True, help="Run date in YYYY-MM-DD")
    args = parser.parse_args()
    
    config = PipelineConfig()
    orchestrator = PipelineOrchestrator(run_date=args.run_date, config=config)
    orchestrator.run()