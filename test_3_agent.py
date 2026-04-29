"""3-Agent 协作测试 - 使用 MiniMax-M2.7"""

import asyncio
import sys

# Add project root to path
sys.path.insert(0, "C:/Users/admin/Desktop/macs")

from macs_pkg.runtime.engine import RuntimeEngine, RuntimeConfig
from macs_pkg.llm import MiniMaxProvider
from macs_pkg.llm.agents import MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent


async def main():
    print("[*] 初始化 MiniMax-M2.7 Provider...")
    provider = MiniMaxProvider(
        api_key="sk-cp-wyiun9o9gXkpIWiCcupjVAoquM7CI3Q3GQ7hzVrMYPy397qOw4S3bNcvpYsGkdBKDH48-JbWuhqMFJPUqUkj4YqA3MlR2Bdw5Yh7E0D9AL8Vd5bKr4_Fja0",
        model="MiniMax-M2.7",
    )

    print("[*] 创建 Runtime Engine...")
    runtime = RuntimeEngine(RuntimeConfig(
        default_mode="hierarchical",
        enable_shared_memory=False,
    ))

    # 创建并注册 3 个 Agent
    print("[*] 创建 Planner Agent...")
    planner = MiniMaxPlannerAgent(
        name="planner",
        provider=provider,
    )

    print("[*] 创建 Executor Agent...")
    executor = MiniMaxExecutorAgent(
        name="executor",
        provider=provider,
    )

    print("[*] 创建 Reviewer Agent...")
    reviewer = MiniMaxReviewerAgent(
        name="reviewer",
        provider=provider,
    )

    runtime.register_agent(planner)
    runtime.register_agent(executor)
    runtime.register_agent(reviewer)

    print("[*] 3 个 Agent 注册完成")
    print(f"    Agents: {runtime.list_agents()}")

    # 执行测试任务
    print("\n[*] 发送测试任务...")
    task = {
        "description": "用一句话介绍你自己",
    }

    print(f"[*] 任务内容: {task['description']}")
    print("[*] 执行中...\n")

    result = await runtime.execute(task, mode="hierarchical")

    print("\n" + "=" * 60)
    print("[RESULT]")
    print("=" * 60)
    print(result)
    print("=" * 60)

    # 显示系统状态
    status = runtime.get_system_status()
    print("\n[SYSTEM STATUS]")
    print(f"  Tasks completed: {status['tasks_completed']}")
    print(f"  Tasks failed: {status['tasks_failed']}")
    print(f"  Registered agents: {list(status['agents'].keys())}")

    print("\n[SUCCESS] 3-Agent 协作测试完成!")


if __name__ == "__main__":
    asyncio.run(main())