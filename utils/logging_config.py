import logging
import os
import sys
from typing import Any

import structlog
from structlog.types import Processor

# --- Structlog Configuration ---


# Processor to add the log level to the event dictionary
def add_log_level(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    event_dict["level"] = method_name.upper()
    return event_dict


# Processor to add a timestamp in ISO format
def add_timestamp(
    logger: logging.Logger, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    event_dict["timestamp"] = structlog.processors.TimeStamper(fmt="iso")(
        logger, method_name, event_dict
    )["timestamp"]
    return event_dict


def configure_logging() -> None:
    """
    Configures logging for the application using structlog.

    - In 'development' (default), logs are human-readable and colorized.
    - In 'production', logs are JSON-formatted for machine readability.
    - The logging level is set to DEBUG if the DEBUG env var is 'true'.
    """
    env = os.getenv("ENV", "development").lower()
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    log_level = logging.DEBUG if debug_mode else logging.INFO

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        add_log_level,
        add_timestamp,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
    ]

    if env == "production":
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=processors,
            foreign_pre_chain=[
                structlog.stdlib.ExtraAdder(),
            ],
        )
    else:  # Development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
        formatter = structlog.stdlib.ProcessorFormatter(
            processors=processors,
            foreign_pre_chain=[
                structlog.stdlib.ExtraAdder(),
            ],
        )

    # Configure the standard logging library
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Configure structlog
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logger = structlog.get_logger("logging_config")
    logger.info("Logging configured", env=env, debug_mode=debug_mode)
    if debug_mode:
        logger.debug("Debug mode enabled. Logging will be verbose.")


def get_agent_logger(agent_name: str) -> Any:
    """Get a configured structlog logger for an agent."""
    return structlog.get_logger(f"src.agents.{agent_name}")


if __name__ == "__main__":
    # Example of how to use this logger.
    os.environ["DEBUG"] = "true"
    # To test production logging, uncomment the following line:
    # os.environ["ENV"] = "production"

    configure_logging()

    main_logger = structlog.get_logger(__name__)

    main_logger.debug("This is a debug message.", user_id=123, request_id="abc-123")
    main_logger.info("User logged in successfully.", username="testuser")
    main_logger.warning("Disk space is running low.", free_space_mb=50)

    try:
        result = 1 / 0
    except ZeroDivisionError:
        main_logger.error("An error occurred during calculation.", exc_info=True)

    # Example of logging with context binding
    bound_logger = main_logger.bind(transaction_id="txn-987")
    bound_logger.info("Processing transaction.")
    bound_logger.info("Transaction complete.")
