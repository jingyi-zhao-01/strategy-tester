"""Observability module for logging and distributed tracing."""

from lib.observability.log import Log, configure_logging

__all__ = ["Log", "configure_logging"]
