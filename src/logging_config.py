"""
Structured Logging Configuration
Configures structlog for production-grade JSON logging
"""

import os
import sys
import structlog
from pythonjsonlogger import jsonlogger


def setup_logging():
    """
    Configure structured logging for the application

    Outputs JSON-formatted logs for production systems
    Use plain text for local development
    """
    environment = os.getenv('ENVIRONMENT', 'development')
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    # Determine if we're in production
    is_production = environment == 'production'

    # Configure standard library logging
    import logging

    # Set log level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
    )

    # Processors for structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Add appropriate renderer based on environment
    if is_production:
        # JSON output for production (easy parsing by log aggregators)
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty console output for development
        processors.append(structlog.dev.ConsoleRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        wrapper_class=structlog.stdlib.BoundLogger,
    )


def get_logger(name=None):
    """
    Get a configured logger instance

    Args:
        name: Logger name (usually __name__ of the module)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name or __name__)


# Initialize logging on module import
setup_logging()
