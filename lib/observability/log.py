import atexit
import contextlib
import logging

from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


class _LoggerState:
    """Internal state holder to avoid global statement usage."""

    _otel_logger_provider: LoggerProvider | None = None
    _logger: logging.Logger | None = None
    _otel_handler: LoggingHandler | None = None

    @classmethod
    def set_providers(
        cls,
        logger: logging.Logger | None,
        otel_provider: LoggerProvider | None = None,
        otel_handler: LoggingHandler | None = None,
    ) -> None:
        """Set both logger and OTEL provider."""
        cls._logger = logger
        cls._otel_logger_provider = otel_provider
        cls._otel_handler = otel_handler

    @classmethod
    def get_logger(cls) -> logging.Logger | None:
        """Get the configured logger."""
        return cls._logger

    @classmethod
    def get_otel_provider(cls) -> LoggerProvider | None:
        """Get the configured OTEL provider."""
        return cls._otel_logger_provider

    @classmethod
    def get_otel_handler(cls) -> LoggingHandler | None:
        """Get the configured OTEL handler."""
        return cls._otel_handler


def _shutdown_otel():
    """Gracefully shutdown OpenTelemetry logger provider before Python shutdown."""
    provider = _LoggerState.get_otel_provider()
    handler = _LoggerState.get_otel_handler()
    logger = _LoggerState.get_logger()

    # Remove the OTEL handler from logger to prevent threading issues during shutdown
    if logger and handler and handler in logger.handlers:
        logger.removeHandler(handler)

    if provider is not None:
        with contextlib.suppress(Exception):
            # Force flush without creating new threads during shutdown
            provider.force_flush(timeout_millis=1000)  # Shorter timeout
            # Don't call shutdown() as it may create threads during interpreter shutdown


# Monkey patch the LoggingHandler.flush to prevent threading during shutdown
_original_flush = None


def _safe_flush(self):
    """Safe flush that doesn't create threads during shutdown."""
    try:
        if _original_flush:
            _original_flush(self)
    except RuntimeError as e:
        if "can't create new thread at interpreter shutdown" in str(e):
            # Silently ignore threading errors during shutdown
            pass
        else:
            raise


# Patch the flush method to be safe during shutdown
try:
    from opentelemetry.sdk._logs._internal import LoggingHandler

    _original_flush = LoggingHandler.flush
    LoggingHandler.flush = _safe_flush
except ImportError:
    pass


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

        # Add file handler to root logger
    root_logger = logging.getLogger()
    file_handler = logging.FileHandler("/home/jingyi/PycharmProjects/strategy-tester/app.log")
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    otel_provider = None
    otel_handler: LoggingHandler | None = None

    # Configure OpenTelemetry if enabled
    if enable_otel:
        try:
            resource = Resource(attributes={SERVICE_NAME: service_name})
            otel_provider = LoggerProvider(resource=resource)
            # Use HTTP/protobuf protocol for OTLP
            otlp_exporter = OTLPLogExporter()
            otel_provider.add_log_record_processor(
                BatchLogRecordProcessor(
                    otlp_exporter,
                    max_queue_size=2048,
                    schedule_delay_millis=5000,  # Export every 5 seconds
                )
            )

            # Add OTEL logging handler to bridge Python logging to OTEL
            otel_handler = LoggingHandler(level=log_level, logger_provider=otel_provider)
            logger.addHandler(otel_handler)

            # Register shutdown handler to run before Python's logging shutdown
            atexit.register(_shutdown_otel)
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")

    # Store in state holder instead of using global
    _LoggerState.set_providers(logger, otel_provider, otel_handler if enable_otel else None)

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

    @staticmethod
    def debug(msg: str, *args, **kwargs) -> None:
        """Log debug level message."""
        logger = _LoggerState.get_logger()
        if logger is not None:
            logger.debug(msg, *args, stacklevel=2, **kwargs)

    @staticmethod
    def log_db_connection_pool_stats(
        active_conns: int | str,
        min_size: int | str,
        max_size: int | str,
    ) -> None:
        """Log database connection pool statistics.

        Args:
        ----
            active_conns: Number of active connections.
            min_size: Minimum pool size.
            max_size: Maximum pool size.

        """
        Log.info(
            f"Database pool stats - Active: {active_conns}, " f"Min: {min_size}, Max: {max_size}"
        )
