"""MCP (Model Context Protocol) Support for MACS.

MCP 是一个让 AI Agent 与外部工具/数据源连接的协议标准。
参考: https://modelcontextprotocol.io

使用方式::

    from macs_pkg.mcp import MCPClient

    # 连接到 MCP Server
    client = MCPClient()
    await client.connect("http://localhost:8000")

    # 使用工具
    tools = await client.list_tools()
    result = await client.call_tool("search", {"query": "..."})
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


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
    """Client for connecting to MCP servers.

    Supports:
    - Connecting to HTTP/S MCP servers
    - Listing available tools
    - Calling tools
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
        """Connect to an MCP server.

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
                    "protocolVersion": "2024-11-05",
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
        """List available tools from the server.

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
        """Call a tool on the MCP server.

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
        """Disconnect from the MCP server."""
        self._connected = False
        self._tools.clear()

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected


__all__ = [
    "MCPError",
    "MCPConnectionError", 
    "MCPTool",
    "MCPCapabilities",
    "MCPClient",
]
