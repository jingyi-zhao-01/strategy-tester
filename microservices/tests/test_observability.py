from opentelemetry import trace

from microservices.shared.observability import (
    _build_otlp_exporter,
    _build_span_processor,
    _parse_headers,
    initialize_tracing,
)


def test_build_otlp_exporter_uses_trace_specific_endpoint(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", "https://example.com/v1/traces")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://example.com/otlp")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Basic abc123")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_TIMEOUT", "7")

    exporter = _build_otlp_exporter()

    assert exporter is not None
    assert exporter._endpoint == "https://example.com/v1/traces"
    assert exporter._headers["Authorization"] == "Basic abc123"
    assert exporter._timeout == 7.0


def test_build_otlp_exporter_rejects_unsupported_protocol(monkeypatch):
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "grpc")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://example.com:4317")

    assert _build_otlp_exporter() is None


def test_parse_headers_handles_repo_standard_separator():
    assert _parse_headers("Authorization=Basic abc123,X-Scope-OrgID=tenant") == {
        "Authorization": "Basic abc123",
        "X-Scope-OrgID": "tenant",
    }


def test_initialize_tracing_adds_datadog_resource_attributes(monkeypatch):
    monkeypatch.setenv("DD_ENV", "prod")
    monkeypatch.setenv("DD_VERSION", "1.2.3")

    from microservices.shared import observability

    observability._TRACE_READY = False
    initialize_tracing("snapshot-ingestor")

    provider = trace.get_tracer_provider()
    resource_attributes = provider.resource.attributes

    assert resource_attributes["service.name"] == "snapshot-ingestor"
    assert resource_attributes["deployment.environment"] == "prod"
    assert resource_attributes["service.version"] == "1.2.3"


def test_build_span_processor_uses_repo_defaults(monkeypatch):
    monkeypatch.delenv("OTEL_BSP_MAX_QUEUE_SIZE", raising=False)
    monkeypatch.delenv("OTEL_BSP_MAX_EXPORT_BATCH_SIZE", raising=False)
    monkeypatch.delenv("OTEL_BSP_SCHEDULE_DELAY", raising=False)
    monkeypatch.delenv("OTEL_BSP_EXPORT_TIMEOUT", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://example.com/v1/traces")

    exporter = _build_otlp_exporter()
    processor = _build_span_processor(exporter)

    batch_processor = processor._batch_processor

    assert batch_processor._max_queue_size == 2048
    assert batch_processor._max_export_batch_size == 128
    assert batch_processor._schedule_delay_millis == 2000
    assert batch_processor._export_timeout_millis == 5000
