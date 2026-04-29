"""Research assistant example with decentralized collaboration."""

import asyncio
from macs_pkg.runtime.engine import create_runtime


async def research_assistant_example():
    """Demonstrate decentralized collaboration for research tasks.

    Flow:
    1. Multiple agents propose research approaches
    2. Agents vote/negotiate on the best approach
    3. Consensus is reached and execution proceeds
    """

    # Create runtime with multiple agents
    runtime = create_runtime(
        agents=[
            {"name": "researcher_1", "role": "executor"},
            {"name": "researcher_2", "role": "executor"},
            {"name": "analyst", "role": "executor"},
            {"name": "synthesizer", "role": "reviewer"},
        ],
        mode="decentralized",
    )

    # Execute a research task
    task = {
        "type": "research",
        "query": "What are the latest developments in AI agent frameworks?",
        "depth": "comprehensive",
        "sources": ["papers", "articles", "github"],
    }

    result = await runtime.execute(task)

    print("Research result:")
    print(result)


if __name__ == "__main__":
    asyncio.run(research_assistant_example())
