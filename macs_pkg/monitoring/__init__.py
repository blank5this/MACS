"""MACS Monitoring — event bus, metrics, and system monitor."""

from .event_bus import Event, EventBus, EventType, get_event_bus, reset_event_bus
from .metrics import Counter, Gauge, Histogram, MetricsStore
from .monitor import SystemMonitor, get_monitor, reset_monitor

try:
    from .prometheus_exporter import PrometheusExporter
    _has_prometheus = True
except ImportError:
    _has_prometheus = False
    PrometheusExporter = None

__all__ = [
    "Event", "EventBus", "EventType", "get_event_bus", "reset_event_bus",
    "Counter", "Gauge", "Histogram", "MetricsStore",
    "SystemMonitor", "get_monitor", "reset_monitor",
]
if _has_prometheus:
    __all__.append("PrometheusExporter")
