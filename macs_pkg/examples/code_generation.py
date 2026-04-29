"""Code generation example with MACS hierarchical collaboration."""

import asyncio
from macs_pkg.runtime.engine import create_runtime


async def code_generation_example():
    """Demonstrate hierarchical collaboration for code generation.

    Flow:
    1. Planner decomposes the coding task
    2. Executors work on different parts
    3. Reviewer validates the code
    """

    # Create runtime with specialized agents
    runtime = create_runtime(
        agents=[
            {"name": "planner", "role": "planner"},
            {"name": "coder", "role": "executor"},
            {"name": "reviewer", "role": "reviewer"},
        ],
        mode="hierarchical",
    )

    # Execute a code generation task
    task = {
        "type": "code_generation",
        "description": "Create a Python function to calculate factorial recursively",
        "requirements": {
            "language": "Python",
            "style": "clean, documented",
            "include_tests": True,
        },
    }

    result = await runtime.execute(task)

    print("Generated code result:")
    print(result)

    # Check task history
    history = runtime.get_task_history()
    print(f"\nCompleted {len(history)} tasks")


if __name__ == "__main__":
    asyncio.run(code_generation_example())
