"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


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