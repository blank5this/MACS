"""MACS Live Demo Server.

A simple FastAPI server that exposes MACS agents via HTTP API.
Can be deployed to Railway, Render, or any WSGI-compatible host.

Usage:
    python demo_server.py

    # Then POST to http://localhost:8000/api/v1/execute
    curl -X POST http://localhost:8000/api/v1/execute \
      -H "Content-Type: application/json" \
      -d '{"task": "How do I submit a purchase requisition?", "mode": "hierarchical"}'

Deploy to Railway:
    1. Connect GitHub repo
    2. Set start command: `python demo_server.py`
    3. Set environment variable: MINIMAX_API_KEY=your_key
"""

from __future__ import annotations

import os
import asyncio
import uuid
import time
from typing import Any, Optional

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from macs_pkg import (
    RuntimeEngine, RuntimeConfig,
    MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent,
    MiniMaxProvider,
    ToolRegistry, RAGSearchTool,
    RAGEngine, RAGConfig,
    PlannerAgent, ExecutorAgent, ReviewerAgent,
)

# ─── Configuration ───────────────────────────────────────────────────────────────

API_KEY = os.environ.get("MINIMAX_API_KEY", "")
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
PORT = int(os.environ.get("PORT", "8000"))

# ─── FastAPI App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MACS Live Demo",
    description="Multi-Agent Collaboration System - Live API Demo",
    version="0.1.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Pydantic Models ────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    task: str = Field(..., description="Task description in natural language")
    mode: str = Field(default="hierarchical", description="Collaboration mode")
    use_rag: bool = Field(default=True, description="Enable RAG knowledge base")


class ExecuteResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_connected: bool
    memory_usage_mb: float


# ─── Global State ───────────────────────────────────────────────────────────────

_runtime: Optional[RuntimeEngine] = None
_rag_engine: Optional[RAGEngine] = None
_provider: Optional[MiniMaxProvider] = None


def _build_runtime() -> RuntimeEngine:
    """Build or return cached runtime engine."""
    global _runtime, _rag_engine, _provider

    if _runtime is not None:
        return _runtime

    # Create RAG engine
    rag_config = RAGConfig(
        embedder_provider="chinese_char_ngram",
        vector_store_type="memory",
        embedding_dim=384,
        chunk_size=200,
        chunk_overlap=30,
        default_top_k=3,
        similarity_threshold=0.0,
    )
    _rag_engine = RAGEngine(rag_config)

    # Load demo knowledge
    DEMO_KNOWLEDGE = [
        {
            "content": (
                "【采购申请流程】1. 员工登录ERP系统，点击'采购申请' "
                "2. 填写申请单：商品名称、数量、预算金额 "
                "3. 金额<1万主管直接审批，>=1万需财务复核 "
                "4. 提交后等待审批通知 5. 审批通过后系统自动生成采购订单"
            ),
            "metadata": {"source": "采购模块", "category": "采购申请"},
        },
        {
            "content": (
                "【供应商管理】- 供应商评级：A级(长期合作)、B级(合格)、C级(试用) "
                "- 付款条件：月结30天、票到付款、预付30%"
            ),
            "metadata": {"source": "供应商模块", "category": "供应商管理"},
        },
        {
            "content": (
                "【库存管理】- 安全库存预警：库存低于安全线时自动提醒 "
                "- 补货策略：定量补货、定期补货、安全库存补货 "
                "- 盘点：月度盘点、年度盘点、抽盘"
            ),
            "metadata": {"source": "库存模块", "category": "库存管理"},
        },
    ]

    asyncio.run(_rag_engine.add_documents(
        [doc["content"] for doc in DEMO_KNOWLEDGE],
        [doc["metadata"] for doc in DEMO_KNOWLEDGE],
    ))

    # Create LLM provider
    if API_KEY:
        _provider = MiniMaxProvider(api_key=API_KEY, model="MiniMax-M2.7")
    else:
        _provider = None

    # Create tool registry
    tool_registry = ToolRegistry()
    rag_tool = RAGSearchTool(
        rag_engine=_rag_engine,
        name="erp_knowledge_search",
        description="搜索ERP知识库，查找采购、供应商、库存相关政策",
        top_k=3,
    )
    tool_registry.register(rag_tool)

    # Create agents
    runtime = RuntimeEngine(RuntimeConfig(
        enable_tracing=True,
        default_mode="hierarchical",
        log_level="DEBUG" if DEBUG else "INFO",
    ))

    if _provider:
        planner = MiniMaxPlannerAgent("planner", provider=_provider)
        executor = MiniMaxExecutorAgent("executor", provider=_provider, tool_registry=tool_registry)
        reviewer = MiniMaxReviewerAgent("reviewer", provider=_provider)
    else:
        planner = PlannerAgent("planner")
        executor = ExecutorAgent("executor")
        reviewer = ReviewerAgent("reviewer")

    runtime.register_agent(planner)
    runtime.register_agent(executor)
    runtime.register_agent(reviewer)

    _runtime = runtime
    return runtime


# ─── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)

    llm_connected = False
    if API_KEY and _provider:
        try:
            from macs_pkg.llm.base import LLMMessage
            result = await asyncio.wait_for(
                _provider.complete([LLMMessage(role="user", content="hi")], max_tokens=5),
                timeout=5.0,
            )
            llm_connected = len(result.content) > 0
        except Exception:
            llm_connected = False

    return HealthResponse(
        status="healthy",
        version="0.1.1",
        llm_connected=llm_connected,
        memory_usage_mb=round(memory_mb, 1),
    )


@app.post("/api/v1/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    """Execute a task via MACS agents."""
    start = time.time()

    try:
        runtime = _build_runtime()

        task_dict = {
            "type": "erp_qa",
            "description": req.task,
            "requirements": [
                "先从知识库检索相关内容" if req.use_rag else "直接回答",
                "结合检索结果回答" if req.use_rag else "",
                "给出具体的操作步骤或政策说明",
            ],
        }

        result = await runtime.execute(task_dict, mode=req.mode)
        duration_ms = (time.time() - start) * 1000

        return ExecuteResponse(
            task_id=str(uuid.uuid4())[:8],
            status="success",
            result=result,
            duration_ms=round(duration_ms, 2),
        )

    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return ExecuteResponse(
            task_id=str(uuid.uuid4())[:8],
            status="error",
            error=str(e),
            duration_ms=round(duration_ms, 2),
        )


@app.get("/api/v1/modes")
async def list_modes():
    """List available collaboration modes."""
    return {
        "modes": [
            {"name": "hierarchical", "description": "Planner → Executor → Reviewer"},
            {"name": "pipeline", "description": "Sequential pipeline through agents"},
            {"name": "decentralized", "description": "Peer-to-peer agent negotiation"},
        ]
    }


# ─── Main ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
