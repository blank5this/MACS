"""统一错误码定义 - MACS 错误处理标准化."""

from enum import Enum
from typing import Optional, Dict, Any


class MACSErrorCode(Enum):
    """MACS 系统错误码.

    错误码格式: CATEGORY_CODE (如 ERR_AGENT_001)
    - AGENT: Agent 相关错误 (0xxx)
    - COLLAB: 协作模式错误 (1xxx)
    - LLM: LLM provider 错误 (2xxx)
    - MEMORY: 记忆系统错误 (3xxx)
    - TOOL: 工具调用错误 (4xxx)
    - RUNTIME: 运行时错误 (5xxx)
    - CONFIG: 配置错误 (6xxx)
    """

    # Agent 错误 (0xxx)
    ERR_AGENT_001 = ("AGENT_001", "Agent初始化失败", "Agent initialization failed")
    ERR_AGENT_002 = ("AGENT_002", "Agent响应超时", "Agent response timeout")
    ERR_AGENT_003 = ("AGENT_003", "Agent状态无效", "Invalid agent state")
    ERR_AGENT_004 = ("AGENT_004", "Agent消息格式错误", "Invalid agent message format")

    # 协作模式错误 (1xxx)
    ERR_COLLAB_001 = ("COLLAB_001", "协作模式不支持该操作", "Collaboration mode does not support this operation")
    ERR_COLLAB_002 = ("COLLAB_002", "共识未达成", "Consensus not reached")
    ERR_COLLAB_003 = ("COLLAB_003", "投票轮次超限", "Voting rounds exceeded")
    ERR_COLLAB_004 = ("COLLAB_004", "无效的提案", "Invalid proposal")

    # LLM 错误 (2xxx)
    ERR_LLM_001 = ("LLM_001", "LLM Provider未初始化", "LLM provider not initialized")
    ERR_LLM_002 = ("LLM_002", "LLM API调用失败", "LLM API call failed")
    ERR_LLM_003 = ("LLM_003", "LLM响应格式错误", "Invalid LLM response format")
    ERR_LLM_004 = ("LLM_004", "LLM API Key无效", "Invalid API key")

    # 记忆系统错误 (3xxx)
    ERR_MEMORY_001 = ("MEMORY_001", "记忆存储失败", "Failed to store memory")
    ERR_MEMORY_002 = ("MEMORY_002", "记忆检索失败", "Failed to retrieve memory")
    ERR_MEMORY_003 = ("MEMORY_003", "共享记忆未初始化", "Shared memory not initialized")
    ERR_MEMORY_004 = ("MEMORY_004", "MemPalace连接失败", "MemPalace connection failed")

    # 工具错误 (4xxx)
    ERR_TOOL_001 = ("TOOL_001", "工具不存在", "Tool not found")
    ERR_TOOL_002 = ("TOOL_002", "工具执行失败", "Tool execution failed")
    ERR_TOOL_003 = ("TOOL_003", "工具注册失败", "Tool registration failed")
    ERR_TOOL_004 = ("TOOL_004", "工具参数无效", "Invalid tool parameters")

    # 运行时错误 (5xxx)
    ERR_RUNTIME_001 = ("RUNTIME_001", "任务执行失败", "Task execution failed")
    ERR_RUNTIME_002 = ("RUNTIME_002", "子任务执行失败", "Subtask execution failed")
    ERR_RUNTIME_003 = ("RUNTIME_003", "无效的执行结果", "Invalid execution result")
    ERR_RUNTIME_004 = ("RUNTIME_004", "系统状态错误", "Invalid system state")

    # 配置错误 (6xxx)
    ERR_CONFIG_001 = ("CONFIG_001", "无效的配置参数", "Invalid configuration parameter")
    ERR_CONFIG_002 = ("CONFIG_002", "缺少必需配置", "Missing required configuration")
    ERR_CONFIG_003 = ("CONFIG_003", "配置值超出范围", "Configuration value out of range")

    @property
    def code(self) -> str:
        return self.value[0]

    @property
    def message_cn(self) -> str:
        return self.value[1]

    @property
    def message_en(self) -> str:
        return self.value[2]

    def __str__(self) -> str:
        return f"[{self.code}] {self.message_cn} ({self.message_en})"


class MACSException(Exception):
    """MACS 基础异常类.

    所有 MACS 自定义异常的基类，提供统一的错误格式。

    Attributes:
        code: 错误码
        message: 错误消息
        details: 详细错误信息
        cause: 原始异常
    """

    def __init__(
        self,
        code: MACSErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        self.code = code
        self.message = message or code.message_cn
        self.details = details or {}
        self.cause = cause

        full_message = f"[{code.code}] {self.message}"
        if details:
            full_message += f" | details: {details}"
        if cause:
            full_message += f" | caused by: {type(cause).__name__}: {str(cause)}"

        super().__init__(full_message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化."""
        return {
            "error_code": self.code.code,
            "message": self.message,
            "message_en": self.code.message_en,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


# ============ 专用异常类 ============


class AgentException(MACSException):
    """Agent 相关异常."""

    def __init__(
        self,
        code: MACSErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        if not code.name.startswith("ERR_AGENT"):
            code = MACSErrorCode.ERR_AGENT_001
        super().__init__(code, message, details, cause)


class CollaborationException(MACSException):
    """协作模式相关异常."""

    def __init__(
        self,
        code: MACSErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        if not code.name.startswith("ERR_COLLAB"):
            code = MACSErrorCode.ERR_COLLAB_001
        super().__init__(code, message, details, cause)


class LLMException(MACSException):
    """LLM Provider 相关异常."""

    def __init__(
        self,
        code: MACSErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        if not code.name.startswith("ERR_LLM"):
            code = MACSErrorCode.ERR_LLM_001
        super().__init__(code, message, details, cause)


class MemoryException(MACSException):
    """记忆系统相关异常."""

    def __init__(
        self,
        code: MACSErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        if not code.name.startswith("ERR_MEMORY"):
            code = MACSErrorCode.ERR_MEMORY_001
        super().__init__(code, message, details, cause)


class ToolException(MACSException):
    """工具调用相关异常."""

    def __init__(
        self,
        code: MACSErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        if not code.name.startswith("ERR_TOOL"):
            code = MACSErrorCode.ERR_TOOL_001
        super().__init__(code, message, details, cause)


class RuntimeException(MACSException):
    """运行时相关异常."""

    def __init__(
        self,
        code: MACSErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        if not code.name.startswith("ERR_RUNTIME"):
            code = MACSErrorCode.ERR_RUNTIME_001
        super().__init__(code, message, details, cause)


class ConfigException(MACSException):
    """配置相关异常."""

    def __init__(
        self,
        code: MACSErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        if not code.name.startswith("ERR_CONFIG"):
            code = MACSErrorCode.ERR_CONFIG_001
        super().__init__(code, message, details, cause)
