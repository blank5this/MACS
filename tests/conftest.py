"""Pytest configuration and fixtures."""

import pytest
import sys
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Mock LLM Provider
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing without real API calls."""
    class MockLLMResponse:
        def __init__(self, content="Mock response", tool_calls=None):
            self.content = content
            self.model = "mock-model"
            self.usage = {"input_tokens": 10, "output_tokens": 20}
            self.tool_calls = tool_calls or []
            self.stop_reason = "stop"

    class MockProvider:
        async def complete(self, messages, system=None, tools=None, max_tokens=1024, temperature=0.7, **kwargs):
            return MockLLMResponse(
                content='{"subtasks": [{"id": "subtask_1", "description": "Test subtask", "type": "execution", "priority": 1}]}'
            )

        def model_name(self):
            return "mock-model"

    return MockProvider()


@pytest.fixture
def mock_llm_provider_with_subtasks():
    """Mock LLM provider that returns subtasks for planner."""
    class MockLLMResponse:
        def __init__(self, content="Mock response", tool_calls=None):
            self.content = content
            self.model = "mock-model"
            self.usage = {"input_tokens": 10, "output_tokens": 20}
            self.tool_calls = tool_calls or []
            self.stop_reason = "stop"

    class MockProvider:
        async def complete(self, messages, system=None, tools=None, max_tokens=1024, temperature=0.7, **kwargs):
            return MockLLMResponse(
                content='{"subtasks": ['
                '{"id": "subtask_1", "description": "Step 1", "type": "execution", "priority": 1},'
                '{"id": "subtask_2", "description": "Step 2", "type": "execution", "priority": 2}]}'
            )

        def model_name(self):
            return "mock-model"

    return MockProvider()


@pytest.fixture
def mock_llm_provider_with_review():
    """Mock LLM provider that returns review approval."""
    class MockLLMResponse:
        def __init__(self, content="Mock response", tool_calls=None):
            self.content = content
            self.model = "mock-model"
            self.usage = {"input_tokens": 10, "output_tokens": 20}
            self.tool_calls = tool_calls or []
            self.stop_reason = "stop"

    class MockProvider:
        async def complete(self, messages, system=None, tools=None, max_tokens=1024, temperature=0.7, **kwargs):
            # Check if this is a review request
            content_str = str(messages[-1].content) if messages else ""
            if "review" in content_str.lower():
                return MockLLMResponse(content='{"action": "review_complete", "status": "approved", "feedback": "Looks good"}')
            return MockLLMResponse(content='{"result": "Review completed"}')

        def model_name(self):
            return "mock-model"

    return MockProvider()


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Sample Data
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_erp_knowledge():
    """Sample ERP knowledge base for testing."""
    return [
        {
            "content": "【采购申请流程】1. 员工点击采购申请 2. 填写商品名称、数量 3. 提交等待审批",
            "metadata": {"source": "采购模块", "category": "采购申请"},
        },
        {
            "content": "【供应商评级】A级(长期合作)、B级(合格)、C级(试用)",
            "metadata": {"source": "供应商模块", "category": "供应商管理"},
        },
        {
            "content": "【库存安全线】库存低于安全线时自动提醒，补货策略有三种",
            "metadata": {"source": "库存模块", "category": "库存管理"},
        },
    ]


@pytest.fixture
def sample_task():
    """Sample task for testing."""
    return {
        "description": "员工如何提交采购申请？金额超过1万怎么处理？",
        "requirements": ["先从知识库检索", "结合检索结果回答"],
    }


@pytest.fixture
def sample_tasks():
    """Multiple sample tasks for parametrized testing."""
    return [
        {"type": "erp_qa", "description": "员工如何提交采购申请？"},
        {"type": "erp_qa", "description": "供应商评级有哪些？"},
        {"type": "erp_qa", "description": "库存安全线是什么？"},
    ]


@pytest.fixture
def sample_agent_configs():
    """Sample agent configurations for runtime creation."""
    return [
        {"name": "planner", "role": "planner"},
        {"name": "executor", "role": "executor"},
        {"name": "reviewer", "role": "reviewer"},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Agent Mock Classes
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    from macs_pkg.core.agent import BaseAgent, AgentRole, Message

    class MockAgent(BaseAgent):
        def __init__(self, name="mock", role=AgentRole.EXECUTOR, responses=None):
            super().__init__(name, role)
            self.responses = responses or [{"result": f"Response from {name}"}]
            self.call_count = 0

        async def think(self, message: Message) -> Message:
            return Message(
                sender=self.name,
                content={"status": "thinking", "thought": f"{self.name} is thinking"},
                msg_type="thought",
            )

        async def act(self, response: Message) -> list:
            self.call_count += 1
            idx = min(self.call_count - 1, len(self.responses) - 1)
            response_text = self.responses[idx] if isinstance(self.responses[idx], str) else self.responses[idx]
            return [Message(sender=self.name, content=response_text, msg_type="action")]

    return MockAgent


@pytest.fixture
def mock_agents_factory(mock_agent):
    """Factory to create multiple mock agents."""
    def create_agents(names_and_roles):
        return [
            mock_agent(name=name, role=role)
            for name, role in names_and_roles
        ]
    return create_agents


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Collaboration Mode Setup
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def hierarchical_mode_setup(mock_agent):
    """Setup for hierarchical mode testing with planner, executor, reviewer."""
    from macs_pkg.collaboration.hierarchical import HierarchicalMode

    planner = mock_agent("planner", AgentRole.PLANNER, responses=[
        {"subtask": "Step 1: Analyze"},
        {"subtask": "Step 2: Plan"},
    ])
    executor = mock_agent("executor", AgentRole.EXECUTOR, responses=[
        {"result": "Executor completed task"}
    ])
    reviewer = mock_agent("reviewer", AgentRole.REVIEWER, responses=[
        {"action": "review_complete", "status": "approved"}
    ])

    mode = HierarchicalMode()
    mode._leader = planner
    mode._executors = [executor]
    mode._reviewer = reviewer

    return {
        "mode": mode,
        "planner": planner,
        "executor": executor,
        "reviewer": reviewer,
    }


@pytest.fixture
def pipeline_mode_setup(mock_agent):
    """Setup for pipeline mode testing."""
    from macs_pkg.collaboration.pipeline import PipelineMode

    agents = [
        mock_agent("agent1", responses=["Processed: Stage 1"]),
        mock_agent("agent2", responses=["Processed: Stage 2"]),
        mock_agent("agent3", responses=["Final result"]),
    ]

    mode = PipelineMode()
    mode._chain = agents

    return {"mode": mode, "agents": agents}


@pytest.fixture
def decentralized_mode_setup(mock_agent):
    """Setup for decentralized mode testing."""
    from macs_pkg.collaboration.decentralized import DecentralizedMode

    agents = [
        mock_agent("node1", responses=["Node1 proposal"]),
        mock_agent("node2", responses=["Node2 proposal"]),
        mock_agent("node3", responses=["Node3 proposal"]),
    ]

    mode = DecentralizedMode()
    mode._agents = agents

    return {"mode": mode, "agents": agents}


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Tool Mocks
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_tool_result():
    """Factory for creating mock tool results."""
    def create_result(success=True, output="test output", error=None):
        from macs_pkg.tools.base import ToolResult
        return ToolResult(success=success, output=output, error=error)
    return create_result


@pytest.fixture
def mock_registry_with_tools():
    """Create a tool registry with mock tools for testing."""
    from macs_pkg.tools.registry import ToolRegistry
    from macs_pkg.tools.base import BaseTool, ToolSpec, ToolResult

    class MockTool(BaseTool):
        def __init__(self, name="mock_tool", result_output="mock result"):
            self._name = name
            self._output = result_output

        @property
        def spec(self) -> ToolSpec:
            return ToolSpec(
                name=self._name,
                description="Mock tool for testing",
                parameters=[],
            )

        async def run(self, **kwargs) -> ToolResult:
            return ToolResult(success=True, output=self._output)

    registry = ToolRegistry()
    registry.register(MockTool(name="tool1", result_output="result1"))
    registry.register(MockTool(name="tool2", result_output="result2"))

    return registry


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Async Support
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures: Common Test Data
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def chinese_texts():
    """Chinese texts for embedding tests."""
    return [
        "这是一个中文句子用于测试嵌入功能",
        "采购申请流程包括提交、审批、执行三个步骤",
        "供应商管理涉及评级、付款、合同等内容",
        "库存管理需要设置安全线和补货策略",
        "财务审批流程包括报销、付款、对账等",
    ]


@pytest.fixture
def english_texts():
    """English texts for embedding tests."""
    return [
        "This is an English sentence for testing embedding.",
        "The procurement process includes submission, approval, and execution.",
        "Supplier management involves rating, payment, and contracts.",
        "Inventory management requires safety stock and replenishment strategies.",
        "Financial approval processes include reimbursement and payment reconciliation.",
    ]


@pytest.fixture
def json_test_data():
    """JSON data for parser tool tests."""
    return {
        "system": {
            "name": "MACS",
            "version": "0.1.0",
            "agents": 3,
            "mode": "hierarchical",
            "config": {
                "enable_memory": True,
                "enable_tracing": False,
            }
        },
        "users": [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "user"},
        ]
    }


@pytest.fixture
def file_test_content(tmp_path):
    """Create temporary test files."""
    content = "Test file content\nLine 2\nLine 3"
    test_file = tmp_path / "test.txt"
    test_file.write_text(content, encoding="utf-8")
    return {"path": test_file, "content": content}