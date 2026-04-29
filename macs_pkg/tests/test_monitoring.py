"""Tests for macs_pkg.monitoring module."""

import pytest
import asyncio

from macs_pkg.monitoring import (
    Event, EventBus, EventType,
    MetricsStore, SystemMonitor,
)


class TestEventBus:
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        bus = EventBus()
        received = []

        async def handler(event: Event):
            received.append(event)

        bus.subscribe(handler, EventType.TASK_STARTED)
        await bus.publish(Event(type=EventType.TASK_STARTED, source="test"))
        await bus.publish(Event(type=EventType.TASK_COMPLETED, source="test"))

        assert len(received) == 1
        assert received[0].type == EventType.TASK_STARTED

    @pytest.mark.asyncio
    async def test_wildcard_subscribe(self):
        bus = EventBus()
        received = []

        bus.subscribe(lambda e: received.append(e))  # sync handler, all events
        await bus.publish(Event(type=EventType.TASK_STARTED, source="test"))
        await bus.publish(Event(type=EventType.TASK_FAILED, source="test"))

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        count = []

        async def handler(e):
            count.append(1)

        bus.subscribe(handler, EventType.TASK_STARTED)
        bus.unsubscribe(handler, EventType.TASK_STARTED)

        await bus.publish(Event(type=EventType.TASK_STARTED, source="test"))
        assert len(count) == 0

    @pytest.mark.asyncio
    async def test_history(self):
        bus = EventBus()
        await bus.publish(Event(type=EventType.MESSAGE_SENT, source="a"))
        await bus.publish(Event(type=EventType.MESSAGE_SENT, source="b"))
        await bus.publish(Event(type=EventType.TASK_STARTED, source="c"))

        all_events = bus.get_history()
        assert len(all_events) == 3

        filtered = bus.get_history(event_type=EventType.MESSAGE_SENT)
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_propagate(self):
        """A failing handler must not crash the event bus."""
        bus = EventBus()

        async def bad_handler(e):
            raise RuntimeError("Handler error!")

        bus.subscribe(bad_handler)
        # Should not raise
        await bus.publish(Event(type=EventType.TASK_STARTED, source="test"))


class TestMetricsStore:
    def test_task_counters(self):
        m = MetricsStore()
        m.record_task_start()
        m.record_task_start()
        m.record_task_complete("hierarchical", 1.0)
        m.record_task_failure("pipeline")

        s = m.summary()
        assert s["tasks"]["started"] == 2
        assert s["tasks"]["completed"] == 1
        assert s["tasks"]["failed"] == 1

    def test_llm_metrics(self):
        m = MetricsStore()
        m.record_llm_call(duration_s=0.5, input_tokens=100, output_tokens=50, cache_hits=30)
        m.record_llm_call(duration_s=1.0, input_tokens=200, output_tokens=80, cache_hits=0)

        s = m.summary()
        assert s["llm"]["calls"] == 2
        assert s["llm"]["input_tokens"] == 300
        assert s["llm"]["cache_hits"] == 30

    def test_tool_metrics(self):
        m = MetricsStore()
        m.record_tool_call("calculator", success=True)
        m.record_tool_call("calculator", success=False)

        s = m.summary()
        assert s["tools"]["calculator"]["calls"] == 2
        assert s["tools"]["calculator"]["errors"] == 1

    def test_collaboration_success_rate(self):
        m = MetricsStore()
        m.record_task_complete("hierarchical", 0.5)
        m.record_task_complete("hierarchical", 0.3)
        m.record_task_failure("hierarchical")

        s = m.summary()
        mode = s["collaboration_modes"]["hierarchical"]
        assert mode["total"] == 3
        assert mode["success"] == 2
        assert abs(mode["success_rate"] - 0.667) < 0.01


class TestSystemMonitor:
    @pytest.mark.asyncio
    async def test_monitor_tracks_tasks(self):
        bus = EventBus()
        monitor = SystemMonitor()
        monitor.attach(bus)

        await bus.publish(Event(type=EventType.TASK_STARTED, source="r", data={"task_id": "t1"}))
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED, source="r",
            data={"task_id": "t1", "mode": "hierarchical", "duration_s": 1.2},
        ))

        s = monitor.metrics.summary()
        assert s["tasks"]["completed"] == 1

    @pytest.mark.asyncio
    async def test_report_contains_sections(self):
        bus = EventBus()
        monitor = SystemMonitor()
        monitor.attach(bus)

        await bus.publish(Event(type=EventType.TASK_STARTED, source="r", data={"task_id": "t1"}))
        await bus.publish(Event(
            type=EventType.TASK_COMPLETED, source="r",
            data={"task_id": "t1", "mode": "pipeline", "duration_s": 0.5},
        ))

        report = monitor.report()
        assert "Tasks" in report
        assert "Collaboration Modes" in report
        assert "pipeline" in report
