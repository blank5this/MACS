"""System monitor — wires the event bus to the metrics store."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Optional

from .event_bus import Event, EventBus, EventType, get_event_bus
from .metrics import MetricsStore


class SystemMonitor:
    """Subscribes to the EventBus and updates MetricsStore.

    Also provides a simple text report for console output.

    Usage::

        monitor = SystemMonitor()
        monitor.attach(event_bus)          # start listening

        # ... run your tasks ...

        print(monitor.report())            # human-readable summary
        metrics = monitor.metrics.summary()  # dict for programmatic use
    """

    def __init__(self, metrics: Optional[MetricsStore] = None):
        self.metrics = metrics or MetricsStore()
        self._task_start_times: Dict[str, float] = {}

    def attach(self, bus: Optional[EventBus] = None) -> None:
        """Start listening to an event bus.

        Args:
            bus: EventBus instance. Defaults to the global event bus.
        """
        if bus is None:
            bus = get_event_bus()
        bus.subscribe(self._handle_event)

    async def _handle_event(self, event: Event) -> None:
        """Route incoming events to metric updates."""
        t = event.type

        if t == EventType.TASK_STARTED:
            self.metrics.record_task_start()
            task_id = event.data.get("task_id", event.source)
            self._task_start_times[task_id] = time.monotonic()

        elif t == EventType.TASK_COMPLETED:
            task_id = event.data.get("task_id", event.source)
            mode = event.data.get("mode", "unknown")
            started = self._task_start_times.pop(task_id, None)
            duration = time.monotonic() - started if started else 0.0
            self.metrics.record_task_complete(mode, duration)

        elif t == EventType.TASK_FAILED:
            task_id = event.data.get("task_id", event.source)
            mode = event.data.get("mode", "unknown")
            self._task_start_times.pop(task_id, None)
            self.metrics.record_task_failure(mode)

        elif t == EventType.LLM_CALL_COMPLETED:
            self.metrics.record_llm_call(
                duration_s=event.data.get("duration_s", 0.0),
                input_tokens=event.data.get("input_tokens", 0),
                output_tokens=event.data.get("output_tokens", 0),
                cache_hits=event.data.get("cache_read_input_tokens", 0),
            )

        elif t == EventType.TOOL_RESULT:
            self.metrics.record_tool_call(
                tool_name=event.data.get("tool", "unknown"),
                success=event.data.get("success", True),
            )

        elif t == EventType.MESSAGE_SENT:
            self.metrics.messages_sent.inc()

        elif t == EventType.MESSAGE_DROPPED:
            self.metrics.messages_dropped.inc()

    def report(self) -> str:
        """Return a formatted text report of current metrics."""
        s = self.metrics.summary()
        lines = [
            "=" * 55,
            "  MACS System Metrics",
            f"  Uptime: {s['uptime_s']}s",
            "=" * 55,
            "",
            "Tasks:",
            f"  Started:    {s['tasks']['started']}",
            f"  Completed:  {s['tasks']['completed']}",
            f"  Failed:     {s['tasks']['failed']}",
            f"  In-flight:  {s['tasks']['in_flight']}",
        ]

        if s["collaboration_modes"]:
            lines += ["", "Collaboration Modes:"]
            for mode, stats in s["collaboration_modes"].items():
                lines.append(
                    f"  {mode}: {stats['success']}/{stats['total']} ok "
                    f"({stats['success_rate']*100:.0f}%)"
                )

        if s["agents"]:
            lines += ["", "Agent Latency (think):"]
            for agent, lat in s["agents"].items():
                lines.append(
                    f"  {agent}: avg={lat['avg_s']}s  "
                    f"min={lat['min_s']}s  max={lat['max_s']}s  n={lat['count']}"
                )

        llm = s["llm"]
        if llm["calls"] > 0:
            lines += [
                "",
                "LLM Usage:",
                f"  Calls:         {llm['calls']}",
                f"  Input tokens:  {llm['input_tokens']}",
                f"  Output tokens: {llm['output_tokens']}",
                f"  Cache hits:    {llm['cache_hits']}",
                f"  Avg latency:   {llm['latency']['avg_s']}s",
            ]

        if s["tools"]:
            lines += ["", "Tool Invocations:"]
            for tool_name, stats in s["tools"].items():
                lines.append(
                    f"  {tool_name}: {stats['calls']} calls, {stats['errors']} errors"
                )

        lines += ["", "Messages:",
                  f"  Sent:    {s['messages']['sent']}",
                  f"  Dropped: {s['messages']['dropped']}",
                  "=" * 55]

        return "\n".join(lines)


# Module-level convenience monitor
_default_monitor: Optional[SystemMonitor] = None


def get_monitor() -> SystemMonitor:
    """Return the global default monitor (auto-attached to the global event bus)."""
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = SystemMonitor()
        _default_monitor.attach()
    return _default_monitor


def reset_monitor() -> None:
    global _default_monitor
    _default_monitor = None
