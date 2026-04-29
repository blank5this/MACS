"""Complete MACS example: LLM agents + tools + monitoring.

Demonstrates how to run a multi-agent task with:
  - LLMPlannerAgent / LLMExecutorAgent (backed by Claude)
  - Built-in tools (calculator, json_parser, text_formatter)
  - SystemMonitor to track metrics
  - Hierarchical collaboration mode

Set ANTHROPIC_API_KEY to enable real LLM. Without it, agents fall back
to heuristic implementations and the example still runs end-to-end.
"""

import asyncio
from macs_pkg import (
    create_runtime,
    create_default_registry,
    get_event_bus,
    SystemMonitor,
)
from macs_pkg.monitoring.event_bus import reset_event_bus
from macs_pkg.monitoring.monitor import reset_monitor


async def main():
    # ── Reset singletons for a clean run ──────────────────────────────────
    reset_event_bus()
    reset_monitor()

    # ── Set up monitoring ──────────────────────────────────────────────────
    monitor = SystemMonitor()
    monitor.attach()                          # attach to global event bus

    # ── Set up tools ──────────────────────────────────────────────────────
    tools = create_default_registry()
    print(f"Available tools: {tools.list_tools()}\n")

    # ── Inline tool demo ───────────────────────────────────────────────────
    calc_result = await tools.invoke("calculator", expression="sqrt(256) + 2**4")
    fmt_result  = await tools.invoke("text_formatter", text="macs multi-agent system", operation="title")
    json_result = await tools.invoke("json_parser",
                                     json_string='{"system": {"agents": 3, "mode": "hierarchical"}}',
                                     path="system.mode")

    print("=== Tool Demos ===")
    print(f"  calculator:     {calc_result.output}")
    print(f"  text_formatter: {fmt_result.output}")
    print(f"  json_parser:    {json_result.output}")
    print()

    # ── Multi-agent task execution ─────────────────────────────────────────
    # Try to use LLM agents if ANTHROPIC_API_KEY is set
    try:
        import os
        from macs_pkg.llm import ClaudeProvider, LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent

        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = ClaudeProvider()
            planner  = LLMPlannerAgent("planner",  provider=provider)
            executor = LLMExecutorAgent("executor", provider=provider, tool_registry=tools)
            reviewer = LLMReviewerAgent("reviewer", provider=provider)

            runtime = create_runtime(mode="hierarchical")
            for agent in [planner, executor, reviewer]:
                runtime.register_agent(agent)
            print("Using real LLM agents (Claude)")
        else:
            raise EnvironmentError("No API key")

    except EnvironmentError:
        # Fallback to heuristic agents
        runtime = create_runtime(
            agents=[
                {"name": "planner",  "role": "planner"},
                {"name": "executor", "role": "executor"},
                {"name": "reviewer", "role": "reviewer"},
            ],
            mode="hierarchical",
        )
        print("Using heuristic agents (no ANTHROPIC_API_KEY set)")

    print()

    # Run two tasks
    tasks = [
        {"type": "analysis", "description": "Analyze the performance characteristics of the hierarchical collaboration mode in MACS."},
        {"type": "code_review", "description": "Review the tools module for potential improvements."},
    ]

    for t in tasks:
        result = await runtime.execute(t, mode="hierarchical")
        print(f"Task '{t['type']}' completed.")

    # ── Print metrics ──────────────────────────────────────────────────────
    print()
    print(monitor.report())


if __name__ == "__main__":
    asyncio.run(main())
