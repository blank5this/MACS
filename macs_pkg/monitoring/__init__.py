"""MACS Monitoring — event bus, metrics, and system monitor."""

from typing import Optional

from .event_bus import Event, EventBus, EventType, get_event_bus, reset_event_bus
from .metrics import Counter, Gauge, Histogram, MetricsStore
from .monitor import SystemMonitor, get_monitor, reset_monitor
from .self_correction_logger import SelfCorrectionLogger

_self_correction_logger: Optional[SelfCorrectionLogger] = None

def get_correction_logger() -> SelfCorrectionLogger:
    global _self_correction_logger
    if _self_correction_logger is None:
        _self_correction_logger = SelfCorrectionLogger()
        _self_correction_logger.attach()
    return _self_correction_logger

try:
    from .prometheus_exporter import PrometheusExporter
    _has_prometheus = True
except ImportError:
    _has_prometheus = False
    PrometheusExporter = None

try:
    from .openTelemetry_exporter import OpenTelemetryExporter
    _has_otel = True
except ImportError:
    _has_otel = False
    OpenTelemetryExporter = None

__all__ = [
    "Event", "EventBus", "EventType", "get_event_bus", "reset_event_bus",
    "Counter", "Gauge", "Histogram", "MetricsStore",
    "SystemMonitor", "get_monitor", "reset_monitor",
    "SelfCorrectionLogger", "get_correction_logger",
]
if _has_prometheus:
    __all__.append("PrometheusExporter")
if _has_otel:
    __all__.append("OpenTelemetryExporter")
