"""Observability module for logging and distributed tracing."""

import os

from dotenv import load_dotenv

from lib.observability.log import Log, configure_logging

# Load environment variables from .env file for project-specific configuration
load_dotenv()

# Auto-initialize logging if service name is provided
_service_name = os.getenv("GRAFANA_SERVICE_NAME")
if _service_name:
    configure_logging(service_name=_service_name)

__all__ = ["Log", "configure_logging"]
