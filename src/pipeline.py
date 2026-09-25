import argparse
import logging
from src.config import PipelineConfig
from src.extract import DataExtractor
from src.validate import DataValidator
from src.model import DataModeler
from src.visualize import DataVisualizer

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, run_date: str, config: PipelineConfig):
        self.run_date = run_date
        self.config = config
        
        # 1. Define Subdirectories
        self.run_dir = self.config.base_output_dir / self.run_date
        self.logs_dir = self.run_dir / "logs"
        self.data_dir = self.run_dir / "data"
        self.viz_dir = self.run_dir / "visualizations"
        
        # 2. Create them safely
        for directory in [self.logs_dir, self.data_dir, self.viz_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        self._setup_logging()
        
    def _setup_logging(self):
        logger.handlers = []
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        
        # Route log file specifically to the /logs subdirectory
        fh = logging.FileHandler(self.logs_dir / "pipeline.log")
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    def run(self):
        try:
            logger.info(f"--- Starting Dependable Olist Pipeline for {self.run_date} ---")
            
            # Extract
            extractor = DataExtractor(self.config)
            raw_data = extractor.run_all()
            
            raw_orders_count = len(raw_data['orders'])
            
            # Validate
            validator = DataValidator()
            validated_data = validator.run_all(raw_data)
            
            clean_orders = validated_data['orders']['clean']
            anomaly_orders = validated_data['orders']['anomalies']
            
            # --- DATA RECONCILIATION CHECK ---
            reconciled_count = len(clean_orders) + len(anomaly_orders)
            if reconciled_count != raw_orders_count:
                logger.critical(f"Data leak detected! Raw: {raw_orders_count}, Clean+Anomaly: {reconciled_count}")
                raise ValueError("Validation layer dropped records silently.")
            logger.info(f"Reconciliation successful: {len(clean_orders)} clean + {len(anomaly_orders)} anomalies == {raw_orders_count} raw.")
            
            if clean_orders.empty:
                logger.error("No valid orders available. Halting.")
                return
            
            # Model & Visualize
            modeler = DataModeler()
            event_model = modeler.process_event_model(clean_orders)
            kpi_dashboard = modeler.generate_kpi_dashboard(event_model)
            
            visualizer = DataVisualizer(viz_dir=self.viz_dir)
            visualizer.generate_insights(event_model)
            
            # Save Outputs to /data
            kpi_dashboard.to_csv(self.data_dir / "kpi_dashboard.csv", index=False)
            event_model.to_csv(self.data_dir / "clean_event_model.csv", index=False)
            if not anomaly_orders.empty:
                anomaly_orders.to_csv(self.data_dir / "flagged_anomalies.csv", index=False)
            
            logger.info(f"Pipeline succeeded. Artifacts routed to {self.run_dir}")
            
        except Exception as e:
            logger.critical(f"Pipeline failed: {e}")
            raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-date", type=str, required=True, help="Run date in YYYY-MM-DD")
    args = parser.parse_args()
    
    config = PipelineConfig()
    orchestrator = PipelineOrchestrator(run_date=args.run_date, config=config)
    orchestrator.run()