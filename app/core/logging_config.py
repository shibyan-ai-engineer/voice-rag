"""
Configuration for application logging.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.config import LOGS_DIR, DEBUG


def configure_logging():
    """Configure logging for the application."""
    log_file = LOGS_DIR / "app.log"
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10485760, backupCount=5  # 10 MB  # Keep 5 backups
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Set levels for external libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Return the configured logger
    return root_logger

# Logger to be used across the application
logger = configure_logging()