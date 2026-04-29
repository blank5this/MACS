"""Simple chat example with MACS."""

import asyncio
from macs_pkg.runtime.engine import create_runtime


async def simple_chat_example():
    """Demonstrate simple multi-agent chat."""

    # Create runtime with default agents
    runtime = create_runtime(
        agents=[
            {"name": "assistant", "role": "executor"},
        ],
        mode="pipeline",
    )

    # Execute a simple task
    result = await runtime.execute({
        "type": "chat",
        "message": "Hello, how can you help me?",
    })

    print("Result:", result)

    # Get system status
    status = runtime.get_system_status()
    print("System status:", status)


if __name__ == "__main__":
    asyncio.run(simple_chat_example())
