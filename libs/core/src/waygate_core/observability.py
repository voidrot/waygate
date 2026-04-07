from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from waygate_core.settings import get_runtime_settings

_configured_service_name: str | None = None


def _build_exporter(exporter_name: str):
    normalized = exporter_name.strip().lower()
    if normalized == "console":
        return ConsoleSpanExporter()
    if normalized == "otlp":
        return OTLPSpanExporter()
    raise ValueError(f"Unsupported OTEL exporter: {exporter_name}")


def configure_tracing(service_name: str) -> bool:
    global _configured_service_name

    settings = get_runtime_settings()
    if not settings.otel_enabled:
        return False

    if _configured_service_name is not None:
        return True

    resource_attributes = {"service.name": service_name}
    if settings.otel_service_namespace:
        resource_attributes["service.namespace"] = settings.otel_service_namespace

    provider = TracerProvider(resource=Resource.create(resource_attributes))
    provider.add_span_processor(
        BatchSpanProcessor(_build_exporter(settings.otel_exporter))
    )
    trace.set_tracer_provider(provider)
    _configured_service_name = service_name
    return True


@contextmanager
def start_span(
    name: str,
    *,
    tracer_name: str,
    attributes: dict[str, Any] | None = None,
):
    tracer = trace.get_tracer(tracer_name)
    with tracer.start_as_current_span(name) as span:
        for key, value in (attributes or {}).items():
            if value is not None:
                span.set_attribute(key, value)
        yield span
