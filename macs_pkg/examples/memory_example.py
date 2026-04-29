"""Memory integration example with MACS and MemPalace.

This example demonstrates how to use the MemPalace memory system
with the MACS multi-agent collaboration framework.
"""

import asyncio
from macs_pkg.runtime.engine import RuntimeEngine, RuntimeConfig
from macs_pkg.core.agent import BaseAgent, AgentRole, Message
from macs_pkg.memory.agent_memory import AgentMemoryConfig, SharedMemory
from macs_pkg.memory.mempalace_client import MemoryConfig


class MemoryEnabledAgent(BaseAgent):
    """Example agent with long-term memory capabilities."""

    async def think(self, message: Message) -> Message:
        """Process message with memory context."""
        self.state = "thinking"

        # Recall relevant past interactions
        relevant_memories = []
        if self.has_long_term_memory():
            relevant_memories = await self.recall(
                query=str(message.content),
                limit=3,
            )

        # Build context from memories
        context = ""
        if relevant_memories:
            context = "\n\n[Past relevant context]\n"
            for m in relevant_memories:
                context += f"- {m.content}\n"

        # Process the message
        response_content = f"[{self.role.value}] Processed: {message.content}{context}"

        # Remember this interaction
        if self.has_long_term_memory():
            await self.remember_interaction(
                message_content=str(message.content),
                sender=message.sender,
                receiver=self.name,
                task_id=message.metadata.get("task_id"),
            )

        self.state = "idle"
        return Message(
            sender=self.name,
            receiver=message.sender,
            content=response_content,
            msg_type="result",
            metadata={"original_id": message.id},
        )

    async def act(self, response: Message) -> list:
        """Send response."""
        self.add_to_memory(response)
        return [response]


async def basic_memory_example():
    """Basic example of using agent memory."""

    print("=" * 60)
    print("Basic Memory Example")
    print("=" * 60)

    # Configure memory
    memory_config = MemoryConfig(
        storage_path="~/.macs/example_memory",
        wing_prefix="agent",
        room_prefix="role",
    )

    # Initialize shared memory for all agents
    await BaseAgent.init_shared_memory(memory_config)

    # Create agents with memory
    planner = MemoryEnabledAgent(
        name="planner",
        role=AgentRole.PLANNER,
        model="gpt-4",
    )
    executor = MemoryEnabledAgent(
        name="executor",
        role=AgentRole.EXECUTOR,
        model="gpt-4",
    )

    # Initialize agent memories
    await planner.init_memory()
    await executor.init_memory()

    # First interaction - will have no prior memories
    print("\n--- First Interaction ---")
    msg1 = Message(
        sender="user",
        receiver="planner",
        content="We need to implement user authentication",
    )
    response1 = await planner.think(msg1)
    print(f"Planner response: {response1.content[:100]}...")

    # Remember a decision
    await planner.remember_decision(
        decision="Use JWT for authentication",
        rationale="JWT is stateless and scales well",
        task_id="task_1",
    )

    # Second interaction - will find the authentication memory
    print("\n--- Second Interaction ---")
    msg2 = Message(
        sender="user",
        receiver="planner",
        content="What authentication method did we decide on?",
    )
    response2 = await planner.think(msg2)
    print(f"Planner response: {response2.content[:200]}...")

    # Recall memories
    print("\n--- Recalling memories ---")
    memories = await planner.recall("authentication", limit=5)
    print(f"Found {len(memories)} relevant memories")
    for m in memories:
        print(f"  - {m.content[:80]}...")


async def shared_memory_example():
    """Example of using shared memory across agents."""

    print("\n" + "=" * 60)
    print("Shared Memory Example")
    print("=" * 60)

    # Create runtime with shared memory enabled
    config = RuntimeConfig(
        enable_shared_memory=True,
        memory={
            "storage_path": "~/.macs/shared_example",
            "project_name": "example_project",
        },
    )
    runtime = RuntimeEngine(config)

    # Initialize shared memory
    await runtime.init_shared_memory_async()

    # Store some shared knowledge
    print("\n--- Storing shared knowledge ---")
    await runtime.store_shared_decision(
        decision="Use microservices architecture",
        made_by="architecture_team",
        rationale="Better scalability and deployment independence",
    )
    print("Stored architecture decision")

    await runtime.store_shared_knowledge(
        fact="Our API uses REST with JSON payloads",
        source="API documentation",
    )
    print("Stored API knowledge")

    # Search shared memory
    print("\n--- Searching shared memory ---")
    results = await runtime.search_shared_memory("architecture", limit=5)
    print(f"Found {len(results)} results for 'architecture'")
    for r in results:
        print(f"  - {r.get('content', '')[:80]}...")


async def full_integration_example():
    """Full integration example with hierarchical collaboration."""

    print("\n" + "=" * 60)
    print("Full Integration Example")
    print("=" * 60)

    # Create runtime with memory enabled
    config = RuntimeConfig(
        enable_shared_memory=True,
        default_mode="hierarchical",
    )
    runtime = RuntimeEngine(config)

    # Create and register agents
    planner = MemoryEnabledAgent(
        name="planner",
        role=AgentRole.PLANNER,
    )
    executor = MemoryEnabledAgent(
        name="executor",
        role=AgentRole.EXECUTOR,
    )
    reviewer = MemoryEnabledAgent(
        name="reviewer",
        role=AgentRole.REVIEWER,
    )

    runtime.register_agent(planner)
    runtime.register_agent(executor)
    runtime.register_agent(reviewer)

    # Initialize memories
    await runtime.init_shared_memory_async()
    await planner.init_memory()
    await executor.init_memory()
    await reviewer.init_memory()

    # Execute a task that will be remembered
    print("\n--- Executing task ---")
    task = {
        "type": "feature_development",
        "description": "Implement user profile management",
        "requirements": [
            "User can view their profile",
            "User can edit their profile",
            "Changes are saved to database",
        ],
    }

    result = await runtime.execute(task, mode="hierarchical")
    print(f"Task result: {str(result)[:100]}...")

    # Check task history
    history = runtime.get_task_history()
    print(f"\nTask history: {len(history)} tasks completed")

    # Get system status including memory info
    status = runtime.get_system_status()
    print(f"\nSystem status:")
    print(f"  Agents: {len(status['agents'])}")
    print(f"  Tasks completed: {status['tasks_completed']}")
    for name, info in status["agents"].items():
        has_memory = "has memory" if has_long_term_memory_for(name) else "no memory"
        print(f"    {name} ({info['role']}): {has_memory}")


def has_long_term_memory_for(agent_name: str) -> bool:
    """Check if an agent has long-term memory (simplified)."""
    # In real usage, you'd check the actual agent instance
    return True


async def memory_comparison_without_mempalace():
    """Demonstrate behavior without MemPalace installed."""

    print("\n" + "=" * 60)
    print("Fallback Mode (MemPalace not installed)")
    print("=" * 60)

    # Create runtime without shared memory
    config = RuntimeConfig(enable_shared_memory=False)
    runtime = RuntimeEngine(config)

    # Create simple agent
    agent = MemoryEnabledAgent(
        name="test_agent",
        role=AgentRole.EXECUTOR,
    )

    # Initialize its memory
    await agent.init_memory()

    # The agent will use in-memory fallback
    print("\n--- Testing with fallback memory ---")
    await agent.remember(
        content="This is a test memory",
        memory_type="interaction",
    )

    memories = await agent.recall("test", limit=5)
    print(f"Found {len(memories)} memories (using fallback)")
    if memories:
        print(f"  First: {memories[0].content}")


async def main():
    """Run all examples."""
    try:
        await basic_memory_example()
    except Exception as e:
        print(f"Basic memory example error: {e}")

    try:
        await shared_memory_example()
    except Exception as e:
        print(f"Shared memory example error: {e}")

    try:
        await full_integration_example()
    except Exception as e:
        print(f"Full integration example error: {e}")

    try:
        await memory_comparison_without_mempalace()
    except Exception as e:
        print(f"Fallback mode example error: {e}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
