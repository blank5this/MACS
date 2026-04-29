"""LLM Integration Example - Demonstrates MACS with Claude LLM.

This example shows how to:
1. Configure MACS with a Claude LLM provider
2. Use LLM-powered agents for task decomposition, execution, and review
3. Combine with MemPalace memory system

Prerequisites:
- Set ANTHROPIC_API_KEY environment variable, or
- Pass api_key to ClaudeProvider
"""

import asyncio
import os
from macs_pkg.runtime.engine import RuntimeEngine, RuntimeConfig
from macs_pkg.llm.claude import ClaudeProvider
from macs_pkg.llm.base import LLMMessage


async def example_with_claude():
    """Example using Claude LLM for all agents."""

    print("=" * 60)
    print("MACS with Claude LLM Integration")
    print("=" * 60)

    # 1. Create LLM Provider
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n⚠️  ANTHROPIC_API_KEY not set, using mock mode")
        print("   Set the environment variable to use real LLM:")
        print("   export ANTHROPIC_API_KEY=your_key")

    provider = ClaudeProvider(api_key=api_key) if api_key else None

    # 2. Create Runtime with shared memory
    runtime = RuntimeEngine(RuntimeConfig(
        enable_shared_memory=True,
        default_mode="hierarchical",
    ))

    # 3. Create and register agents with LLM provider
    runtime.create_and_register_agents([
        {"name": "planner", "role": "planner", "model": "claude-sonnet-4-6"},
        {"name": "executor", "role": "executor", "model": "claude-sonnet-4-6"},
        {"name": "reviewer", "role": "reviewer", "model": "claude-sonnet-4-6"},
    ], provider=provider)

    # 4. Set provider for existing agents (if not set during creation)
    if provider:
        runtime.set_llm_provider(provider)

    # 5. Initialize memories
    await runtime.init_shared_memory_async()
    for agent_name in runtime.list_agents():
        agent = runtime.get_agent(agent_name)
        if agent and hasattr(agent, 'init_memory'):
            await agent.init_memory()

    # 6. Execute a task
    print("\n--- Executing Task ---")
    task = {
        "type": "feature_development",
        "description": "Implement a REST API for user authentication with JWT tokens",
        "requirements": [
            "POST /auth/register - User registration",
            "POST /auth/login - User login, returns JWT",
            "GET /auth/me - Get current user (protected)",
            "JWT tokens should expire in 24 hours",
        ],
    }

    result = await runtime.execute(task, mode="hierarchical")

    print(f"\n--- Result ---")
    print(f"Task completed: {result}")

    # 7. Check memory
    print("\n--- Memory Check ---")
    planner = runtime.get_agent("planner")
    if planner and planner.has_long_term_memory():
        memories = await planner.get_all_long_term_memories(limit=5)
        print(f"Planner has {len(memories)} long-term memories")


async def example_without_llm():
    """Example without LLM (mock mode)."""

    print("\n" + "=" * 60)
    print("MACS without LLM (Mock Mode)")
    print("=" * 60)

    runtime = RuntimeEngine(RuntimeConfig(
        enable_shared_memory=True,
        default_mode="hierarchical",
    ))

    runtime.create_and_register_agents([
        {"name": "planner", "role": "planner"},
        {"name": "executor", "role": "executor"},
        {"name": "reviewer", "role": "reviewer"},
    ])

    await runtime.init_shared_memory_async()
    for agent_name in runtime.list_agents():
        agent = runtime.get_agent(agent_name)
        if agent and hasattr(agent, 'init_memory'):
            await agent.init_memory()

    print("\n--- Task Execution (Mock) ---")
    result = await runtime.execute({
        "type": "test",
        "description": "Test task without LLM",
    })

    print(f"Result: {result}")
    print(f"Status: {runtime.get_system_status()}")


async def example_code_generation():
    """Example of code generation task."""

    print("\n" + "=" * 60)
    print("Code Generation Example")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    provider = ClaudeProvider(api_key=api_key) if api_key else None

    runtime = RuntimeEngine(RuntimeConfig(
        enable_shared_memory=True,
        default_mode="hierarchical",
    ))

    runtime.create_and_register_agents([
        {"name": "planner", "role": "planner"},
        {"name": "executor", "role": "executor"},
    ], provider=provider)

    if provider:
        runtime.set_llm_provider(provider)

    await runtime.init_shared_memory_async()
    for agent_name in runtime.list_agents():
        agent = runtime.get_agent(agent_name)
        if agent and hasattr(agent, 'init_memory'):
            await agent.init_memory()

    print("\n--- Code Generation Task ---")
    task = {
        "type": "code_generation",
        "description": "Generate a Python function to calculate fibonacci numbers",
        "requirements": [
            "Function name: fibonacci",
            "Input: integer n",
            "Output: nth fibonacci number",
            "Handle edge cases (negative numbers)",
        ],
    }

    result = await runtime.execute(task, mode="hierarchical")
    print(f"Result: {result}")


async def main():
    """Run all examples."""

    # Check if we have API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if api_key:
        try:
            await example_with_claude()
        except Exception as e:
            print(f"Claude example error: {e}")
            await example_without_llm()
    else:
        await example_without_llm()

    await example_code_generation()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
