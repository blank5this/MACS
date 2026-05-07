# Contributing to MACS

感谢您对 MACS 的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 1. 报告问题
- 使用 GitHub Issues 报告 Bug
- 描述清晰的问题复现步骤
- 提供相关日志和配置信息

### 2. 功能建议
- 在 GitHub Discussions 中提出想法
- 描述使用场景和预期行为
- 考虑与其他功能的兼容性

### 3. 代码贡献

#### 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/blank5this/MACS.git
cd MACS

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 开发流程
1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 进行开发并编写测试
4. 确保所有测试通过 (`pytest`)
5. 提交更改 (`git commit -m 'Add amazing feature'`)
6. 推送到分支 (`git push origin feature/amazing-feature`)
7. 创建 Pull Request

### 4. 添加新的 LLM Provider

参考现有 Provider 实现：

```python
# macs_pkg/llm/your_provider.py
from .base import LLMMessage, LLMProvider, LLMResponse

class YourProvider(LLMProvider):
    """你的 Provider 描述."""
    
    BASE_URL = "https://api.your-provider.com/v1"
    
    def __init__(self, api_key: str = None, model: str = "default"):
        self._api_key = api_key or os.environ.get("YOUR_API_KEY", "")
        self._model = model
    
    def model_name(self) -> str:
        return self._model
    
    async def complete(self, messages, system=None, tools=None, ...):
        # 实现 API 调用
        ...
```

然后在 `macs_pkg/llm/__init__.py` 中导出。

### 5. 添加新工具

```python
# macs_pkg/tools/your_tool.py
from typing import Any, Dict
from pydantic import BaseModel

class YourToolInput(BaseModel):
    """工具输入参数."""
    param1: str
    param2: int = 10

class YourTool(BaseTool):
    """你的工具描述."""
    
    name = "your_tool"
    description = "工具功能描述"
    input_model = YourToolInput
    
    async def _run(self, param1: str, param2: int = 10) -> str:
        # 实现工具逻辑
        return f"Result: {param1}, {param2}"
```

## 代码规范

- 遵循 PEP 8
- 使用 type hints
- 编写 docstrings
- 为新功能添加测试

## 测试

```bash
# 运行所有测试
pytest -v

# 带覆盖率
pytest --cov=macs_pkg --cov-report=html

# 只运行特定测试
pytest tests/test_llm.py -v
```

## 项目结构

```
macs_pkg/
├── core/           # 核心抽象
├── agents/        # Agent 实现
├── collaboration/ # 协作模式
├── llm/           # LLM Provider
├── tools/         # 工具集
├── runtime/       # 运行时
├── memory/        # 记忆管理
├── rag/           # RAG 功能
└── mcp/           # MCP 协议支持
```

## 许可

通过贡献代码，您同意将其按 MIT 许可证发布。
