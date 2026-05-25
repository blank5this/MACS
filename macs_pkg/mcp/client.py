"""MCP Client 实现 - 连接 MCP Server 的客户端部分。

注意：这是一个基础实现。完整的 MCP Client 功能已整合到 protocol/transport/session 中。
如果需要更强的 Client 功能，请使用 MCPSession + 相应 Transport。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .protocol import MCPMessage, MCP_PROTOCOL_VERSION


class MCPError(Exception):
    """MCP-related errors."""
    pass


class MCPConnectionError(MCPError):
    """Failed to connect to MCP server."""
    pass


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    annotations: Optional[Dict[str, Any]] = None


@dataclass
class MCPCapabilities:
    """MCP Server capabilities."""
    tools: bool = False
    resources: bool = False
    prompts: bool = False


class MCPClient:
    """MCP Client - 连接 MCP Server。

    这是一个简化版本的 Client，适用于连接 HTTP MCP Server。
    如需更复杂的场景（如 stdio server），请使用 MCPSession + InMemoryTransport。
    """

    def __init__(self, timeout: float = 30.0):
        """
        Args:
            timeout: Request timeout in seconds.
        """
        self._timeout = timeout
        self._connected = False
        self._tools: Dict[str, MCPTool] = {}
        self._server_url: Optional[str] = None

    async def connect(self, server_url: str) -> MCPCapabilities:
        """连接到 MCP Server。

        Args:
            server_url: Server URL.

        Returns:
            Server capabilities.

        Raises:
            MCPConnectionError: If connection fails.
        """
        import urllib.request
        import urllib.error

        self._server_url = server_url

        try:
            payload = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {
                        "name": "macs-pkg",
                        "version": "0.1.0",
                    },
                },
            }).encode("utf-8")

            req = urllib.request.Request(
                server_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if "result" in data:
                self._connected = True
                caps = data["result"].get("capabilities", {})
                return MCPCapabilities(
                    tools=caps.get("tools", False),
                    resources=caps.get("resources", False),
                    prompts=caps.get("prompts", False),
                )
            else:
                raise MCPConnectionError(f"Initialization failed: {data}")

        except urllib.error.URLError as e:
            raise MCPConnectionError(f"Failed to connect: {e}")
        except Exception as e:
            raise MCPConnectionError(f"MCP connection error: {e}")

    async def list_tools(self) -> List[MCPTool]:
        """列出可用工具。

        Returns:
            List of available tools.
        """
        if not self._connected or not self._server_url:
            raise MCPConnectionError("Not connected. Call connect() first.")

        import urllib.request

        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }).encode("utf-8")

        req = urllib.request.Request(
            self._server_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if "result" in data:
            tools = data["result"].get("tools", [])
            self._tools = {t["name"]: MCPTool(**t) for t in tools}
            return list(self._tools.values())
        return []

    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """调用工具。

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """
        if not self._connected or not self._server_url:
            raise MCPConnectionError("Not connected. Call connect() first.")

        import urllib.request

        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {},
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            self._server_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if "result" in data:
            return data["result"]
        elif "error" in data:
            raise MCPError(f"Tool call failed: {data['error']}")
        return {}

    async def disconnect(self) -> None:
        """断开连接。"""
        self._connected = False
        self._tools.clear()

    @property
    def is_connected(self) -> bool:
        """检查是否已连接。"""
        return self._connected


__all__ = [
    "MCPClient",
    "MCPError",
    "MCPConnectionError",
    "MCPTool",
    "MCPCapabilities",
]