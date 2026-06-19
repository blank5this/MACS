"""Agent 协作过程演示 - 展示多 Agent 如何配合工作

这个脚本展示：
1. Planner 理解问题并分解任务
2. Executor 执行具体子任务
3. Reviewer 审核结果
4. 三者如何协作

运行方式:
    MINIMAX_API_KEY="your-key" python agent_process_demo.py
"""

import asyncio
import os
import json
import sys
from datetime import datetime

# 跨平台强制 UTF-8 I/O（修 Windows cp936 中文乱码）
from macs_pkg._compat import force_utf8_io
force_utf8_io()


class Agent:
    """简单的 Agent 模拟"""

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    async def think(self, task: str, context: dict = None) -> str:
        """思考阶段"""
        print(f"\n[{self.name}] 思考中...")
        print(f"  角色: {self.role}")
        print(f"  任务: {task[:50]}...")
        if context:
            print(f"  上下文: {len(context.get('sources', []))} 条检索结果")
        return f"[{self.name}] 理解了任务，准备执行"

    async def act(self, task: str, context: dict = None) -> dict:
        """行动阶段"""
        print(f"\n[{self.name}] 执行中...")
        return {
            "agent": self.name,
            "action": f"{self.role}_action",
            "result": f"完成 {self.role} 任务",
            "task": task,
            "context": context
        }


async def main():
    print("=" * 70)
    print("MACS 多智能体协作演示 - 一步步展示 Agent 配合过程")
    print("=" * 70)

    # 研究问题
    query = "解释一下什么是 RAG"

    print(f"\n{'=' * 70}")
    print(f"用户问题: {query}")
    print("=" * 70)

    # ========== 阶段 1: Planner 分解任务 ==========
    print("\n" + "=" * 70)
    print("阶段 1: PLANNER 分解任务")
    print("=" * 70)

    planner = Agent("Planner", "任务规划")

    # Planner 思考
    await planner.think(f"分析用户问题: {query}")

    # Planner 分解
    print(f"\n[Planner] 分解任务:")
    print(f"  1. 理解问题 - 理解用户问的是 RAG 技术")
    print(f"  2. 分解子任务:")
    print(f"     - 子任务 1: 解释 RAG 定义")
    print(f"     - 子任务 2: 说明 RAG 工作原理")
    print(f"     - 子任务 3: 列举 RAG 应用场景")
    print(f"  3. 确定执行顺序: 1 -> 2 -> 3")
    print(f"  4. 分配执行者: Executor")

    subtasks = [
        {"id": "subtask_1", "description": "解释 RAG 定义", "type": "definition"},
        {"id": "subtask_2", "description": "说明 RAG 工作原理", "type": "原理"},
        {"id": "subtask_3", "description": "列举 RAG 应用场景", "type": "应用"},
    ]

    # Planner 行动
    plan_result = await planner.act(f"分解任务: {query}", {"subtasks": subtasks})
    print(f"\n[Planner] 任务分解完成，生成执行计划")

    # ========== 阶段 2: Executor 执行 ==========
    print("\n" + "=" * 70)
    print("阶段 2: EXECUTOR 执行子任务")
    print("=" * 70)

    executor = Agent("Executor", "任务执行")

    for i, subtask in enumerate(subtasks, 1):
        print(f"\n--- 执行子任务 {i}/{len(subtasks)} ---")

        # Executor 思考
        await executor.think(f"执行: {subtask['description']}")

        # Executor 行动
        print(f"\n[Executor] 调用 LLM 生成内容...")
        print(f"  子任务: {subtask['description']}")
        print(f"  类型: {subtask['type']}")

        # 模拟 LLM 调用
        if subtask['type'] == "definition":
            content = "RAG（检索增强生成）是一种将信息检索与语言模型生成相结合的技术。"
        elif subtask['type'] == "原理":
            content = "RAG 通过检索外部知识库获取相关文档，然后将这些文档作为上下文输入 LLM 进行生成。"
        else:
            content = "RAG 应用于企业知识库问答、文档分析、专业咨询等场景。"

        print(f"  生成内容: {content[:30]}...")
        print(f"  [Executor] 子任务 {i} 完成")

    # Executor 汇总
    print(f"\n[Executor] 所有子任务完成，汇总结果")
    executor_result = {
        "agent": "Executor",
        "subtasks_completed": len(subtasks),
        "summary": "RAG 是检索增强生成技术，结合外部检索和 LLM 生成..."
    }

    # ========== 阶段 3: Reviewer 审核 ==========
    print("\n" + "=" * 70)
    print("阶段 3: REVIEWER 审核结果")
    print("=" * 70)

    reviewer = Agent("Reviewer", "质量审核")

    # Reviewer 思考
    await reviewer.think("审核 Executor 的结果")

    # Reviewer 审核
    print(f"\n[Reviewer] 审核项目:")
    print(f"  1. 完整性检查: 是否回答了问题的各个方面 ✓")
    print(f"  2. 准确性检查: 内容是否正确 ✓")
    print(f"  3. 相关性检查: 是否与问题相关 ✓")
    print(f"  4. 可读性检查: 表达是否清晰 ✓")

    review_result = await reviewer.act("审核结果", executor_result)
    print(f"\n[Reviewer] 审核通过!")
    print(f"  质量评分: 95/100")
    print(f"  建议: 可以直接返回给用户")

    # ========== 阶段 4: 返回结果 ==========
    print("\n" + "=" * 70)
    print("阶段 4: 返回最终结果给用户")
    print("=" * 70)

    print(f"\n最终答案:")
    print("-" * 50)
    print("""
RAG（检索增强生成）是一种将信息检索与语言模型生成相结合的技术。

工作原理：
1. 检索：当用户提问时，先从外部知识库检索相关文档
2. 增强：将检索到的文档作为上下文输入 LLM
3. 生成：LLM 基于上下文生成准确答案

应用场景：企业知识库问答、文档分析、专业咨询等
""")
    print("-" * 50)

    # ========== 总结 ==========
    print("\n" + "=" * 70)
    print("协作流程总结")
    print("=" * 70)
    print("""
    ┌─────────────────────────────────────────────────────────┐
    │                      用户提问                            │
    │               "解释一下什么是 RAG"                        │
    └─────────────────────┬───────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────┐
    │  PLANNER (任务规划)                                    │
    │  • 理解用户意图                                         │
    │  • 分解为 3 个子任务                                    │
    │  • 制定执行计划                                         │
    └─────────────────────┬───────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────┐
    │  EXECUTOR (执行器)                                      │
    │  • 执行子任务 1: 解释定义                                │
    │  • 执行子任务 2: 说明原理                                │
    │  • 执行子任务 3: 列举应用                                │
    │  • 汇总结果                                              │
    └─────────────────────┬───────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────┐
    │  REVIEWER (审核员)                                       │
    │  • 完整性检查                                            │
    │  • 准确性检查                                            │
    │  • 质量评分                                              │
    └─────────────────────┬───────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────────┐
    │                      用户得到答案                         │
    └─────────────────────────────────────────────────────────┘
    """)

    print("\n演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
