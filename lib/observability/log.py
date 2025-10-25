import atexit
import logging

from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


class _LoggerState:
    """Internal state holder to avoid global statement usage."""

    _otel_logger_provider: LoggerProvider | None = None
    _logger: logging.Logger | None = None

    @classmethod
    def set_providers(
        cls, logger: logging.Logger, otel_provider: LoggerProvider | None = None
    ) -> None:
        """Set both logger and OTEL provider."""
        cls._logger = logger
        cls._otel_logger_provider = otel_provider

    @classmethod
    def get_logger(cls) -> logging.Logger | None:
        """Get the configured logger."""
        return cls._logger

    @classmethod
    def get_otel_provider(cls) -> LoggerProvider | None:
        """Get the configured OTEL provider."""
        return cls._otel_logger_provider


def _shutdown_otel():
    """Gracefully shutdown OpenTelemetry logger provider before Python shutdown."""
    provider = _LoggerState.get_otel_provider()
    if provider is not None:
        try:
            provider.force_flush(timeout_millis=5000)
            provider.shutdown()
        except Exception:
            pass  # Silently ignore errors during shutdown


def configure_logging(
    service_name: str,
    log_level: int = logging.INFO,
    enable_otel: bool = True,
    log_format: str = "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    date_format: str = "%Y-%m-%d %H:%M:%S",
) -> logging.Logger:
    """Configure and initialize the logger with optional OpenTelemetry integration.

    Args:
    ----
        service_name: Name of the service (used for logging and OTEL resource).
        log_level: Logging level (default: logging.INFO).
        enable_otel: Enable OpenTelemetry log export (default: True).
        log_format: Format string for log messages.
        date_format: Format string for dates in logs.

    Returns:
    -------
        Configured logger instance.

    """
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # Create logger for this service
    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)
    logger.propagate = False  # Prevent propagation to root logger

    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Add console handler if not already present
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    otel_provider = None

    # Configure OpenTelemetry if enabled
    if enable_otel:
        try:
            resource = Resource(attributes={SERVICE_NAME: service_name})
            otel_provider = LoggerProvider(resource=resource)
            otlp_exporter = OTLPLogExporter()
            otel_provider.add_log_record_processor(
                BatchLogRecordProcessor(
                    otlp_exporter,
                    max_queue_size=2048,
                    schedule_delay_millis=5000,  # Export every 5 seconds
                )
            )
            # Register shutdown handler to run before Python's logging shutdown
            atexit.register(_shutdown_otel)
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")

    # Store in state holder instead of using global
    _LoggerState.set_providers(logger, otel_provider)

    return logger


class Log:
    """Wrapper for logging with the configured logger instance."""

    @staticmethod
    def info(msg: str, *args, **kwargs) -> None:
        """Log info level message."""
        logger = _LoggerState.get_logger()
        if logger is not None:
            logger.info(msg, *args, stacklevel=2, **kwargs)

    @staticmethod
    def warn(msg: str, *args, **kwargs) -> None:
        """Log warning level message."""
        logger = _LoggerState.get_logger()
        if logger is not None:
            logger.warning(msg, *args, stacklevel=2, **kwargs)

    @staticmethod
    def error(msg: str, *args, **kwargs) -> None:
        """Log error level message."""
        logger = _LoggerState.get_logger()
        if logger is not None:
            logger.error(msg, *args, stacklevel=2, **kwargs)
