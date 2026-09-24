import logging
from pathlib import Path
from src.extract import DataExtractor
from src.validate import DataValidator
from src.model import DataModeler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def run(self):
        try:
            logger.info("--- Starting Dependable Olist Pipeline ---")
            
            # 1. Extraction
            extractor = DataExtractor()
            raw_data = extractor.run_all()
            
            # 2. Validation
            validator = DataValidator()
            validated_data = validator.run_all(raw_data)
            
            if 'orders' not in validated_data or validated_data['orders']['clean'].empty:
                logger.error("No valid orders available to model. Halting pipeline.")
                return
            
            # 3. Modeling
            modeler = DataModeler()
            event_model = modeler.process_event_model(validated_data['orders']['clean'])
            kpi_dashboard = modeler.generate_kpi_dashboard(event_model)
            
            # 4. Output Generation (Dependable Evidence)
            # Using safe overwrites for rerun-ability
            kpi_path = self.output_dir / "kpi_dashboard.csv"
            event_path = self.output_dir / "clean_event_model.csv"
            anomalies_path = self.output_dir / "flagged_anomalies.csv"
            
            kpi_dashboard.to_csv(kpi_path, index=False)
            event_model.to_csv(event_path, index=False)
            
            if not validated_data['orders']['anomalies'].empty:
                validated_data['orders']['anomalies'].to_csv(anomalies_path, index=False)
            
            logger.info(f"Pipeline succeeded. KPIs saved to {kpi_path}")
            
        except Exception as e:
            logger.critical(f"Pipeline experienced a fatal failure: {e}")
            raise
            
if __name__ == "__main__":
    orchestrator = PipelineOrchestrator()
    orchestrator.run()