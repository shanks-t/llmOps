"""Internal logging utilities."""

import logging

# Create SDK logger
logger = logging.getLogger("llmops")

# Default to WARNING to avoid noise
logger.setLevel(logging.WARNING)


def log_internal_error(operation: str, error: Exception) -> None:
    """Log an internal SDK error without raising to user code."""
    logger.warning(f"llmops internal error in {operation}: {error}", exc_info=True)


def log_debug(message: str) -> None:
    """Log a debug message."""
    logger.debug(message)


def log_info(message: str) -> None:
    """Log an info message."""
    logger.info(message)
