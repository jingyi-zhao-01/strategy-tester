import logging
import os
import subprocess
import sys

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# List of OTEL environment variables to set
otel_env_vars = [
    "OTEL_RESOURCE_ATTRIBUTES",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_PROTOCOL",
]

# Prepare environment for subprocess
env = os.environ.copy()

# Build the command to run lambda_handler.py with opentelemetry-instrument
cmd = [
    "opentelemetry-instrument",
    sys.executable,
    os.path.join(os.path.dirname(__file__), "lambda_handler.py"),
]

# Run the command with the loaded environment
subprocess.run(cmd, env=env, check=False)

# Ensure log handlers are flushed and closed to avoid shutdown errors

logging.shutdown()
