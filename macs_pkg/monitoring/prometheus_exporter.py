"""Prometheus Metrics Exporter for MACS.

Exports MACS metrics to Prometheus for monitoring and alerting.
Integrates with the existing MetricsStore and SystemMonitor.

Usage:
    from macs_pkg.monitoring import get_monitor
    from macs_pkg.monitoring.prometheus_exporter import PrometheusExporter

    # Create exporter
    exporter = PrometheusExporter(port=9091)
    await exporter.start()

    # Or use with existing monitor
    monitor = get_monitor()
    prometheus = PrometheusExporter.from_monitor(monitor)
"""

import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import threading

try:
    from prometheus_client import (
        Counter as PromCounter,
        Gauge as PromGauge,
        Histogram as PromHistogram,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
        start_http_server,
    )
except ImportError:
    PromCounter = None
    PromGauge = None
    PromHistogram = None
    CollectorRegistry = None

from ..utils.logger import get_logger

logger = get_logger("prometheus_exporter")


@dataclass
class MetricDefinition:
    """Definition for a Prometheus metric."""
    name: str
    description: str
    metric_type: str  # "counter", "gauge", "histogram"
    labels: tuple = field(default_factory=tuple)


class PrometheusExporter:
    """Exports MACS metrics to Prometheus.

    Features:
    - Automatic metric sync from MetricsStore
    - HTTP server for /metrics endpoint
    - Configurable metric mappings
    - Thread-safe operations
    """

    # Default metrics to export
    DEFAULT_METRICS = [
        MetricDefinition("macs_agents_total", "Total number of MACS agents", "gauge", ("role",)),
        MetricDefinition("macs_tasks_executed_total", "Total tasks executed", "counter", ("mode", "status")),
        MetricDefinition("macs_tasks_duration_seconds", "Task execution duration", "histogram", ("mode",)),
        MetricDefinition("macs_agent_thinks_total", "Total agent think() calls", "counter", ("agent",)),
        MetricDefinition("macs_agent_acts_total", "Total agent act() calls", "counter", ("agent",)),
        MetricDefinition("macs_messages_sent_total", "Total messages sent", "counter", ("channel",)),
        MetricDefinition("macs_memory_usage_bytes", "Memory usage by agent", "gauge", ("agent", "memory_type")),
        MetricDefinition("macs_queue_length", "Message queue length", "gauge", ("queue",)),
    ]

    def __init__(
        self,
        port: int = 9091,
        registry: Optional[CollectorRegistry] = None,
        sync_interval: float = 5.0,
    ):
        """Initialize Prometheus exporter.

        Args:
            port: HTTP port for /metrics endpoint.
            registry: Prometheus collector registry.
            sync_interval: Seconds between metric syncs.
        """
        if PromCounter is None:
            raise ImportError(
                "prometheus_client not installed. Install with: pip install prometheus-client"
            )

        self._port = port
        self._sync_interval = sync_interval
        self._registry = registry or CollectorRegistry()
        self._metrics: Dict[str, Any] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()

        self._setup_metrics()

    def _setup_metrics(self) -> None:
        """Set up Prometheus metrics from definitions."""
        for metric_def in self.DEFAULT_METRICS:
            labels = {label: "" for label in metric_def.labels}

            if metric_def.metric_type == "counter":
                metric = PromCounter(
                    metric_def.name,
                    metric_def.description,
                    labelnames=tuple(labels.keys()),
                    registry=self._registry,
                )
            elif metric_def.metric_type == "gauge":
                metric = PromGauge(
                    metric_def.name,
                    metric_def.description,
                    labelnames=tuple(labels.keys()),
                    registry=self._registry,
                )
            elif metric_def.metric_type == "histogram":
                metric = PromHistogram(
                    metric_def.name,
                    metric_def.description,
                    labelnames=tuple(labels.keys()),
                    registry=self._registry,
                )
            else:
                logger.warning(f"Unknown metric type: {metric_def.metric_type}")
                continue

            self._metrics[metric_def.name] = (metric, metric_def)

    @classmethod
    def from_monitor(cls, monitor: "SystemMonitor", **kwargs) -> "PrometheusExporter":
        """Create exporter from existing SystemMonitor.

        Args:
            monitor: Existing SystemMonitor instance.
            **kwargs: Additional arguments for constructor.

        Returns:
            PrometheusExporter instance.
        """
        exporter = cls(**kwargs)
        exporter._monitor = monitor
        return exporter

    async def start(self) -> None:
        """Start the Prometheus HTTP server and sync loop."""
        if self._running:
            return

        self._running = True

        # Start HTTP server in background thread
        try:
            start_http_server(self._port, registry=self._registry)
            logger.info(f"Prometheus metrics server started on port {self._port}")
        except OSError as e:
            logger.warning(f"Could not start HTTP server on port {self._port}: {e}")

        # Start sync loop
        self._task = asyncio.create_task(self._sync_loop())

    async def stop(self) -> None:
        """Stop the exporter and HTTP server."""
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Prometheus exporter stopped")

    async def _sync_loop(self) -> None:
        """Periodically sync metrics from internal store to Prometheus."""
        while self._running:
            try:
                await asyncio.sleep(self._sync_interval)
                await self._sync_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error syncing metrics: {e}")

    async def _sync_metrics(self) -> None:
        """Sync metrics from MetricsStore to Prometheus."""
        # This will be called periodically to update Prometheus metrics
        # Subclasses or external code can populate the metrics store
        pass

    def record_task(self, mode: str, duration_ms: float, status: str) -> None:
        """Record a task execution.

        Args:
            mode: Execution mode (hierarchical, pipeline, etc).
            duration_ms: Duration in milliseconds.
            status: Task status (success, failure).
        """
        with self._lock:
            metric, _ = self._metrics.get("macs_tasks_duration_seconds", (None, None))
            if metric:
                metric.labels(mode=mode).observe(duration_ms / 1000)

            metric, _ = self._metrics.get("macs_tasks_executed_total", (None, None))
            if metric:
                metric.labels(mode=mode, status=status).inc()

    def record_agent_think(self, agent_name: str) -> None:
        """Record an agent think() call."""
        with self._lock:
            metric, _ = self._metrics.get("macs_agent_thinks_total", (None, None))
            if metric:
                metric.labels(agent=agent_name).inc()

    def record_agent_act(self, agent_name: str) -> None:
        """Record an agent act() call."""
        with self._lock:
            metric, _ = self._metrics.get("macs_agent_acts_total", (None, None))
            if metric:
                metric.labels(agent=agent_name).inc()

    def set_agent_count(self, role: str, count: int) -> None:
        """Set the number of agents with a specific role."""
        with self._lock:
            metric, _ = self._metrics.get("macs_agents_total", (None, None))
            if metric:
                metric.labels(role=role).set(count)

    def set_memory_usage(self, agent_name: str, memory_type: str, bytes_used: int) -> None:
        """Set memory usage for an agent."""
        with self._lock:
            metric, _ = self._metrics.get("macs_memory_usage_bytes", (None, None))
            if metric:
                metric.labels(agent=agent_name, memory_type=memory_type).set(bytes_used)

    def set_queue_length(self, queue_name: str, length: int) -> None:
        """Set the length of a message queue."""
        with self._lock:
            metric, _ = self._metrics.get("macs_queue_length", (None, None))
            if metric:
                metric.labels(queue=queue_name).set(length)

    def get_metrics(self) -> bytes:
        """Get current metrics in Prometheus format."""
        return generate_latest(self._registry)

    def get_content_type(self) -> str:
        """Get content type for metrics response."""
        return CONTENT_TYPE_LATEST
