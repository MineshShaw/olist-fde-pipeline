import logging
from datetime import date

from src.config import PipelineConfig


class PipelineLogger:
    def __init__(self, config: PipelineConfig, run_date: str):
        self.config = config
        self.run_date = run_date
        self.log_dir = self.config.base_output_dir / run_date / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        logger_name = f"olist_pipeline.{run_date}"
        self._logger = logging.getLogger(logger_name)
        self._logger.handlers.clear()
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        file_handler = logging.FileHandler(self.log_dir / "pipeline.log")
        terminal_handler = logging.StreamHandler()
        file_handler.setFormatter(formatter)
        terminal_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)
        self._logger.addHandler(terminal_handler)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warn(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)


def default_logger() -> PipelineLogger:
    return PipelineLogger(PipelineConfig(), date.today().isoformat())