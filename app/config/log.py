import logging
import logging.handlers
import sys
from pathlib import Path

from app.config.settings import settings

LOG_FILE = "logs/app.log"

def setup_logging():
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(settings.log_level.upper())
    app_logger.propagate = False

    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    file_handler = logging.FileHandler(
        filename=LOG_FILE,
        encoding="utf-8",
    )
    file_handler.setFormatter(file_formatter)

    app_logger.addHandler(console_handler)
    app_logger.addHandler(file_handler)