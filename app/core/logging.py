import logging
import logging.config

import structlog


def configure_logging(debug: bool = False) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structlog": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processor": structlog.processors.JSONRenderer(),
                    "foreign_pre_chain": [
                        structlog.stdlib.add_log_level,
                        timestamper,
                    ],
                },
            },
            "handlers": {
                "default": {
                    "level": "DEBUG" if debug else "INFO",
                    "class": "logging.StreamHandler",
                    "formatter": "structlog",
                },
            },
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": "DEBUG" if debug else "INFO",
                },
            },
        }
    )

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG if debug else logging.INFO),
        cache_logger_on_first_use=True,
    )

