"""研究助手 Demo - Research Assistant with Multi-Agent Collaboration

这个脚本演示如何使用 MACS 框架构建一个研究助手：
- PlannerAgent: 分解研究任务
- ExecutorAgent: 执行搜索和阅读
- ReviewerAgent: 审核结果质量

运行方式:
    python research_assistant_demo.py

可选配置:
    - 设置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 环境变量启用 LLM
    - 默认使用 mock 模式运行
"""

import asyncio
import os

# 跨平台强制 UTF-8 I/O（修 Windows cp936 中文乱码）
from macs_pkg._compat import force_utf8_io
force_utf8_io()

from macs_pkg.runtime.engine import RuntimeEngine, RuntimeConfig
from macs_pkg.core.agent import AgentRole
from macs_pkg.llm import MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent
from macs_pkg.rag import RAGEngine, RAGConfig


class ResearchAssistant:
    """研究助手 - 使用多 Agent 协作进行信息研究和总结"""

    def __init__(self, use_llm: bool = False):
        self.use_llm = use_llm
        self.rag = None
        self.runtime = None

    async def initialize(self):
        """初始化研究助手"""
        print("=" * 60)
        print("Research Assistant - 初始化中...")
        print("=" * 60)

        # 初始化 RAG 知识库
        print("\n[1/3] 初始化知识库...")
        self.rag = RAGEngine(RAGConfig(
            embedder_provider="dummy",
            vector_store_type="memory",
            embedding_dim=384,
        ))

        # 添加一些示例知识
        await self.rag.add_documents([
            "人工智能（AI）是计算机科学的一个分支，旨在创造能够模拟人类智能的机器。",
            "机器学习是 AI 的一个子领域，通过数据分析让计算机自动学习规律。",
            "深度学习是机器学习的一个分支，使用多层神经网络进行特征提取和学习。",
            "自然语言处理（NLP）是 AI 与语言学的交叉领域，专注于理解和生成人类语言。",
            "RAG（检索增强生成）结合了信息检索和文本生成，提高 AI 回答的准确性。",
            "向量数据库用于存储高维向量，支持高效的相似性搜索。",
            "Transformer 架构是现代 NLP 的基础，GPT 和 BERT 都基于此。",
            "大语言模型（LLM）是参数量巨大的语言模型，具备强大的泛化能力。",
        ], metadatas=[{"source": "AI基础知识"}, {"source": "ML"}, {"source": "DL"}, {"source": "NLP"},
                      {"source": "RAG"}, {"source": "向量数据库"}, {"source": "架构"}, {"source": "LLM"}])
        print("      知识库已加载 8 条文档")

        # 初始化 Runtime
        print("\n[2/3] 初始化 Agent 运行时...")

        # 检查是否有 LLM API Key
        api_key = os.environ.get("MINIMAX_API_KEY")
        if api_key and self.use_llm:
            print("      检测到 MINIMAX_API_KEY，将使用 MiniMax M2.7")
            from macs_pkg.llm import MiniMaxProvider
            provider = MiniMaxProvider(model="MiniMax-M2.7")
            self.runtime = RuntimeEngine(RuntimeConfig(
                enable_shared_memory=True,
                default_mode="hierarchical",
            ))
        else:
            print("      无 API Key，使用 Mock 模式")
            from macs_pkg.core.agent import SimpleAgent
            self.runtime = RuntimeEngine(RuntimeConfig(
                enable_shared_memory=True,
                default_mode="hierarchical",
            ))
            provider = None

        # 注册 Agents（使用 LLM 驱动的 Agent）
        if provider:
            self.runtime.register_agent(MiniMaxPlannerAgent("planner", provider=provider))
            self.runtime.register_agent(MiniMaxExecutorAgent("executor", provider=provider))
            self.runtime.register_agent(MiniMaxReviewerAgent("reviewer", provider=provider))
        else:
            from macs_pkg.core.agent import SimpleAgent
            self.runtime.register_agent(SimpleAgent("planner", AgentRole.PLANNER))
            self.runtime.register_agent(SimpleAgent("executor", AgentRole.EXECUTOR))
            self.runtime.register_agent(SimpleAgent("reviewer", AgentRole.REVIEWER))

        print("      注册了 planner, executor, reviewer Agent")

        print("\n[3/3] 初始化完成！")
        print("=" * 60)

    async def research(self, query: str) -> dict:
        """执行研究任务

        Args:
            query: 研究主题

        Returns:
            研究结果字典
        """
        print(f"\n{'=' * 60}")
        print(f"研究主题: {query}")
        print("=" * 60)

        # 1. 知识库检索
        print("\n>>> [Step 1] Planner 分解任务...")
        print(f"    用户问题: {query}")

        print("\n>>> [Step 2] Executor 执行检索...")
        results = await self.rag.search(query)
        print(f"    RAG 找到 {len(results)} 条相关内容")

        # 3. Agent 协作处理
        print("\n>>> [Step 3] 多 Agent 协作处理...")
        task_result = await self.runtime.execute({
            "type": "research",
            "description": query,
            "context": [r.content for r in results],
        })
        print(f"      Agent 处理完成")

        # 3. 总结结果
        print("\n>>> [Step 4] Reviewer 审核结果...")

        # 构建报告
        report = {
            "topic": query,
            "sources": [r.content for r in results],
            "agent_response": str(task_result),
        }

        print(report.get("agent_response", "无响应"))

        return report

    async def interactive_mode(self):
        """交互模式 - 持续接受用户查询"""
        print("\n" + "=" * 60)
        print("交互模式 - 输入你的研究问题，或输入 'quit' 退出")
        print("=" * 60)

        while True:
            try:
                query = input("\n> ").strip()
                if not query:
                    continue
                if query.lower() in ['quit', 'exit', 'q']:
                    print("再见！")
                    break

                await self.research(query)

            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except Exception as e:
                print(f"错误: {e}")


async def main():
    """主函数"""
    # 创建研究助手（启用 LLM）
    assistant = ResearchAssistant(use_llm=True)

    # 初始化
    await assistant.initialize()

    # 执行示例研究
    print("\n" + "=" * 60)
    print("执行示例研究...")
    print("=" * 60)

    queries = [
        "什么是大语言模型？",
        "RAG 是什么？",
        "人工智能和机器学习有什么关系？",
    ]

    # 保存结果到文件
    results_file = "research_results.txt"

    for query in queries:
        print(f"\n[研究] {query}")
        report = await assistant.research(query)

        # 保存到文件
        with open(results_file, "a", encoding="utf-8") as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"研究主题: {query}\n")
            f.write(f"{'=' * 60}\n")
            f.write(f"来源数量: {len(report['sources'])}\n")
            for i, src in enumerate(report['sources'][:5], 1):
                f.write(f"\n[{i}] {src}\n")
            f.write(f"\nAgent 响应:\n{report['agent_response']}\n")

        await asyncio.sleep(0.5)

    print("\n" + "=" * 60)
    print("研究助手 Demo 完成！")
    print(f"结果已保存到: {results_file}")
    print("=" * 60)
    print("\n下次运行可以:")
    print("  1. 修改 knowledge 库内容")
    print("  2. 设置 API Key 启用 LLM 模式")
    print("  3. 将脚本导入到你的项目中使用")


if __name__ == "__main__":
    asyncio.run(main())
