"""
Logging configuration for LostMindAI Backend API Service.

Provides structured logging with different levels for development and production.
"""

import logging
import logging.config
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    log_to_file: bool = True,
    log_to_console: bool = True
) -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        log_to_file: Whether to log to files
        log_to_console: Whether to log to console
    """
    # Create logs directory
    if log_to_file:
        Path(log_dir).mkdir(exist_ok=True)
    
    # Create log filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"lostmindai_backend_{timestamp}.log")
    
    # Logging configuration
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "simple": {
                "format": "%(levelname)s - %(name)s - %(message)s"
            },
            "json": {
                "format": "%(asctime)s %(name)s %(levelname)s %(module)s %(lineno)d %(message)s",
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
            }
        },
        "handlers": {},
        "root": {
            "level": log_level,
            "handlers": []
        },
        "loggers": {
            "lostmindai": {
                "level": log_level,
                "handlers": [],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": [],
                "propagate": False
            },
            "fastapi": {
                "level": "INFO", 
                "handlers": [],
                "propagate": False
            }
        }
    }
    
    # Console handler
    if log_to_console:
        config["handlers"]["console"] = {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "detailed",
            "stream": sys.stdout
        }
        config["root"]["handlers"].append("console")
        config["loggers"]["lostmindai"]["handlers"].append("console")
        config["loggers"]["uvicorn"]["handlers"].append("console")
        config["loggers"]["fastapi"]["handlers"].append("console")
    
    # File handler
    if log_to_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": log_level,
            "formatter": "detailed",
            "filename": log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8"
        }
        config["root"]["handlers"].append("file")
        config["loggers"]["lostmindai"]["handlers"].append("file")
        config["loggers"]["uvicorn"]["handlers"].append("file")
        config["loggers"]["fastapi"]["handlers"].append("file")
    
    # Error file handler for production
    if log_to_file and log_level in ["WARNING", "ERROR", "CRITICAL"]:
        error_file = os.path.join(log_dir, f"lostmindai_backend_errors_{timestamp}.log")
        config["handlers"]["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": error_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "encoding": "utf-8"
        }
        config["root"]["handlers"].append("error_file")
        config["loggers"]["lostmindai"]["handlers"].append("error_file")
    
    # Apply configuration
    logging.config.dictConfig(config)
    
    # Set up specific logger levels for third-party libraries
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger("lostmindai.startup")
    logger.info(f"Logging configured - Level: {log_level}, File: {log_file if log_to_file else 'None'}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"lostmindai.{name}")


class ContextFilter(logging.Filter):
    """
    Logging filter to add context information to log records.
    """
    
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record):
        """Add context to log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def add_context_to_logger(logger: logging.Logger, **context) -> None:
    """
    Add context information to a logger.
    
    Args:
        logger: Logger instance
        **context: Context key-value pairs
    """
    context_filter = ContextFilter(context)
    logger.addFilter(context_filter)