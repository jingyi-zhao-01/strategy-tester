import atexit
import logging
import pathlib

from dotenv import load_dotenv
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("strategy-tester")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Set up OpenTelemetry logging with structured fields
resource = Resource(attributes={SERVICE_NAME: "strategy-tester"})
otel_logger_provider = LoggerProvider(resource=resource)
otlp_exporter = OTLPLogExporter()
otel_logger_provider.add_log_record_processor(
    BatchLogRecordProcessor(
        otlp_exporter,
        max_queue_size=2048,
        schedule_delay_millis=5000,  # Export every 5 seconds
    )
)


def _shutdown_otel():
    """Gracefully shutdown OpenTelemetry logger provider before Python shutdown."""
    try:
        otel_logger_provider.force_flush(timeout_millis=5000)
        otel_logger_provider.shutdown()
    except Exception:
        pass  # Silently ignore errors during shutdown


# Register shutdown handler to run before Python's logging shutdown
atexit.register(_shutdown_otel)

# Ensure /log directory exists and use absolute path for log file
project_root = pathlib.Path(__file__).parent.parent.resolve()
log_dir = project_root / "log"
log_dir.mkdir(exist_ok=True)
log_file_path = log_dir / "app.log"

# Add file handler if not already present
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    file_handler = logging.FileHandler(str(log_file_path))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Add console handler if not already present
if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


class Log:
    @staticmethod
    def info(msg, *args, **kwargs):
        logger.info(msg, *args, stacklevel=2, **kwargs)

    @staticmethod
    def warn(msg, *args, **kwargs):
        logger.warning(msg, *args, stacklevel=2, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        logger.error(msg, *args, stacklevel=2, **kwargs)
