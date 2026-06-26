"""OpenTelemetry helpers for ingestion microservices."""

import logging
import os
from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from threading import Lock
from urllib.parse import parse_qsl

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import Span, SpanLimits, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind

_TRACE_LOCK = Lock()
_TRACE_READY = False
_TRACER_NAME = "strategy-tester"
_SERVICE_NAME: ContextVar[str] = ContextVar("strategy_tester_service_name", default="-")


class TraceContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.service_name = _SERVICE_NAME.get()
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            record.trace_id = format(span_context.trace_id, "032x")
            record.span_id = format(span_context.span_id, "016x")
        else:
            record.trace_id = "-"
            record.span_id = "-"
        return True


def configure_service_logger(service_name: str) -> logging.Logger:
    _SERVICE_NAME.set(service_name)
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format=(
            "%(asctime)s %(levelname)s service=%(service_name)s %(name)s trace_id=%(trace_id)s "
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
        resource_attributes: dict[str, str] = {"service.name": service_name}
        deployment_environment = os.getenv("DD_ENV", "").strip()
        service_version = os.getenv("DD_VERSION", "").strip()
        if deployment_environment:
            resource_attributes["deployment.environment"] = deployment_environment
        if service_version:
            resource_attributes["service.version"] = service_version
        resource = Resource.create(resource_attributes)
        provider = TracerProvider(
            resource=resource,
            span_limits=SpanLimits(
                max_attributes=int(os.getenv("OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT", "32")),
                max_events=int(os.getenv("OTEL_SPAN_EVENT_COUNT_LIMIT", "8")),
                max_attribute_length=int(
                    os.getenv("OTEL_SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT", "256")
                ),
            ),
        )
        exporter = _build_otlp_exporter()
        if exporter is not None:
            provider.add_span_processor(_build_span_processor(exporter))
        trace.set_tracer_provider(provider)
        _TRACE_READY = True


def shutdown_tracing() -> None:
    provider = trace.get_tracer_provider()
    force_flush = getattr(provider, "force_flush", None)
    if callable(force_flush):
        force_flush()

    shutdown = getattr(provider, "shutdown", None)
    if callable(shutdown):
        shutdown()


def start_span(
    name: str,
    *,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Mapping[str, object] | None = None,
) -> AbstractContextManager[trace.Span]:
    tracer = trace.get_tracer(_TRACER_NAME)
    return tracer.start_as_current_span(
        name,
        kind=kind,
        attributes=attributes,
        record_exception=False,
    )


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


def annotate_span_error(span: Span, exc: BaseException) -> None:
    span.set_attribute("error", True)
    span.set_attribute("error.type", type(exc).__name__)
    message = str(exc).strip()
    if message:
        span.set_attribute("error.message", message)


def _build_otlp_exporter() -> OTLPSpanExporter | None:
    protocol = os.getenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf").strip()
    if protocol and protocol != "http/protobuf":
        logging.getLogger(__name__).warning(
            "Unsupported OTEL protocol=%s for strategy-tester; expected http/protobuf",
            protocol,
        )
        return None

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "").strip()
    if not endpoint:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return None

    timeout = float(os.getenv("OTEL_EXPORTER_OTLP_TIMEOUT", "10"))
    return OTLPSpanExporter(
        endpoint=endpoint,
        headers=_parse_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")) or None,
        timeout=timeout,
    )


def _build_span_processor(exporter: OTLPSpanExporter) -> BatchSpanProcessor:
    return BatchSpanProcessor(
        exporter,
        max_queue_size=int(os.getenv("OTEL_BSP_MAX_QUEUE_SIZE", "2048")),
        max_export_batch_size=int(os.getenv("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", "128")),
        schedule_delay_millis=int(os.getenv("OTEL_BSP_SCHEDULE_DELAY", "2000")),
        export_timeout_millis=int(os.getenv("OTEL_BSP_EXPORT_TIMEOUT", "5000")),
    )


def _parse_headers(raw_headers: str) -> dict[str, str]:
    return dict(
        parse_qsl(
            raw_headers,
            separator=",",
            keep_blank_values=True,
        )
    )
