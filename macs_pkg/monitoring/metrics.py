"""Metrics collection for MACS agents and tasks."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from statistics import mean, median
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Counter:
    """Simple incrementing counter."""
    name: str
    value: int = 0

    def inc(self, amount: int = 1) -> None:
        self.value += amount

    def reset(self) -> None:
        self.value = 0


@dataclass
class Gauge:
    """Holds the latest observed value."""
    name: str
    value: float = 0.0

    def set(self, value: float) -> None:
        self.value = value


@dataclass
class Histogram:
    """Stores a series of durations or measurements for statistical summaries."""
    name: str
    _samples: List[float] = field(default_factory=list)

    def observe(self, value: float) -> None:
        self._samples.append(value)

    @property
    def count(self) -> int:
        return len(self._samples)

    @property
    def total(self) -> float:
        return sum(self._samples)

    @property
    def avg(self) -> float:
        return mean(self._samples) if self._samples else 0.0

    @property
    def median(self) -> float:
        return median(self._samples) if self._samples else 0.0

    @property
    def min(self) -> float:
        return min(self._samples) if self._samples else 0.0

    @property
    def max(self) -> float:
        return max(self._samples) if self._samples else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "total_s": round(self.total, 4),
            "avg_s": round(self.avg, 4),
            "median_s": round(self.median, 4),
            "min_s": round(self.min, 4),
            "max_s": round(self.max, 4),
        }


class MetricsStore:
    """Central store for MACS runtime metrics.

    Tracks:
      - Task outcomes (completed / failed / in-flight)
      - Per-agent latency histograms
      - Collaboration mode usage
      - LLM token consumption
      - Tool invocations
    """

    def __init__(self):
        # Task counters
        self.tasks_started = Counter("tasks_started")
        self.tasks_completed = Counter("tasks_completed")
        self.tasks_failed = Counter("tasks_failed")

        # Agent latency: agent_name → Histogram of think() durations
        self._agent_latency: Dict[str, Histogram] = defaultdict(
            lambda: Histogram("agent_latency")
        )

        # Collaboration mode usage
        self._mode_usage: Dict[str, Counter] = defaultdict(
            lambda: Counter("mode_usage")
        )
        self._mode_success: Dict[str, Counter] = defaultdict(
            lambda: Counter("mode_success")
        )
        self._mode_failure: Dict[str, Counter] = defaultdict(
            lambda: Counter("mode_failure")
        )

        # LLM usage
        self.llm_calls = Counter("llm_calls")
        self.llm_input_tokens = Counter("llm_input_tokens")
        self.llm_output_tokens = Counter("llm_output_tokens")
        self.llm_cache_hits = Counter("llm_cache_hits")
        self._llm_latency = Histogram("llm_latency")

        # Tool invocations
        self._tool_calls: Dict[str, Counter] = defaultdict(lambda: Counter("tool_calls"))
        self._tool_errors: Dict[str, Counter] = defaultdict(lambda: Counter("tool_errors"))

        # Message stats
        self.messages_sent = Counter("messages_sent")
        self.messages_dropped = Counter("messages_dropped")

        # Timestamps
        self._started_at = datetime.now()

    # ── Task ──────────────────────────────────────────────────────────────────

    def record_task_start(self) -> None:
        self.tasks_started.inc()

    def record_task_complete(self, mode: str, duration_s: float) -> None:
        self.tasks_completed.inc()
        self._mode_usage[mode].inc()
        self._mode_success[mode].inc()

    def record_task_failure(self, mode: str) -> None:
        self.tasks_failed.inc()
        self._mode_usage[mode].inc()
        self._mode_failure[mode].inc()

    # ── Agent ─────────────────────────────────────────────────────────────────

    def record_agent_think(self, agent_name: str, duration_s: float) -> None:
        self._agent_latency[agent_name].observe(duration_s)

    # ── LLM ──────────────────────────────────────────────────────────────────

    def record_llm_call(
        self,
        duration_s: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_hits: int = 0,
    ) -> None:
        self.llm_calls.inc()
        self.llm_input_tokens.inc(input_tokens)
        self.llm_output_tokens.inc(output_tokens)
        self.llm_cache_hits.inc(cache_hits)
        self._llm_latency.observe(duration_s)

    # ── Tools ─────────────────────────────────────────────────────────────────

    def record_tool_call(self, tool_name: str, success: bool) -> None:
        self._tool_calls[tool_name].inc()
        if not success:
            self._tool_errors[tool_name].inc()

    # ── Summary ───────────────────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """Return a human-readable metrics snapshot."""
        uptime = (datetime.now() - self._started_at).total_seconds()

        mode_stats = {}
        for mode in set(list(self._mode_usage.keys())):
            total = self._mode_usage[mode].value
            success = self._mode_success[mode].value
            failure = self._mode_failure[mode].value
            mode_stats[mode] = {
                "total": total,
                "success": success,
                "failure": failure,
                "success_rate": round(success / total, 3) if total else 0.0,
            }

        agent_stats = {
            name: hist.to_dict()
            for name, hist in self._agent_latency.items()
        }

        tool_stats = {
            name: {
                "calls": self._tool_calls[name].value,
                "errors": self._tool_errors[name].value,
            }
            for name in self._tool_calls
        }

        return {
            "uptime_s": round(uptime, 1),
            "tasks": {
                "started": self.tasks_started.value,
                "completed": self.tasks_completed.value,
                "failed": self.tasks_failed.value,
                "in_flight": self.tasks_started.value - self.tasks_completed.value - self.tasks_failed.value,
            },
            "collaboration_modes": mode_stats,
            "agents": agent_stats,
            "llm": {
                "calls": self.llm_calls.value,
                "input_tokens": self.llm_input_tokens.value,
                "output_tokens": self.llm_output_tokens.value,
                "cache_hits": self.llm_cache_hits.value,
                "latency": self._llm_latency.to_dict(),
            },
            "tools": tool_stats,
            "messages": {
                "sent": self.messages_sent.value,
                "dropped": self.messages_dropped.value,
            },
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.__init__()
