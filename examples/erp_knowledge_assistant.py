"""ERP Knowledge Assistant - 完整的多Agent+RAG+可视化追踪演示

这个示例展示如何用 MACS 构建一个企业知识库问答助手：
- RAG 加载 ERP 操作手册
- Planner 分解用户问题
- Executor + RAG 检索回答
- Reviewer 验证答案质量
- ExecutionTracer 生成执行时序图

使用方式:
    python examples/erp_knowledge_assistant.py

面试时可展示的亮点:
    1. "我从零构建了多Agent协作框架，支持4种协作模式"
    2. "完整RAG pipeline：文档切分+Embedding+向量检索"
    3. "执行流程可视化：Tracer生成Mermaid时序图"
    4. "记忆系统：Agent能记住历史交互"
"""

import asyncio
import os

from macs_pkg import (
    # 核心
    RuntimeEngine, RuntimeConfig, create_runtime,
    AgentRole, Message,
    # LLM
    MiniMaxProvider,
    MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent,
    # RAG
    RAGEngine, RAGConfig,
    # Tools
    ToolRegistry, RAGSearchTool,
    # 可视化
    ExecutionTracer,
)


# ==================== ERP 知识库文档 ====================

ERP_KNOWLEDGE_BASE = [
    {
        "content": """
        【采购申请流程】
        1. 员工登录ERP系统，点击"采购申请"
        2. 填写申请单：商品名称、数量、预算金额、预计交付日期
        3. 选择审批流程：金额<1万主管直接审批，>=1万需财务复核
        4. 提交后等待审批通知
        5. 审批通过后，系统自动生成采购订单
        """,
        "metadata": {"source": "采购模块", "category": "采购申请"},
    },
    {
        "content": """
        【供应商管理】
        - 新增供应商：基础信息、银行账户、联系人
        - 供应商评级：A级(长期合作)、B级(合格)、C级(试用)
        - 付款条件：月结30天、票到付款、预付30%
        - 质量问题可发起供应商评估
        """,
        "metadata": {"source": "供应商模块", "category": "供应商管理"},
    },
    {
        "content": """
        【库存管理】
        - 安全库存预警：库存低于安全线时自动提醒
        - 补货策略：定量补货、定期补货、安全库存补货
        - 库存盘点：月度盘点、年度盘点、抽盘
        - 库位管理：ABC分类管理
        """,
        "metadata": {"source": "库存模块", "category": "库存管理"},
    },
    {
        "content": """
        【财务审批】
        - 差旅报销：票据粘贴→部门审批→财务复核→出纳付款
        - 采购付款：收货确认→发票校验→付款申请→出纳付款
        - 月末结账：应收结清、应付结清、凭证审核
        - 预算控制：超预算需额外审批
        """,
        "metadata": {"source": "财务模块", "category": "财务审批"},
    },
    {
        "content": """
        【销售订单】
        - 订单录入：客户名称、产品、数量、单价、交期
        - 价格折扣：标准价、品牌折扣、促销活动
        - 信用控制：超信用额度需特批
        - 发货通知：仓库备货→物流配送→客户签收
        """,
        "metadata": {"source": "销售模块", "category": "销售订单"},
    },
    {
        "content": """
        【系统管理】
        - 用户权限：系统管理员、部门管理员、普通用户
        - 角色定义：每个角色可配置不同功能权限
        - 数据权限：部门数据隔离、敏感数据加密
        - 审计日志：关键操作记录可追溯
        """,
        "metadata": {"source": "系统模块", "category": "系统管理"},
    },
]


async def main():
    print("=" * 70)
    print("  MACS ERP 知识助手 - 多Agent + RAG + 可视化追踪演示")
    print("=" * 70)
    print()

    # ==================== 1. 初始化 RAG 引擎 ====================
    print("[1/5] 初始化 RAG 知识库...")

    rag_config = RAGConfig(
        embedder_provider="chinese_char_ngram",
        vector_store_type="memory",
        chunk_size=200,
        chunk_overlap=30,
        default_top_k=3,
        similarity_threshold=0.0,
        embedding_dim=384,
    )

    rag_engine = RAGEngine(rag_config)

    # 加载 ERP 知识文档
    texts = [doc["content"] for doc in ERP_KNOWLEDGE_BASE]
    metadatas = [doc["metadata"] for doc in ERP_KNOWLEDGE_BASE]
    chunks_added = await rag_engine.add_documents(texts, metadatas)
    print(f"      已加载 {len(ERP_KNOWLEDGE_BASE)} 篇文档，切分 {chunks_added} 个知识块")
    print(f"      Embedding: {rag_config.embedder_provider}, VectorStore: {rag_config.vector_store_type}")
    print()

    # ==================== 2. 初始化 LLM Provider ====================
    print("[2/5] 初始化 LLM Provider...")

    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        print("      [!] MINIMAX_API_KEY 未设置，将使用模拟模式")
        provider = None
    else:
        provider = MiniMaxProvider(
            api_key=api_key,
            model="MiniMax-M2.7",
        )
        print(f"      Provider: MiniMax-M2.7")
    print()

    # ==================== 3. 创建 RuntimeEngine（启用追踪） ====================
    print("[3/5] 创建 Agent 团队（启用执行追踪）...")

    runtime = RuntimeEngine(RuntimeConfig(
        enable_shared_memory=True,
        enable_tracing=True,  # 关键：启用可视化追踪
        default_mode="hierarchical",
        log_level="INFO",
    ))

    # 创建带 RAG 能力的 Executor
    if provider:
        # 创建 RAG 搜索工具
        rag_tool = RAGSearchTool(
            rag_engine=rag_engine,
            name="erp_knowledge_search",
            description="搜索ERP知识库，查找采购申请、供应商管理、库存管理、财务审批、销售订单等相关政策和流程。",
            top_k=3,
        )

        # 创建工具注册表
        tool_registry = ToolRegistry()
        tool_registry.register(rag_tool)

        planner = MiniMaxPlannerAgent("planner", provider=provider)
        executor = MiniMaxExecutorAgent("executor", provider=provider, tool_registry=tool_registry)
        reviewer = MiniMaxReviewerAgent("reviewer", provider=provider)
        print(f"      Provider: MiniMax-Text-01")
        print(f"      Executor 已注册 RAG 搜索工具 (Agentic RAG)")
    else:
        from macs_pkg import PlannerAgent, ExecutorAgent, ReviewerAgent
        planner = PlannerAgent("planner")
        executor = ExecutorAgent("executor")
        reviewer = ReviewerAgent("reviewer")
        print("      Provider: Mock (无 API Key)")

    # 注册 Agent
    runtime.register_agent(planner)
    runtime.register_agent(executor)
    runtime.register_agent(reviewer)
    print(f"      已注册: planner, executor, reviewer")
    print()

    # ==================== 4. 初始化记忆系统 ====================
    print("[4/5] 初始化 MemPalace 记忆系统...")
    try:
        await runtime.init_shared_memory_async()
        for name in runtime.list_agents():
            agent = runtime.get_agent(name)
            if agent and hasattr(agent, 'init_memory'):
                await agent.init_memory()
        print("      记忆系统就绪")
    except Exception as e:
        print(f"      记忆系统暂不可用: {e}")
    print()

    # ==================== 5. 执行问答 ====================
    print("[5/5] 执行 ERP 知识问答...")
    print("-" * 70)

    questions = [
        "员工如何提交采购申请？金额超过1万怎么处理？",
        "供应商评级有哪些？付款条件是什么？",
        "库存安全线是什么？如何设置补货策略？",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n【问题 {i}】{question}")
        print("-" * 70)

        task = {
            "type": "erp_qa",
            "description": question,
            "requirements": [
                "先从知识库检索相关内容",
                "结合检索结果回答",
                "给出具体的操作步骤或政策说明",
            ],
        }

        result = await runtime.execute(task, mode="hierarchical")

        print(f"\n【回答】")
        if isinstance(result, dict):
            if "error" in result:
                print(f"  处理中出现问题: {result['error']}")
            else:
                # 简化输出
                output = str(result)[:500]
                print(f"  {output}...")
        else:
            print(f"  {str(result)[:500]}...")

    print("\n" + "=" * 70)

    # ==================== 6. 生成执行追踪报告 ====================
    print("\n【执行追踪报告】")
    print("=" * 70)

    tracer = runtime.get_tracer()
    if tracer:
        # 生成统计
        stats = tracer.generate_stats()
        print(f"\n[*] 执行统计:")
        print(f"   任务ID: {stats['task_id']}")
        print(f"   总耗时: {stats['total_duration_ms']:.2f}ms")
        print(f"   总事件数: {stats['total_events']}")
        print(f"   参与Agent: {', '.join(stats['agents'])}")

        print(f"\n[*] Agent统计:")
        for name, agent_stats in stats['agent_stats'].items():
            print(f"   [{name}]")
            print(f"     think调用: {agent_stats['think_count']}")
            print(f"     act调用: {agent_stats['act_count']}")
            print(f"     平均响应: {agent_stats['avg_think_time_ms']:.2f}ms")

        # 生成 Mermaid 时序图
        print(f"\n[*] Mermaid 时序图:")
        print("   (复制以下内容到 https://mermaid.live 查看)")
        print("-" * 70)
        mermaid = tracer.generate_mermaid_sequence()
        for line in mermaid.split("\n"):
            if line.startswith("```"):
                print(line)
            else:
                print(f"   {line}")
        print("-" * 70)

        # 打印完整报告
        print(tracer.print_stats())
    else:
        print("   追踪未启用")

    # ==================== 7. 记忆系统检查 ====================
    print("\n【记忆系统检查】")
    print("-" * 70)

    for name in runtime.list_agents():
        agent = runtime.get_agent(name)
        if agent and hasattr(agent, 'has_long_term_memory') and agent.has_long_term_memory():
            memories = await agent.get_all_long_term_memories(limit=3)
            print(f"   [{name}] 长期记忆: {len(memories)} 条")
        elif agent:
            print(f"   [{name}] 短期记忆: {len(agent.get_memory())} 条")

    print("\n" + "=" * 70)
    print("  ERP 知识助手演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
