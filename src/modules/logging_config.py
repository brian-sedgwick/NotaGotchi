"""
Not-A-Gotchi Logging Configuration

Provides structured logging throughout the application.
Replaces print() statements with proper logging levels and formatting.
"""

import logging
import sys
from typing import Optional


# Default log format with timestamp, level, module, and message
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Shorter format for console output
CONSOLE_FORMAT = "[%(levelname).1s] %(name)s: %(message)s"


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path to write logs
        console: Whether to output to console (default True)

    Returns:
        Root logger for the application
    """
    # Get or create the root logger for notagotchi
    logger = logging.getLogger("notagotchi")
    logger.setLevel(level)

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(CONSOLE_FORMAT)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance for the module

    Usage:
        from modules.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Starting up...")
        logger.debug("Debug details")
        logger.warning("Something unexpected")
        logger.error("An error occurred", exc_info=True)
    """
    # Create child logger under notagotchi namespace
    if name.startswith("modules."):
        # Strip "modules." prefix for cleaner names
        name = name[8:]
    return logging.getLogger(f"notagotchi.{name}")


# Convenience functions for quick logging without getting a logger
def log_info(message: str, module: str = "app") -> None:
    """Log an info message."""
    get_logger(module).info(message)


def log_warning(message: str, module: str = "app") -> None:
    """Log a warning message."""
    get_logger(module).warning(message)


def log_error(message: str, module: str = "app", exc_info: bool = False) -> None:
    """Log an error message, optionally with exception info."""
    get_logger(module).error(message, exc_info=exc_info)


def log_debug(message: str, module: str = "app") -> None:
    """Log a debug message."""
    get_logger(module).debug(message)
