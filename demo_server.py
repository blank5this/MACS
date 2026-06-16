"""MACS Live Demo Server — Production-ready with Auth, Rate Limit, Session Memory.

A FastAPI server that exposes MACS agents via HTTP API.
Features:
- Per-user API key authentication
- Token budget tracking and rate limiting
- Session memory for conversation context
- Guardrails (input validation, blocked topics)

Deploy to Railway:
    1. Connect GitHub repo
    2. Set start command: `python demo_server.py`
    3. Set environment variables:
       - MINIMAX_API_KEY=your_key
       - API_KEYS=user1:sk-xxx,user2:sk-yyy (optional, comma-separated)
       - ENABLE_GUARDRAILS=true
"""

from __future__ import annotations

import os
import asyncio
import uuid
import time
import hashlib
from typing import Any, Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Header, Depends
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
from macs_pkg.utils import (
    AgentGuardrails, GuardrailsConfig, SecurityError,
    TokenBudget, TokenBudgetConfig, BudgetExceededError,
    SessionMemory,
)

# ─── Configuration ───────────────────────────────────────────────────────────────

API_KEY = os.environ.get("MINIMAX_API_KEY", "")
CONFIGURED_KEYS = os.environ.get("API_KEYS", "")  # Format: user1:sk-xxx,user2:sk-yyy
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
PORT = int(os.environ.get("PORT", "8000"))
ENABLE_GUARDRAILS = os.environ.get("ENABLE_GUARDRAILS", "true").lower() == "true"

# ─── Auth / Rate Limit Setup ───────────────────────────────────────────────────

def _parse_api_keys() -> dict:
    """Parse API_KEYS env var into {user_id: api_key} dict."""
    result = {}
    if not CONFIGURED_KEYS:
        return result
    for entry in CONFIGURED_KEYS.split(","):
        parts = entry.strip().split(":", 1)
        if len(parts) == 2:
            result[parts[0]] = parts[1]
    return result


def _hash_key(key: str) -> str:
    """Hash an API key for safe storage/logging."""
    return hashlib.sha256(key.encode()).hexdigest()[:12]


# Global instances
_api_keys = _parse_api_keys()
_token_budget = TokenBudget(TokenBudgetConfig(
    daily_limit=200_000,
    monthly_limit=2_000_000,
))
_session_memory: Optional[SessionMemory] = None
_guardrails: Optional[AgentGuardrails] = None

if ENABLE_GUARDRAILS:
    _guardrails = AgentGuardrails(GuardrailsConfig(
        blocked_topics=["密码", "password", "信用卡", "credit card", "ssn", "身份证"],
        max_tool_calls=10,
        max_iterations=5,
    ))

# In-memory rate limiting: user -> (timestamp, count)
_rate_limit_store: dict = defaultdict(list)  # user_id -> list of request timestamps
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 20      # max requests per window per user


def _check_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Validate API key from X-API-Key header. Returns user_id or 'anonymous'."""
    if not x_api_key:
        if not API_KEY:
            return "anonymous"
        # Single key mode: any request with this key is valid
        return "single_key"

    # Multi-key mode
    for user_id, key in _api_keys.items():
        if key == x_api_key:
            return user_id

    raise HTTPException(status_code=401, detail="Invalid API key")


def _check_rate_limit(user_id: str) -> None:
    """Check and update rate limit for user."""
    now = time.time()
    # Remove old entries
    _rate_limit_store[user_id] = [
        ts for ts in _rate_limit_store[user_id]
        if now - ts < RATE_LIMIT_WINDOW
    ]
    if len(_rate_limit_store[user_id]) >= RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX} requests per {RATE_LIMIT_WINDOW}s."
        )
    _rate_limit_store[user_id].append(now)


# ─── FastAPI App ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MACS Live Demo",
    description="Multi-Agent Collaboration System - Production API",
    version="0.2.0",
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
    task: str = Field(..., description="Task description")
    mode: str = Field(default="hierarchical")
    use_rag: bool = Field(default=True)
    session_id: Optional[str] = Field(default=None, description="Session ID for context")


class ExecuteResponse(BaseModel):
    task_id: str
    session_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: float
    tokens_used: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_connected: bool
    memory_usage_mb: float
    active_sessions: int


class TokenUsageResponse(BaseModel):
    user_id: str
    daily_tokens: int
    daily_limit: int
    monthly_tokens: int
    monthly_limit: int


# ─── Global State ────────────────────────────────────────────────────────────────

_runtime: Optional[RuntimeEngine] = None
_rag_engine: Optional[RAGEngine] = None
_provider: Optional[MiniMaxProvider] = None


async def _build_runtime() -> RuntimeEngine:
    global _runtime, _rag_engine, _provider

    if _runtime is not None:
        return _runtime

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

    await _rag_engine.add_documents(
        [doc["content"] for doc in DEMO_KNOWLEDGE],
        [doc["metadata"] for doc in DEMO_KNOWLEDGE],
    )

    if API_KEY:
        _provider = MiniMaxProvider(api_key=API_KEY, model="MiniMax-M2.7")
    else:
        _provider = None

    tool_registry = ToolRegistry()
    rag_tool = RAGSearchTool(
        rag_engine=_rag_engine,
        name="erp_knowledge_search",
        description="搜索ERP知识库，查找采购、供应商、库存相关政策",
        top_k=3,
    )
    tool_registry.register(rag_tool)

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
async def health(user_id: str = Depends(_check_api_key)):
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

    session_count = _session_memory.session_count() if _session_memory else 0

    return HealthResponse(
        status="healthy",
        version="0.2.0",
        llm_connected=llm_connected,
        memory_usage_mb=round(memory_mb, 1),
        active_sessions=session_count,
    )


@app.post("/api/v1/execute", response_model=ExecuteResponse)
async def execute(
    req: ExecuteRequest,
    user_id: str = Depends(_check_api_key),
):
    # Rate limit check
    _check_rate_limit(user_id)

    # Guardrails check
    if _guardrails:
        try:
            _guardrails.check_input(req.task)
        except SecurityError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Budget check
    session_id = req.session_id or f"req_{str(uuid.uuid4())[:8]}"

    try:
        _token_budget.check_available("MiniMax-M2.7", estimated_tokens=2000)
    except BudgetExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))

    start = time.time()

    try:
        runtime = await _build_runtime()

        # Get session context (for conversation continuity)
        session_context = ""
        if _session_memory and session_id:
            history = await _session_memory.get(session_id, limit=10)
            if history:
                turns = [f"{t.role}: {t.content}" for t in history]
                session_context = "\n\n[Conversation History]\n" + "\n".join(turns[-6:]) + "\n\n"

        task_desc = req.task
        if session_context:
            task_desc = f"{session_context}\n[Current Question]\n{req.task}"

        task_dict = {
            "type": "erp_qa",
            "description": task_desc,
            "requirements": [
                "先从知识库检索相关内容" if req.use_rag else "直接回答",
                "结合检索结果回答" if req.use_rag else "",
                "给出具体的操作步骤或政策说明",
            ],
        }

        result = await runtime.execute(task_dict, mode=req.mode)
        duration_ms = (time.time() - start) * 1000

        # Track token usage (estimate: ~2 tokens per char for Chinese)
        if _provider:
            token_estimate = int((len(req.task) + len(str(result))) * 2)
            _token_budget.track("MiniMax-M2.7", token_estimate, token_estimate // 2)

        # Store in session memory
        if _session_memory:
            await _session_memory.add(session_id, "user", req.task)
            if isinstance(result, dict):
                result_text = result.get("final_output", str(result))
            else:
                result_text = str(result)
            await _session_memory.add(session_id, "assistant", result_text)

        return ExecuteResponse(
            task_id=str(uuid.uuid4())[:8],
            session_id=session_id,
            status="success",
            result=result,
            duration_ms=round(duration_ms, 2),
            tokens_used=None,
        )

    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        return ExecuteResponse(
            task_id=str(uuid.uuid4())[:8],
            session_id=session_id,
            status="error",
            error=str(e),
            duration_ms=round(duration_ms, 2),
        )


@app.get("/api/v1/modes")
async def list_modes():
    return {
        "modes": [
            {"name": "hierarchical", "description": "Planner → Executor → Reviewer"},
            {"name": "pipeline", "description": "Sequential pipeline through agents"},
            {"name": "decentralized", "description": "Peer-to-peer agent negotiation"},
        ]
    }


@app.get("/api/v1/usage/{target_user}", response_model=TokenUsageResponse)
async def get_usage(target_user: str, user_id: str = Depends(_check_api_key)):
    """Get token usage for a user (admin endpoint)."""
    usage = _token_budget.get_usage()
    user_data = usage["models"].get(target_user, {})
    return TokenUsageResponse(
        user_id=target_user,
        daily_tokens=user_data.get("daily_tokens", 0),
        daily_limit=_token_budget.config.daily_limit,
        monthly_tokens=user_data.get("monthly_tokens", 0),
        monthly_limit=_token_budget.config.monthly_limit,
    )


@app.post("/api/v1/session/{session_id}/clear")
async def clear_session(session_id: str, user_id: str = Depends(_check_api_key)):
    """Clear a session's conversation history."""
    if _session_memory:
        await _session_memory.clear(session_id)
    return {"status": "ok", "session_id": session_id}


# ─── Main ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    _session_memory = SessionMemory(ttl_seconds=3600)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
