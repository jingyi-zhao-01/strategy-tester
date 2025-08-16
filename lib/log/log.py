import logging

# import os
import pathlib

from dotenv import load_dotenv

# from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
# from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
# from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
# from opentelemetry.sdk.resources import Resource

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("strategy-tester")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

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


# TODO: Implement OpenTelemetry logging


# # OpenTelemetry logger setup using gRPC OTLPLogExporter and ConsoleLogExporter
# otel_logger_provider = LoggerProvider(
#     resource=Resource.create(
#         {"service.name": os.getenv("OTEL_RESOURCE_ATTRIBUTES", "strategy-tester")}
#     )
# )
# otel_log_exporter = OTLPLogExporter(
#     endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
#     headers=os.getenv("OTEL_EXPORTER_OTLP_HEADERS"),
#     # insecure=True
# )
# otel_logger_provider.add_log_record_processor(BatchLogRecordProcessor(otel_log_exporter))
# otel_logger_provider.add_log_record_processor(BatchLogRecordProcessor(ConsoleLogExporter()))

# # Attach OpenTelemetry LoggingHandler to the standard logger
# otel_handler = LoggingHandler(level=logging.INFO, logger_provider=otel_logger_provider)
# logger.addHandler(otel_handler)


class Log:
    @staticmethod
    def info(msg, *args, **kwargs):
        logger.info(msg, *args, **kwargs)

    @staticmethod
    def warn(msg, *args, **kwargs):
        logger.warning(msg, *args, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        logger.error(msg, *args, **kwargs)
