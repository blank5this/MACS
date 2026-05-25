"""MCP Session 管理 - 处理 JSON-RPC 消息流、请求/响应配对。

Session 负责:
- 管理请求/响应的配对
- 处理方法调度
- 生命周期管理
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Callable, Awaitable, AsyncGenerator
from dataclasses import dataclass, field
from loguru import logger

from .protocol import (
    MCPMessage,
    MCP_PROTOCOL_VERSION,
    JSONRPC_VERSION,
    ServerCapabilities,
    ClientCapabilities,
    create_notification,
    is_notification,
    is_request,
    is_response,
    MCPCode,
)
from .transport import Transport, TransportClosed


# ──────────────────────────────────────────────────────────────────────────────
# Session Config
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SessionConfig:
    """Session 配置。"""
    protocol_version: str = MCP_PROTOCOL_VERSION
    server_info: Dict[str, str] = field(default_factory=lambda: {
        "name": "macs-mcp-server",
        "version": "0.1.0",
    })
    capabilities: ServerCapabilities = field(default_factory=ServerCapabilities)
    request_timeout: float = 30.0


# ──────────────────────────────────────────────────────────────────────────────
# Method Handler
# ──────────────────────────────────────────────────────────────────────────────

MethodHandler = Callable[[MCPMessage], Awaitable[MCPMessage]]
NotificationHandler = Callable[[MCPMessage], Awaitable[None]]


# ──────────────────────────────────────────────────────────────────────────────
# Session
# ──────────────────────────────────────────────────────────────────────────────

class MCPSession:
    """MCP Session - 管理与服务端的对话。

    Session 处理:
    - 协议初始化 (initialize)
    - 请求/响应配对
    - 方法调度
    - 工具调用
    """

    def __init__(
        self,
        transport: Transport,
        config: Optional[SessionConfig] = None,
    ):
        self._transport = transport
        self._config = config or SessionConfig()
        self._running = False
        self._initialized = False

        # 请求/响应配对
        self._pending_requests: Dict[str, asyncio.Future[MCPMessage]] = {}
        self._request_counter = 0

        # 方法处理器
        self._method_handlers: Dict[str, MethodHandler] = {}
        self._notification_handlers: Dict[str, NotificationHandler] = {}

        # 已注册的工具
        self._tools: Dict[str, Any] = {}
        self._tool_handlers: Dict[str, Callable] = {}

        # Server 能力
        self._server_capabilities = self._config.capabilities

        # 注册默认处理器
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """注册默认的方法处理器。"""
        self.add_method_handler("initialize", self._handle_initialize)
        self.add_method_handler("shutdown", self._handle_shutdown)
        self.add_notification_handler("exit", self._handle_exit)

    # ──────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """启动 session。"""
        if self._running:
            return

        await self._transport.start()
        self._running = True
        logger.info("MCPSession started")

    async def close(self) -> None:
        """关闭 session。"""
        self._running = False
        self._initialized = False

        # 取消所有待处理的请求
        for fut in self._pending_requests.values():
            if not fut.done():
                fut.cancel()

        self._pending_requests.clear()
        await self._transport.close()
        logger.info("MCPSession closed")

    async def run(self) -> None:
        """运行 session，处理传入消息。"""
        await self.start()

        try:
            async for message in self._transport.receive():
                await self._dispatch(message)
        except TransportClosed:
            logger.info("Transport closed, session ending")
        except asyncio.CancelledError:
            logger.info("Session cancelled")
        except Exception as e:
            logger.error(f"Session error: {e}")
            raise

        await self.close()

    # ──────────────────────────────────────────────────────────────────────────
    # Message Dispatch
    # ──────────────────────────────────────────────────────────────────────────

    async def _dispatch(self, message: MCPMessage) -> None:
        """分发消息到相应处理器。"""
        try:
            if is_response(message):
                await self._handle_response(message)
            elif is_request(message):
                await self._handle_request(message)
            elif is_notification(message):
                await self._handle_notification(message)
            else:
                logger.warning(f"Unknown message type: {message}")
        except Exception as e:
            logger.error(f"Dispatch error for {message.method if message.method else message.id}: {e}")
            if message.id is not None:
                error_resp = MCPMessage.error_response(
                    id=message.id,
                    code=MCPCode.INTERNAL_ERROR.value,
                    message=str(e),
                )
                await self.send(error_resp)

    async def _handle_request(self, message: MCPMessage) -> None:
        """处理请求消息。"""
        method = message.method
        if not method:
            return

        handler = self._method_handlers.get(method)
        if handler:
            try:
                response = await handler(message)
                if response.id is None:
                    response.id = message.id
                await self.send(response)
            except Exception as e:
                error_resp = MCPMessage.error_response(
                    id=message.id,
                    code=MCPCode.INTERNAL_ERROR.value,
                    message=str(e),
                )
                await self.send(error_resp)
        else:
            error_resp = MCPMessage.error_response(
                id=message.id,
                code=MCPCode.METHOD_NOT_FOUND.value,
                message=f"Method not found: {method}",
            )
            await self.send(error_resp)

    async def _handle_notification(self, message: MCPMessage) -> None:
        """处理通知消息。"""
        method = message.method
        if not method:
            return

        handler = self._notification_handlers.get(method)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Notification handler error for {method}: {e}")
        else:
            logger.debug(f"No handler for notification: {method}")

    async def _handle_response(self, message: MCPMessage) -> None:
        """处理响应消息，配对到待处理的请求。"""
        msg_id = message.id
        if msg_id is not None:
            future = self._pending_requests.pop(str(msg_id), None)
            if future and not future.done():
                future.set_result(message)

    # ──────────────────────────────────────────────────────────────────────────
    # Default Handlers
    # ──────────────────────────────────────────────────────────────────────────

    async def _handle_initialize(self, message: MCPMessage) -> MCPMessage:
        """处理 initialize 请求。"""
        params = message.params or {}
        client_version = params.get("protocolVersion", MCP_PROTOCOL_VERSION)
        client_caps = params.get("capabilities", ClientCapabilities())
        client_info = params.get("clientInfo", {})

        logger.info(f"Client initializing: {client_info}, caps: {client_caps}")

        self._initialized = True

        return MCPMessage.response(
            id=message.id,
            result={
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": self._server_capabilities.to_dict(),
                "serverInfo": self._config.server_info,
            },
        )

    async def _handle_shutdown(self, message: MCPMessage) -> MCPMessage:
        """处理 shutdown 请求。"""
        self._initialized = False
        return MCPMessage.response(
            id=message.id,
            result={"success": True},
        )

    async def _handle_exit(self, message: MCPMessage) -> None:
        """处理 exit 通知。"""
        logger.info("Exit notification received")
        self._running = False

    # ──────────────────────────────────────────────────────────────────────────
    # Request/Response
    # ──────────────────────────────────────────────────────────────────────────

    async def send(self, message: MCPMessage) -> None:
        """发送消息。"""
        await self._transport.send(message)

    async def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """调用工具（客户端方法）。"""
        if not self._initialized:
            raise RuntimeError("Session not initialized")

        self._request_counter += 1
        request_id = str(self._request_counter)

        request = MCPMessage.request(
            method="tools/call",
            params={
                "name": tool_name,
                "arguments": arguments or {},
            },
            id=request_id,
        )

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            await self.send(request)
            response = await asyncio.wait_for(future, timeout=self._config.request_timeout)
            if response.error:
                raise RuntimeError(f"Tool call error: {response.error}")
            return response.result or {}
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Tool call {tool_name} timed out")
        finally:
            self._pending_requests.pop(request_id, None)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """列出可用工具。"""
        if not self._initialized:
            raise RuntimeError("Session not initialized")

        self._request_counter += 1
        request_id = str(self._request_counter)

        request = MCPMessage.request(
            method="tools/list",
            params={},
            id=request_id,
        )

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        try:
            await self.send(request)
            response = await asyncio.wait_for(future, timeout=self._config.request_timeout)
            if response.error:
                raise RuntimeError(f"List tools error: {response.error}")
            return response.result.get("tools", []) if response.result else []
        finally:
            self._pending_requests.pop(request_id, None)

    # ──────────────────────────────────────────────────────────────────────────
    # Method Registration
    # ──────────────────────────────────────────────────────────────────────────

    def add_method_handler(self, method: str, handler: MethodHandler) -> None:
        """注册请求方法处理器。"""
        self._method_handlers[method] = handler

    def add_notification_handler(self, method: str, handler: NotificationHandler) -> None:
        """注册通知处理器。"""
        self._notification_handlers[method] = handler

    def register_tool(self, name: str, handler: Callable, schema: Dict[str, Any]) -> None:
        """注册工具（服务端方法）。"""
        self._tools[name] = schema
        self._tool_handlers[name] = handler

        # 注册 tools/call 处理器
        async def tool_call_handler(msg: MCPMessage) -> MCPMessage:
            params = msg.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self._tool_handlers:
                return MCPMessage.error_response(
                    id=msg.id,
                    code=MCPCode.TOOL_NOT_FOUND.value,
                    message=f"Tool not found: {tool_name}",
                )

            try:
                result = await self._tool_handlers[tool_name](**arguments)
                return MCPMessage.response(
                    id=msg.id,
                    result={
                        "content": [
                            {"type": "text", "text": str(result)}
                        ]
                    },
                )
            except Exception as e:
                return MCPMessage.error_response(
                    id=msg.id,
                    code=MCPCode.INTERNAL_ERROR.value,
                    message=str(e),
                )

        self.add_method_handler("tools/call", tool_call_handler)
        self.add_method_handler("tools/list", self._handle_list_tools)

    async def _handle_list_tools(self, msg: MCPMessage) -> MCPMessage:
        """处理 tools/list 请求。"""
        tools = [
            {"name": name, "description": schema.get("description", ""), "inputSchema": schema.get("parameters", {})}
            for name, schema in self._tools.items()
        ]
        return MCPMessage.response(
            id=msg.id,
            result={"tools": tools},
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def transport(self) -> Transport:
        return self._transport


__all__ = [
    "SessionConfig",
    "MethodHandler",
    "NotificationHandler",
    "MCPSession",
]