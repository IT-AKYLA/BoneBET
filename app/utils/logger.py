import logging
import sys
from typing import Any, Optional

import structlog
from structlog.types import EventDict, Processor


def add_app_context(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    """Add application context to log events."""
    from app.config import get_settings
    
    settings = get_settings()
    event_dict["app"] = settings.APP_NAME
    event_dict["env"] = settings.ENVIRONMENT
    return event_dict


def setup_logging(
    level: str = "INFO",
    json_format: bool = False,
) -> None:
    """Configure structured logging."""
    
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        add_app_context,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    if json_format:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Set standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)