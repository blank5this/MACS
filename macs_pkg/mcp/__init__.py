"""MCP (Model Context Protocol) Support for MACS.

MCP 是一个让 AI Agent 与外部工具/数据源连接的协议标准。
参考: https://modelcontextprotocol.io

模块组成:
- protocol: MCP 协议定义（消息类型、常量、编解码）
- transport: 传输层（stdio、HTTP/SSE、内存）
- session: Session 管理（请求/响应配对、方法调度）
- server: MCPServer 实现（工具注册、生命周期管理）

使用示例 - MCP Client::

    from macs_pkg.mcp import MCPClient

    client = MCPClient()
    await client.connect("http://localhost:8000")
    tools = await client.list_tools()
    result = await client.call_tool("search", {"query": "..."})

使用示例 - MCP Server::

    from macs_pkg.mcp import MCPServer

    server = MCPServer(name="my-server", version="1.0.0")

    @server.tool(name="search", description="Search the web")
    async def search(query: str) -> str:
        return f"Results for: {query}"

    await server.run_http(port=8000)
"""

from __future__ import annotations

# Protocol
from .protocol import (
    MCP_PROTOCOL_VERSION,
    JSONRPC_VERSION,
    JSONRPCMethod,
    MCPMessage,
    MCPCode,
    ServerCapabilities,
    ClientCapabilities,
    ToolSchema,
    InitializeParams,
    InitializeResult,
    Tool,
    ToolCallResult,
    create_notification,
    is_notification,
    is_request,
    is_response,
)

# Transport
from .transport import (
    Transport,
    TransportError,
    TransportClosed,
    StdioTransport,
    HttpSSETransport,
    InMemoryTransport,
)

# Session
from .session import (
    SessionConfig,
    MethodHandler,
    NotificationHandler,
    MCPSession,
)

# Server
from .server import MCPServer, ToolHandler

# Re-export MCPClient from original implementation
from .client import MCPClient, MCPError, MCPConnectionError, MCPTool, MCPCapabilities


__all__ = [
    # Protocol
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
    # Transport
    "Transport",
    "TransportError",
    "TransportClosed",
    "StdioTransport",
    "HttpSSETransport",
    "InMemoryTransport",
    # Session
    "SessionConfig",
    "MethodHandler",
    "NotificationHandler",
    "MCPSession",
    # Server
    "MCPServer",
    "ToolHandler",
    # Client (original)
    "MCPClient",
    "MCPError",
    "MCPConnectionError",
    "MCPTool",
    "MCPCapabilities",
]