"""OpenTelemetry helpers for ingestion microservices."""

import logging
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from threading import Lock
from urllib.parse import parse_qsl

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind

_TRACE_LOCK = Lock()
_TRACE_READY = False
_TRACER_NAME = "strategy-tester"


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            record.trace_id = format(span_context.trace_id, "032x")
            record.span_id = format(span_context.span_id, "016x")
        else:
            record.trace_id = "-"
            record.span_id = "-"
        return True


def configure_service_logger(service_name: str) -> logging.Logger:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format=(
            "%(asctime)s %(levelname)s %(name)s trace_id=%(trace_id)s "
            "span_id=%(span_id)s %(message)s"
        ),
    )
    _install_trace_filter()
    return logging.getLogger(service_name)


def initialize_tracing(service_name: str) -> None:
    global _TRACE_READY
    with _TRACE_LOCK:
        if _TRACE_READY:
            return
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
        if endpoint:
            headers = dict(
                parse_qsl(
                    os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""),
                    separator=",",
                    keep_blank_values=True,
                )
            )
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        endpoint=endpoint,
                        headers=headers or None,
                    )
                )
            )
        trace.set_tracer_provider(provider)
        _TRACE_READY = True


def start_span(
    name: str,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Mapping[str, object] | None = None,
) -> Iterator[trace.Span]:
    tracer = trace.get_tracer(_TRACER_NAME)
    return tracer.start_as_current_span(name, kind=kind, attributes=attributes)


@contextmanager
def start_span_sync(
    name: str,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Mapping[str, object] | None = None,
) -> Iterator[trace.Span]:
    with start_span(name, kind=kind, attributes=attributes) as span:
        yield span


def _install_trace_filter() -> None:
    root = logging.getLogger()
    for handler in root.handlers:
        if not any(isinstance(f, TraceContextFilter) for f in handler.filters):
            handler.addFilter(TraceContextFilter())
