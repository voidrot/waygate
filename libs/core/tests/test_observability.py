from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from waygate_core import observability


def test_configure_tracing_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setattr(observability, "_configured_service_name", None)
    monkeypatch.setattr(
        observability,
        "get_runtime_settings",
        lambda: SimpleNamespace(
            otel_enabled=False,
            otel_exporter="console",
            otel_service_namespace="waygate",
        ),
    )

    assert observability.configure_tracing("waygate-receiver") is False


def test_configure_tracing_builds_provider_for_supported_exporters(
    monkeypatch,
) -> None:
    monkeypatch.setattr(observability, "_configured_service_name", None)
    monkeypatch.setattr(
        observability,
        "get_runtime_settings",
        lambda: SimpleNamespace(
            otel_enabled=True,
            otel_exporter="console",
            otel_service_namespace="waygate",
        ),
    )

    created = {}

    class FakeProvider:
        def __init__(self, resource) -> None:
            created["resource"] = resource
            created["processors"] = []

        def add_span_processor(self, processor) -> None:
            created["processors"].append(processor)

    monkeypatch.setattr(observability, "TracerProvider", FakeProvider)
    monkeypatch.setattr(observability, "ConsoleSpanExporter", lambda: "console")
    monkeypatch.setattr(
        observability,
        "BatchSpanProcessor",
        lambda exporter: {"exporter": exporter},
    )

    provider_calls = []
    monkeypatch.setattr(
        observability.trace,
        "set_tracer_provider",
        lambda provider: provider_calls.append(provider),
    )

    assert observability.configure_tracing("waygate-compiler") is True
    assert provider_calls
    assert created["processors"] == [{"exporter": "console"}]
    assert created["resource"].attributes["service.name"] == "waygate-compiler"
    assert created["resource"].attributes["service.namespace"] == "waygate"


def test_start_span_sets_attributes(monkeypatch) -> None:
    observed = []

    class FakeSpan:
        def set_attribute(self, key: str, value: object) -> None:
            observed.append((key, value))

    @contextmanager
    def fake_current_span(_name: str):
        yield FakeSpan()

    class FakeTracer:
        def start_as_current_span(self, name: str):
            return fake_current_span(name)

    monkeypatch.setattr(observability.trace, "get_tracer", lambda _name: FakeTracer())

    with observability.start_span(
        "receiver.enqueue_documents",
        tracer_name="tests",
        attributes={
            "waygate.trace_id": "trace-1",
            "waygate.document_count": 2,
            "waygate.null_attr": None,
        },
    ):
        pass

    assert observed == [
        ("waygate.trace_id", "trace-1"),
        ("waygate.document_count", 2),
    ]
