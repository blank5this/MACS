"""MCP Server 实现 - 基于 Transport + Session 构建完整的服务端。

MCPServer 负责:
- 管理多个 Session（支持多客户端）
- 注册工具、资源、Prompts
- 处理 MCP 协议消息
- 生命周期管理
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from loguru import logger

from .protocol import (
    MCPMessage,
    MCP_PROTOCOL_VERSION,
    ServerCapabilities,
    ClientCapabilities,
    Tool,
    create_notification,
)
from .transport import Transport, StdioTransport, HttpSSETransport
from .session import MCPSession, SessionConfig


# ──────────────────────────────────────────────────────────────────────────────
# Tool Handler Type
# ──────────────────────────────────────────────────────────────────────────────

ToolHandler = Callable[..., Awaitable[Any]]


# ──────────────────────────────────────────────────────────────────────────────
# MCPServer
# ──────────────────────────────────────────────────────────────────────────────

class MCPServer:
    """MCP Server - 提供工具/资源/prompts 的服务端。

    支持两种运行模式:
    - stdio: 接收子进程通信（用于 CLI 工具）
    - http: 通过 HTTP/SSE 接收请求（用于网络服务）

    使用示例::

        server = MCPServer(name="my-server", version="1.0.0")

        # 注册工具
        @server.tool(name="search", description="Search the web")
        async def search(query: str) -> str:
            return f"Results for: {query}"

        # 启动 stdio 模式
        await server.run_stdio()
    """

    def __init__(
        self,
        name: str = "macs-mcp-server",
        version: str = "0.1.0",
        capabilities: Optional[ServerCapabilities] = None,
    ):
        self._name = name
        self._version = version
        self._capabilities = capabilities or ServerCapabilities(
            tools=True,
            resources=False,
            prompts=False,
            logging=True,
        )

        # 工具注册
        self._tools: Dict[str, Tool] = {}
        self._tool_handlers: Dict[str, ToolHandler] = {}

        # Session 管理
        self._sessions: Dict[str, MCPSession] = {}
        self._transport: Optional[Transport] = None
        self._running = False

        # 服务器信息
        self._server_info = {
            "name": name,
            "version": version,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Tool Registration
    # ──────────────────────────────────────────────────────────────────────────

    def tool(
        self,
        name: str,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """装饰器方式注册工具。

        使用示例::

            @server.tool(name="search", description="Search the web")
            async def search(query: str) -> str:
                return f"Results for: {query}"
        """
        def decorator(handler: ToolHandler) -> ToolHandler:
            self.register_tool(
                name=name,
                handler=handler,
                description=description,
                input_schema=input_schema or self._infer_schema(handler),
            )
            return handler
        return decorator

    def register_tool(
        self,
        name: str,
        handler: ToolHandler,
        description: str = "",
        input_schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """注册工具。

        Args:
            name: 工具名称
            handler: 异步处理函数
            description: 工具描述
            input_schema: 输入参数 schema
        """
        schema = input_schema or self._infer_schema(handler)

        self._tools[name] = Tool(
            name=name,
            description=description or handler.__doc__ or "",
            inputSchema=schema,
        )
        self._tool_handlers[name] = handler
        logger.debug(f"Tool registered: {name}")

    def _infer_schema(self, handler: ToolHandler) -> Dict[str, Any]:
        """从函数签名推断 schema（简单实现）。"""
        import inspect

        sig = inspect.signature(handler)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = "string"
            if param.annotation is int:
                param_type = "integer"
            elif param.annotation is float:
                param_type = "number"
            elif param.annotation is bool:
                param_type = "boolean"
            elif param.annotation in (list, List):
                param_type = "array"
            elif param.annotation is dict:
                param_type = "object"

            properties[param_name] = {
                "type": param_type,
            }

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required if required else None,
        }

    def list_tools(self) -> List[Tool]:
        """列出所有已注册的工具。"""
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具定义。"""
        return self._tools.get(name)

    # ──────────────────────────────────────────────────────────────────────────
    # Session Management
    # ──────────────────────────────────────────────────────────────────────────

    def _create_session_config(self) -> SessionConfig:
        """创建 session 配置。"""
        return SessionConfig(
            protocol_version=MCP_PROTOCOL_VERSION,
            server_info=self._server_info,
            capabilities=self._capabilities,
        )

    async def _handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Any:
        """处理工具调用。"""
        handler = self._tool_handlers.get(name)
        if not handler:
            raise ValueError(f"Tool not found: {name}")

        try:
            result = await handler(**arguments)
            return result
        except Exception as e:
            logger.error(f"Tool {name} execution failed: {e}")
            raise

    async def _dispatch_message(self, message: MCPMessage) -> Optional[MCPMessage]:
        """分发消息到相应处理器。"""
        method = message.method
        if not method:
            return None

        # Handle initialize
        if method == "initialize":
            return MCPMessage.response(
                id=message.id,
                result={
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": self._capabilities.to_dict(),
                    "serverInfo": self._server_info,
                },
            )

        # Handle tools/list
        if method == "tools/list":
            return MCPMessage.response(
                id=message.id,
                result={
                    "tools": [t.to_dict() for t in self._tools.values()],
                },
            )

        # Handle tools/call
        if method == "tools/call":
            params = message.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                return MCPMessage.error_response(
                    id=message.id,
                    code=-32001,
                    message="Tool name required",
                )

            if tool_name not in self._tool_handlers:
                return MCPMessage.error_response(
                    id=message.id,
                    code=-32001,
                    message=f"Tool not found: {tool_name}",
                )

            try:
                result = await self._handle_tool_call(tool_name, arguments)
                return MCPMessage.response(
                    id=message.id,
                    result={
                        "content": [
                            {"type": "text", "text": str(result)}
                        ]
                    },
                )
            except Exception as e:
                return MCPMessage.error_response(
                    id=message.id,
                    code=-32603,
                    message=str(e),
                )

        # Handle other methods
        return MCPMessage.error_response(
            id=message.id,
            code=-32601,
            message=f"Method not implemented: {method}",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Server Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    async def run_stdio(self) -> None:
        """以 stdio 模式运行（子进程模式）。"""
        logger.info("Starting MCP Server in stdio mode")

        transport = StdioTransport()
        self._transport = transport

        # 创建 session
        session = MCPSession(transport, self._create_session_config())

        # 注册所有工具到 session
        for name, tool in self._tools.items():
            session.register_tool(
                name=name,
                handler=self._tool_handlers[name],
                schema=tool.inputSchema,
            )

        self._sessions["stdio"] = session

        # 运行 session
        await session.run()

    async def run_http(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
    ) -> None:
        """以 HTTP/SSE 模式运行（网络服务模式）。"""
        logger.info(f"Starting MCP Server on {host}:{port}")

        try:
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp required for HTTP mode. Install: pip install aiohttp")
            raise

        app = web.Application()

        # 注册路由
        app.router.add_post("/", self._handle_http_jsonrpc)
        app.router.add_get("/sse", self._handle_sse)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, host, port)
        await site.start()

        logger.info(f"MCP Server listening on http://{host}:{port}")

        self._running = True
        try:
            # 保持运行
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()

    async def _handle_http_jsonrpc(self, request: web.Request) -> web.Response:
        """处理 JSON-RPC 请求。"""
        try:
            data = await request.json()
            message = MCPMessage.from_dict(data)

            response = await self._dispatch_message(message)
            if response is None:
                return web.json_response({}, status=204)

            return web.json_response(response.to_dict())
        except Exception as e:
            logger.error(f"HTTP JSON-RPC handler error: {e}")
            return web.json_response(
                MCPMessage.error_response(
                    id=None,
                    code=-32603,
                    message=str(e),
                ).to_dict(),
                status=500,
            )

    async def _handle_sse(self, request: web.Request) -> web.StreamResponse:
        """处理 SSE 连接（服务端推送）。"""
        response = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

        await response.prepare(request)

        try:
            while self._running:
                # 发送心跳
                await response.write(b"data: ping\n\n")
                await asyncio.sleep(30)
        except (asyncio.CancelledError, ConnectionResetError):
            pass

        return response

    async def stop(self) -> None:
        """停止 MCP Server。"""
        logger.info("Stopping MCP Server")
        self._running = False

        for session in self._sessions.values():
            await session.close()

        self._sessions.clear()

        if self._transport:
            await self._transport.close()

    # ──────────────────────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def is_running(self) -> bool:
        return self._running


__all__ = [
    "MCPServer",
    "ToolHandler",
]