"""Visualization tracer for MACS - trace agent execution flow.

Usage:
    from macs_pkg.visualization.tracer import ExecutionTracer

    tracer = ExecutionTracer(task_id="task_001")
    tracer.trace_agent_think_start("planner", "decompose task")
    tracer.trace_agent_think_end("planner", "3 subtasks created")
    tracer.trace_message("planner", "executor", "task", "subtask_1")

    # Generate visualization
    print(tracer.generate_mermaid_sequence())
    print(tracer.generate_mermaid_flowchart())
    print(tracer.print_stats())
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum


class TraceEventType(Enum):
    """Trace event types."""
    AGENT_THINK_START = "agent_think_start"
    AGENT_THINK_END = "agent_think_end"
    AGENT_ACT_START = "agent_act_start"
    AGENT_ACT_END = "agent_act_end"
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    TOOL_INVOKED = "tool_invoked"
    TOOL_COMPLETED = "tool_completed"
    LLM_CALL_START = "llm_call_start"
    LLM_CALL_END = "llm_call_end"
    TASK_RECEIVED = "task_received"
    TASK_COMPLETED = "task_completed"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class TraceEvent:
    """Single trace event."""
    type: TraceEventType
    agent: str
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "agent": self.agent,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "data": self.data,
        }


@dataclass
class AgentStats:
    """Agent statistics."""
    name: str
    think_count: int = 0
    act_count: int = 0
    total_think_time_ms: float = 0
    total_act_time_ms: float = 0
    llm_calls: int = 0
    total_llm_time_ms: float = 0
    messages_sent: int = 0
    messages_received: int = 0
    errors: int = 0

    @property
    def avg_think_time_ms(self) -> float:
        return self.total_think_time_ms / self.think_count if self.think_count > 0 else 0

    @property
    def avg_act_time_ms(self) -> float:
        return self.total_act_time_ms / self.act_count if self.act_count > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "think_count": self.think_count,
            "act_count": self.act_count,
            "avg_think_time_ms": round(self.avg_think_time_ms, 2),
            "avg_act_time_ms": round(self.avg_act_time_ms, 2),
            "llm_calls": self.llm_calls,
            "total_llm_time_ms": round(self.total_llm_time_ms, 2),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "errors": self.errors,
        }


class ExecutionTracer:
    """Trace agent execution flow and generate visualization.

    Records for each agent:
    - think/act phases and duration
    - inter-agent messages
    - tool invocations
    - LLM calls

    Generates Mermaid diagrams for visualization.
    """

    def __init__(self, task_id: str, enable_llm_tracing: bool = True):
        self.task_id = task_id
        self.enable_llm_tracing = enable_llm_tracing
        self.events: List[TraceEvent] = []
        self._agent_stats: Dict[str, AgentStats] = {}
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

    def record(self, event: TraceEvent):
        """Record a trace event."""
        if not self._start_time:
            self._start_time = event.timestamp
        self._end_time = event.timestamp
        self.events.append(event)
        self._update_stats(event)

    def _update_stats(self, event: TraceEvent):
        """Update agent statistics."""
        if event.agent not in self._agent_stats:
            self._agent_stats[event.agent] = AgentStats(name=event.agent)

        stats = self._agent_stats[event.agent]

        if event.type == TraceEventType.AGENT_THINK_START:
            stats.think_count += 1
        elif event.type == TraceEventType.AGENT_ACT_START:
            stats.act_count += 1
        elif event.type == TraceEventType.LLM_CALL_START:
            stats.llm_calls += 1
        elif event.type == TraceEventType.MESSAGE_SENT:
            stats.messages_sent += 1
        elif event.type == TraceEventType.MESSAGE_RECEIVED:
            stats.messages_received += 1
        elif event.type == TraceEventType.ERROR_OCCURRED:
            stats.errors += 1

        # Accumulate duration for END events
        if event.type in (TraceEventType.AGENT_THINK_END, TraceEventType.AGENT_ACT_END,
                         TraceEventType.LLM_CALL_END, TraceEventType.TOOL_COMPLETED):
            start_type = None
            if event.type == TraceEventType.AGENT_THINK_END:
                start_type = TraceEventType.AGENT_THINK_START
            elif event.type == TraceEventType.AGENT_ACT_END:
                start_type = TraceEventType.AGENT_ACT_START
            elif event.type == TraceEventType.LLM_CALL_END:
                start_type = TraceEventType.LLM_CALL_START
            elif event.type == TraceEventType.TOOL_COMPLETED:
                start_type = TraceEventType.TOOL_INVOKED

            if start_type:
                for e in reversed(self.events[:-1]):
                    if e.type == start_type and e.agent == event.agent:
                        duration = (event.timestamp - e.timestamp).total_seconds() * 1000
                        event.duration_ms = duration
                        if event.type == TraceEventType.AGENT_THINK_END:
                            stats.total_think_time_ms += duration
                        elif event.type == TraceEventType.AGENT_ACT_END:
                            stats.total_act_time_ms += duration
                        elif event.type == TraceEventType.LLM_CALL_END:
                            stats.total_llm_time_ms += duration
                        break

    # ========== Convenience methods ==========

    def trace_agent_think_start(self, agent_name: str, task_desc: str = ""):
        """Record agent think phase start."""
        self.record(TraceEvent(
            type=TraceEventType.AGENT_THINK_START,
            agent=agent_name,
            data={"task": task_desc[:100] if task_desc else ""},
        ))

    def trace_agent_think_end(self, agent_name: str, result_preview: str = ""):
        """Record agent think phase end."""
        self.record(TraceEvent(
            type=TraceEventType.AGENT_THINK_END,
            agent=agent_name,
            data={"result": result_preview[:100] if result_preview else ""},
        ))

    def trace_agent_act_start(self, agent_name: str, action: str = ""):
        """Record agent act phase start."""
        self.record(TraceEvent(
            type=TraceEventType.AGENT_ACT_START,
            agent=agent_name,
            data={"action": action[:100] if action else ""},
        ))

    def trace_agent_act_end(self, agent_name: str, outcome: str = ""):
        """Record agent act phase end."""
        self.record(TraceEvent(
            type=TraceEventType.AGENT_ACT_END,
            agent=agent_name,
            data={"outcome": outcome[:100] if outcome else ""},
        ))

    def trace_message(self, from_agent: str, to_agent: str, msg_type: str,
                      content_preview: str = ""):
        """Record inter-agent message."""
        self.record(TraceEvent(
            type=TraceEventType.MESSAGE_SENT,
            agent=from_agent,
            data={
                "to": to_agent,
                "msg_type": msg_type,
                "content": content_preview[:100] if content_preview else "",
            },
        ))
        self.record(TraceEvent(
            type=TraceEventType.MESSAGE_RECEIVED,
            agent=to_agent,
            data={
                "from": from_agent,
                "msg_type": msg_type,
                "content": content_preview[:100] if content_preview else "",
            },
        ))

    def trace_llm_call(self, agent_name: str, prompt_preview: str = "",
                       response_preview: str = "", duration_ms: float = 0):
        """Record LLM call."""
        if not self.enable_llm_tracing:
            return
        self.record(TraceEvent(
            type=TraceEventType.LLM_CALL_START,
            agent=agent_name,
            data={"prompt": prompt_preview[:100] if prompt_preview else ""},
        ))
        self.record(TraceEvent(
            type=TraceEventType.LLM_CALL_END,
            agent=agent_name,
            duration_ms=duration_ms,
            data={"response": response_preview[:100] if response_preview else ""},
        ))

    def trace_tool_invoked(self, agent_name: str, tool_name: str, args: Dict[str, Any] = None):
        """Record tool invocation."""
        self.record(TraceEvent(
            type=TraceEventType.TOOL_INVOKED,
            agent=agent_name,
            data={
                "tool": tool_name,
                "args": {k: str(v)[:50] for k, v in (args or {}).items()},
            },
        ))

    def trace_task_received(self, agent_name: str, task_id: str, task_desc: str = ""):
        """Record task received."""
        self.record(TraceEvent(
            type=TraceEventType.TASK_RECEIVED,
            agent=agent_name,
            data={
                "task_id": task_id,
                "task": task_desc[:100] if task_desc else "",
            },
        ))

    def trace_task_completed(self, agent_name: str, task_id: str, success: bool = True):
        """Record task completed."""
        self.record(TraceEvent(
            type=TraceEventType.TASK_COMPLETED,
            agent=agent_name,
            data={
                "task_id": task_id,
                "success": success,
            },
        ))

    def trace_error(self, agent_name: str, error: str, context: Dict[str, Any] = None):
        """Record error."""
        self.record(TraceEvent(
            type=TraceEventType.ERROR_OCCURRED,
            agent=agent_name,
            data={
                "error": error[:200] if error else "",
                "context": context or {},
            },
        ))

    # ========== Visualization generation ==========

    def generate_mermaid_sequence(self) -> str:
        """Generate Mermaid sequence diagram.

        Usage: paste to https://mermaid.live to view.
        """
        lines = ["```mermaid", "sequenceDiagram"]

        agents = sorted(set(e.agent for e in self.events))
        for agent in agents:
            lines.append(f"    Participant {agent}")

        lines.append("")

        for event in self.events:
            data = event.data
            duration = f"[{event.duration_ms:.1f}ms]" if event.duration_ms else ""

            if event.type == TraceEventType.AGENT_THINK_START:
                lines.append(f"    {event.agent}->>+{event.agent}: think(){duration}")
            elif event.type == TraceEventType.AGENT_THINK_END:
                lines.append(f"    {event.agent}-->>-{event.agent}: result{duration}")
            elif event.type == TraceEventType.AGENT_ACT_START:
                lines.append(f"    {event.agent}->>+{event.agent}: act(){duration}")
            elif event.type == TraceEventType.AGENT_ACT_END:
                lines.append(f"    {event.agent}-->>-{event.agent}: done{duration}")
            elif event.type == TraceEventType.MESSAGE_SENT:
                to_agent = data.get("to", "?")
                msg_type = data.get("msg_type", "message")
                lines.append(f"    {event.agent}->>+{to_agent}: {msg_type}{duration}")
            elif event.type == TraceEventType.MESSAGE_RECEIVED:
                from_agent = data.get("from", "?")
                lines.append(f"    {event.agent}-->>-{from_agent}: ack{duration}")
            elif event.type == TraceEventType.LLM_CALL_START:
                lines.append(f"    {event.agent}->>+{event.agent}: LLM call(){duration}")
            elif event.type == TraceEventType.LLM_CALL_END:
                lines.append(f"    {event.agent}-->>-{event.agent}: response{duration}")
            elif event.type == TraceEventType.TOOL_INVOKED:
                tool = data.get("tool", "?")
                lines.append(f"    {event.agent}->>+{event.agent}: tool:{tool}(){duration}")
            elif event.type == TraceEventType.TASK_RECEIVED:
                task_id = data.get("task_id", "?")
                lines.append(f"    {event.agent}->>+{event.agent}: task:{task_id}{duration}")

        lines.append("```")
        return "\n".join(lines)

    def generate_mermaid_flowchart(self) -> str:
        """Generate Mermaid flowchart.

        Usage: paste to https://mermaid.live to view.
        """
        lines = ["```mermaid", "graph TD"]

        # Collect agents and their tasks
        agent_tasks: Dict[str, List[str]] = {}
        for event in self.events:
            if event.type == TraceEventType.AGENT_THINK_START:
                if event.agent not in agent_tasks:
                    agent_tasks[event.agent] = []
                task_num = len(agent_tasks[event.agent])
                agent_tasks[event.agent].append(f"{event.agent}_Task{task_num}")

        # Define nodes
        for agent, tasks in agent_tasks.items():
            lines.append(f"    {agent}[({agent})]")
            for i, task_id in enumerate(tasks):
                lines.append(f"    {task_id}[{agent}/Task {i+1}]")
                lines.append(f"    {agent} --> {task_id}")

        # Define connections
        for event in self.events:
            if event.type == TraceEventType.MESSAGE_SENT:
                from_a = event.agent
                to_a = event.data.get("to", "?")
                lines.append(f"    {from_a} -->|msg| {to_a}")

        lines.append("```")
        return "\n".join(lines)

    def generate_stats(self) -> Dict[str, Any]:
        """Generate statistics."""
        total_duration_ms = 0
        if self._start_time and self._end_time:
            total_duration_ms = (self._end_time - self._start_time).total_seconds() * 1000

        return {
            "task_id": self.task_id,
            "total_duration_ms": round(total_duration_ms, 2),
            "total_events": len(self.events),
            "agents": list(self._agent_stats.keys()),
            "agent_stats": {name: stats.to_dict() for name, stats in self._agent_stats.items()},
            "event_counts": self._count_events_by_type(),
        }

    def _count_events_by_type(self) -> Dict[str, int]:
        """Count events by type."""
        counts: Dict[str, int] = {}
        for event in self.events:
            type_name = event.type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts

    def print_stats(self) -> str:
        """Generate readable stats report."""
        stats = self.generate_stats()
        lines = [
            "=" * 50,
            f"Execution Tracer Report - Task: {stats['task_id']}",
            "=" * 50,
            f"Total Duration: {stats['total_duration_ms']:.2f}ms",
            f"Total Events: {stats['total_events']}",
            f"Agents: {', '.join(stats['agents'])}",
            "",
            "Agent Statistics:",
            "-" * 50,
        ]

        for name, agent_stats in stats['agent_stats'].items():
            lines.append(f"  [{name}]")
            lines.append(f"    think: {agent_stats['think_count']} calls, "
                        f"avg {agent_stats['avg_think_time_ms']:.2f}ms")
            lines.append(f"    act:   {agent_stats['act_count']} calls, "
                        f"avg {agent_stats['avg_act_time_ms']:.2f}ms")
            lines.append(f"    LLM:   {agent_stats['llm_calls']} calls, "
                        f"total {agent_stats['total_llm_time_ms']:.2f}ms")
            lines.append(f"    msgs:  {agent_stats['messages_sent']} sent, "
                        f"{agent_stats['messages_received']} received")
            if agent_stats['errors'] > 0:
                lines.append(f"    errors: {agent_stats['errors']}")
            lines.append("")

        lines.append("Event Counts:")
        for event_type, count in stats['event_counts'].items():
            lines.append(f"  {event_type}: {count}")

        lines.append("=" * 50)
        return "\n".join(lines)


# ============ Runtime Integration ============

class TracedRuntimeMixin:
    """Mixin to add tracing capability to RuntimeEngine.

    Usage:
        class TracedRuntimeEngine(TracedRuntimeMixin, RuntimeEngine):
            pass
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tracer: Optional[ExecutionTracer] = None

    def enable_tracing(self, task_id: str):
        """Enable tracing."""
        self._tracer = ExecutionTracer(task_id=task_id)

    def get_tracer(self) -> Optional[ExecutionTracer]:
        """Get tracer."""
        return self._tracer

    def disable_tracing(self):
        """Disable tracing."""
        self._tracer = None
