"""MCP 协议定义 - 消息类型、常量、编解码。

参考 https://modelcontextprotocol.io/specification
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid


# ──────────────────────────────────────────────────────────────────────────────
# Protocol Constants
# ──────────────────────────────────────────────────────────────────────────────

MCP_PROTOCOL_VERSION = "2024-11-05"
JSONRPC_VERSION = "2.0"

# ──────────────────────────────────────────────────────────────────────────────
# JSON-RPC Message Types
# ──────────────────────────────────────────────────────────────────────────────

class JSONRPCMethod(Enum):
    """Standard JSON-RPC methods for MCP."""
    # Lifecycle
    INITIALIZE = "initialize"
    SHUTDOWN = "shutdown"
    NOTIFY = "notifications/"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"

    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # Logging
    LOGGING_SET_LEVEL = "logging/setLevel"


@dataclass
class MCPMessage:
    """MCP 协议消息封装。"""
    jsonrpc: str = JSONRPC_VERSION
    id: Union[str, int, None] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    @staticmethod
    def request(
        method: str,
        params: Optional[Dict[str, Any]] = None,
        id: Optional[Union[str, int]] = None,
    ) -> "MCPMessage":
        """创建请求消息。"""
        return MCPMessage(
            id=id or str(uuid.uuid4()),
            method=method,
            params=params or {},
        )

    @staticmethod
    def response(
        id: Union[str, int],
        result: Any,
    ) -> "MCPMessage":
        """创建响应消息。"""
        return MCPMessage(
            id=id,
            result=result,
        )

    @staticmethod
    def error_response(
        id: Union[str, int],
        code: int,
        message: str,
        data: Any = None,
    ) -> "MCPMessage":
        """创建错误响应消息。"""
        return MCPMessage(
            id=id,
            error={
                "code": code,
                "message": message,
                "data": data,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典。"""
        obj = {"jsonrpc": self.jsonrpc}
        if self.id is not None:
            obj["id"] = self.id
        if self.method is not None:
            obj["method"] = self.method
        if self.params is not None:
            obj["params"] = self.params
        if self.result is not None:
            obj["result"] = self.result
        if self.error is not None:
            obj["error"] = self.error
        return obj

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MCPMessage":
        """从字典反序列化。"""
        return MCPMessage(
            jsonrpc=data.get("jsonrpc", JSONRPC_VERSION),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )

    def to_json(self) -> str:
        """序列化为 JSON 字符串。"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @staticmethod
    def from_json(raw: str) -> "MCPMessage":
        """从 JSON 字符串反序列化。"""
        return MCPMessage.from_dict(json.loads(raw))


# ──────────────────────────────────────────────────────────────────────────────
# Error Codes
# ──────────────────────────────────────────────────────────────────────────────

class MCPCode(Enum):
    """MCP 错误码。"""
    # Standard JSON-RPC errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP specific
    TOOL_NOT_FOUND = -32001
    RESOURCE_NOT_FOUND = -32002
    CONNECTION_CLOSED = -32003


# ──────────────────────────────────────────────────────────────────────────────
# Capability Definitions
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ServerCapabilities:
    """MCP Server 能力声明。"""
    tools: bool = False
    resources: bool = False
    prompts: bool = False
    logging: bool = False

    def to_dict(self) -> Dict[str, Any]:
        caps = {}
        if self.tools:
            caps["tools"] = {}
        if self.resources:
            caps["resources"] = {}
        if self.prompts:
            caps["prompts"] = {}
        if self.logging:
            caps["logging"] = {}
        return caps


@dataclass
class ClientCapabilities:
    """MCP Client 能力声明。"""
    tools: bool = False
    resources: bool = False
    prompts: bool = False


# ──────────────────────────────────────────────────────────────────────────────
# Tool Schema (OpenAI compatible)
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ToolSchema:
    """工具参数 schema (OpenAI function calling 兼容)。"""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_openai_schema(self) -> Dict[str, Any]:
        """转换为 OpenAI tool schema 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# ──────────────────────────────────────────────────────────────────────────────
# Request/Response Types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class InitializeParams:
    """initialize 请求参数。"""
    protocolVersion: str = MCP_PROTOCOL_VERSION
    capabilities: ClientCapabilities = field(default_factory=ClientCapabilities)
    clientInfo: Optional[Dict[str, str]] = None


@dataclass
class InitializeResult:
    """initialize 响应结果。"""
    protocolVersion: str = MCP_PROTOCOL_VERSION
    capabilities: ServerCapabilities = field(default_factory=ServerCapabilities)
    serverInfo: Dict[str, str] = field(default_factory=dict)


@dataclass
class Tool:
    """MCP Tool 定义。"""
    name: str
    description: str
    inputSchema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema,
        }


@dataclass
class ToolCallResult:
    """tools/call 响应结果。"""
    content: List[Dict[str, Any]]  # [{type: "text"|"image", text?: str, data?: str}]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Protocol Helpers
# ──────────────────────────────────────────────────────────────────────────────

def create_notification(method: str, params: Optional[Dict[str, Any]] = None) -> MCPMessage:
    """创建通知消息（无 id）。"""
    return MCPMessage(method=method, params=params)


def is_notification(msg: MCPMessage) -> bool:
    """判断是否是通知消息。"""
    return msg.method is not None and msg.id is None


def is_request(msg: MCPMessage) -> bool:
    """判断是否是请求消息。"""
    return msg.method is not None and msg.id is not None


def is_response(msg: MCPMessage) -> bool:
    """判断是否是响应消息。"""
    return msg.result is not None or msg.error is not None


__all__ = [
    "MCP_PROTOCOL_VERSION",
    "JSONRPC_VERSION",
    "JSONRPCMethod",
    "MCPMessage",
    "MCPCode",
    "ServerCapabilities",
    "ClientCapabilities",
    "ToolSchema",
    "InitializeParams",
    "InitializeResult",
    "Tool",
    "ToolCallResult",
    "create_notification",
    "is_notification",
    "is_request",
    "is_response",
]