"""OpenTelemetry Exporter for MACS.

Provides distributed tracing and metrics collection compatible with
Jaeger, Prometheus, DataDog, and other OpenTelemetry backends.

Usage:
    from macs_pkg.monitoring import get_monitor
    from macs_pkg.monitoring.openTelemetry_exporter import OpenTelemetryExporter

    exporter = OpenTelemetryExporter(
        service_name="macs-agent",
        otlp_endpoint="http://localhost:4317",  # gRPC
    )
    tracer = exporter.get_tracer()

    with tracer.start_as_current_span("my_task") as span:
        result = await agent.execute(task)
        span.set_attribute("task.result", str(result))
"""

from __future__ import annotations

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import time

try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.trace import Status, StatusCode
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.context import Context
    _HAS_OTEL = True
except ImportError:
    trace = None
    metrics = None
    _HAS_OTEL = False

from ..utils.logger import get_logger

logger = get_logger("openTelemetry_exporter")


class OTelExportFormat(Enum):
    """Supported OpenTelemetry export formats."""
    GRPC = "grpc"      # OTLP gRPC (preferred)
    HTTP = "http"      # OTLP HTTP
    JAEGER = "jaeger"  # Jaeger thrift (via OTLP)


@dataclass
class SpanEvent:
    """A span event for tracing."""
    name: str
    timestamp: datetime = field(default_factory=datetime.now)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricPoint:
    """A single metric data point."""
    name: str
    value: float
    labels: Dict[str, str]
    timestamp: datetime = field(default_factory=datetime.now)


class OpenTelemetryExporter:
    """OpenTelemetry exporter for MACS.

    Supports:
    - Distributed tracing (OTLP gRPC/HTTP)
    - Metrics collection (counter, gauge, histogram)
    - Span events and attributes
    - Context propagation

    Usage::

        exporter = OpenTelemetryExporter(
            service_name="macs-agent",
            otlp_endpoint="http://localhost:4317",
        )

        # Get tracer for spans
        tracer = exporter.get_tracer()

        @tracer.start_as_current_span("my_task")
        async def my_task():
            return await runtime.execute(task)

        # Or manually
        span = tracer.start_span("my_task")
        try:
            result = await runtime.execute(task)
            span.set_attribute("task.success", True)
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            span.end()
    """

    _instance: Optional["OpenTelemetryExporter"] = None

    def __init__(
        self,
        service_name: str = "macs-agent",
        service_version: str = "0.1.0",
        otlp_endpoint: str = "http://localhost:4317",
        export_format: OTelExportFormat = OTelExportFormat.GRPC,
        export_interval_ms: int = 5000,
        debug: bool = False,
    ):
        """Initialize OpenTelemetry exporter.

        Args:
            service_name: Name of this service for tracing.
            service_version: Version string for tracing.
            otlp_endpoint: OTLP collector endpoint (gRPC or HTTP).
            export_format: Export format (GRPC, HTTP, or JAEGER).
            export_interval_ms: Interval for metric exports in milliseconds.
            debug: Enable debug logging.
        """
        if not _HAS_OTEL:
            raise ImportError(
                "opentelemetry not installed. Install with:\n"
                "pip install opentelemetry-api "
                "opentelemetry-sdk "
                "opentelemetry-exporter-otlp-proto-grpc "
                "opentelemetry-exporter-otlp-proto-http"
            )

        self._service_name = service_name
        self._service_version = service_version
        self._otlp_endpoint = otlp_endpoint
        self._export_format = export_format
        self._export_interval_ms = export_interval_ms
        self._debug = debug

        self._provider: Optional[TracerProvider] = None
        self._tracer: Optional[trace.Tracer] = None
        self._meter: Optional[metrics.Meter] = None
        self._metrics: Dict[str, metrics.Counter | metrics.Histogram | metrics.Gauge] = {}
        self._lock = threading.Lock()
        self._spans: List[Dict[str, Any]] = []
        self._metric_buffer: List[MetricPoint] = []
        self._running = False

        self._setup()
        OpenTelemetryExporter._instance = self

    def _setup(self) -> None:
        """Set up OpenTelemetry tracer and meter providers."""
        # Build resource
        resource = Resource.create({
            SERVICE_NAME: self._service_name,
            "service.version": self._service_version,
            "deployment.environment": "development" if self._debug else "production",
        })

        # Set up tracer provider
        self._provider = TracerProvider(resource=resource)

        # Add OTLP exporter based on format
        try:
            if self._export_format == OTelExportFormat.GRPC:
                span_exporter = OTLPSpanExporter(
                    endpoint=self._otlp_endpoint,
                    insecure=True,
                )
            else:
                from opentelemetry.exporter.otlp.proto.http import OTLPSpanExporter as OTLPHTTPSpanExporter
                span_exporter = OTLPHTTPSpanExporter(
                    endpoint=self._otlp_endpoint,
                )

            self._provider.add_span_processor(
                BatchSpanProcessor(span_exporter)
            )
            logger.info(f"OpenTelemetry span exporter connected to {self._otlp_endpoint}")
        except Exception as e:
            logger.warning(f"Could not connect to OTLP endpoint: {e}. Tracing will be local only.")
            self._spans = []  # In-memory fallback

        # Set global tracer provider
        trace.set_tracer_provider(self._provider)

        # Get tracer
        self._tracer = trace.get_tracer(
            self._service_name,
            self._service_version,
        )

        # Set up meter provider
        try:
            metric_exporter = OTLPMetricExporter(
                endpoint=self._otlp_endpoint,
                insecure=True,
            )
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=self._export_interval_ms,
            )
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader],
            )
            metrics.set_meter_provider(meter_provider)
            self._meter = metrics.get_meter(self._service_name)
        except Exception as e:
            logger.warning(f"Could not set up metric exporter: {e}. Metrics will be local only.")
            self._meter = metrics.get_meter(self._service_name)

    @classmethod
    def get_instance(cls) -> Optional["OpenTelemetryExporter"]:
        """Get the singleton instance if initialized."""
        return cls._instance

    def get_tracer(self) -> trace.Tracer:
        """Get the OpenTelemetry tracer.

        Returns:
            The tracer for creating spans.
        """
        if self._tracer is None:
            raise RuntimeError("OpenTelemetryExporter not initialized")
        return self._tracer

    def get_meter(self) -> metrics.Meter:
        """Get the OpenTelemetry meter.

        Returns:
            The meter for creating metrics.
        """
        if self._meter is None:
            raise RuntimeError("OpenTelemetryExporter not initialized")
        return self._meter

    # ─── Span Operations ───────────────────────────────────────────────────────

    def start_span(
        self,
        name: str,
        parent_context: Optional[Context] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> trace.Span:
        """Start a new span.

        Args:
            name: Name of the span.
            parent_context: Optional parent context.
            attributes: Initial span attributes.

        Returns:
            The started span.
        """
        tracer = self.get_tracer()
        return tracer.start_span(name, context=parent_context, attributes=attributes or {})

    def record_exception(self, span: trace.Span, exception: Exception) -> None:
        """Record an exception on a span.

        Args:
            span: The span to record on.
            exception: The exception to record.
        """
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))

    def add_span_event(self, span: trace.Span, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to a span.

        Args:
            span: The span to add event to.
            name: Event name.
            attributes: Optional event attributes.
        """
        span.add_event(name, attributes=attributes or {})

    def set_span_attribute(self, span: trace.Span, key: str, value: Any) -> None:
        """Set an attribute on a span.

        Args:
            span: The span to set attribute on.
            key: Attribute key.
            value: Attribute value.
        """
        span.set_attribute(key, value)

    # ─── Metrics Operations ─────────────────────────────────────────────────────

    def create_counter(self, name: str, description: str = "", unit: str = "") -> metrics.Counter:
        """Create a counter metric.

        Args:
            name: Metric name.
            description: Metric description.
            unit: Unit of measurement.

        Returns:
            The created counter.
        """
        meter = self.get_meter()
        counter = meter.create_counter(name=name, description=description, unit=unit)
        with self._lock:
            self._metrics[name] = counter
        return counter

    def create_histogram(self, name: str, description: str = "", unit: str = "", explicit_bucket_boundaries: Optional[List[float]] = None) -> metrics.Histogram:
        """Create a histogram metric.

        Args:
            name: Metric name.
            description: Metric description.
            unit: Unit of measurement.
            explicit_bucket_boundaries: Bucket boundaries for histogram.

        Returns:
            The created histogram.
        """
        meter = self.get_meter()
        if explicit_bucket_boundaries:
            histogram = meter.create_histogram(
                name=name,
                description=description,
                unit=unit,
                explicit_bucket_boundaries=explicit_bucket_boundaries,
            )
        else:
            histogram = meter.create_histogram(name=name, description=description, unit=unit)
        with self._lock:
            self._metrics[name] = histogram
        return histogram

    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value.

        Args:
            name: Metric name.
            value: The value to record.
            labels: Optional label key-value pairs.
        """
        with self._lock:
            metric = self._metrics.get(name)
            if metric is None:
                return

        labels = labels or {}
        if isinstance(metric, metrics.Counter):
            metric.add(value, labels)
        elif isinstance(metric, metrics.Histogram):
            metric.record(value, labels)

    # ─── High-Level Helpers ────────────────────────────────────────────────────

    def record_agent_think(self, agent_name: str, duration_ms: float) -> None:
        """Record an agent think() call as a metric.

        Args:
            agent_name: Name of the agent.
            duration_ms: Duration in milliseconds.
        """
        self.record_metric(
            "macs.agent.think.duration",
            duration_ms,
            {"agent": agent_name}
        )
        self.record_metric("macs.agent.think.total", 1, {"agent": agent_name})

    def record_agent_act(self, agent_name: str, duration_ms: float) -> None:
        """Record an agent act() call as a metric.

        Args:
            agent_name: Name of the agent.
            duration_ms: Duration in milliseconds.
        """
        self.record_metric(
            "macs.agent.act.duration",
            duration_ms,
            {"agent": agent_name}
        )
        self.record_metric("macs.agent.act.total", 1, {"agent": agent_name})

    def record_task_execution(
        self,
        task_type: str,
        mode: str,
        duration_ms: float,
        success: bool,
    ) -> None:
        """Record a task execution.

        Args:
            task_type: Type of task (erp_qa, code_generation, etc).
            mode: Collaboration mode used.
            duration_ms: Total duration in milliseconds.
            success: Whether the task succeeded.
        """
        status = "success" if success else "failure"
        self.record_metric("macs.task.duration", duration_ms, {"task_type": task_type, "mode": mode})
        self.record_metric("macs.task.total", 1, {"task_type": task_type, "mode": mode, "status": status})

    def record_llm_call(
        self,
        provider: str,
        model: str,
        duration_ms: float,
        tokens_used: int,
        success: bool,
    ) -> None:
        """Record an LLM API call.

        Args:
            provider: LLM provider (minimax, claude, openai).
            model: Model name.
            duration_ms: Call duration in milliseconds.
            tokens_used: Total tokens consumed.
            success: Whether the call succeeded.
        """
        status = "success" if success else "failure"
        self.record_metric("macs.llm.duration", duration_ms, {"provider": provider, "model": model})
        self.record_metric("macs.llm.tokens", tokens_used, {"provider": provider, "model": model})
        self.record_metric("macs.llm.total", 1, {"provider": provider, "model": model, "status": status})

    def record_rag_search(self, query: str, results_count: int, duration_ms: float) -> None:
        """Record a RAG search operation.

        Args:
            query: Search query text.
            results_count: Number of results returned.
            duration_ms: Search duration in milliseconds.
        """
        self.record_metric("macs.rag.search.duration", duration_ms)
        self.record_metric("macs.rag.search.results", results_count)
        self.record_metric("macs.rag.search.total", 1)

    # ─── Context Propagation ───────────────────────────────────────────────────

    def inject_context(self, carrier: Dict[str, str]) -> Dict[str, str]:
        """Inject current trace context into a carrier dict (for cross-service propagation).

        Args:
            carrier: Dict to inject context into (e.g., HTTP headers).

        Returns:
            The carrier with injected context.
        """
        propagator = TraceContextTextMapPropagator()
        propagator.inject(carrier)
        return carrier

    def extract_context(self, carrier: Dict[str, str]) -> Context:
        """Extract trace context from a carrier dict.

        Args:
            carrier: Dict containing context (e.g., HTTP headers).

        Returns:
            The extracted context.
        """
        propagator = TraceContextTextMapPropagator()
        return propagator.extract(carrier)

    # ─── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self, timeout_ms: int = 5000) -> None:
        """Shut down the exporter gracefully.

        Args:
            timeout_ms: Timeout in milliseconds for graceful shutdown.
        """
        self._running = False
        if self._provider:
            self._provider.shutdown()
        logger.info("OpenTelemetry exporter shut down")

    def __enter__(self) -> "OpenTelemetryExporter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.shutdown()


# ─── Decorator Helpers ────────────────────────────────────────────────────────

def traced(span_name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """Decorator to automatically trace a function with OpenTelemetry.

    Usage::

        @traced("my_task")
        async def my_task():
            return await runtime.execute(task)
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            exporter = OpenTelemetryExporter.get_instance()
            if exporter is None:
                return await func(*args, **kwargs)

            tracer = exporter.get_tracer()
            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name, attributes=attributes or {}) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    exporter.record_exception(span, e)
                    span.set_attribute("success", False)
                    raise

        return wrapper
    return decorator
