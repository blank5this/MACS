"""MCP Transport 层 - stdio 和 HTTP/SSE 两种传输方式。

Transport 负责消息的发送和接收，是 MCP 协议的底层通信机制。
"""

from __future__ import annotations

import asyncio
import json
import sys
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Optional, List
from loguru import logger

from .protocol import MCPMessage, JSONRPC_VERSION


class TransportError(Exception):
    """Transport 相关错误。"""
    pass


class TransportClosed(TransportError):
    """Transport 已关闭。"""
    pass


# ──────────────────────────────────────────────────────────────────────────────
# Abstract Base
# ──────────────────────────────────────────────────────────────────────────────

class Transport(ABC):
    """MCP Transport 抽象基类。

    子类需要实现:
    - start(): 启动传输
    - send(message): 发送消息
    - receive(): 接收消息（异步生成器）
    - close(): 关闭传输
    """

    @abstractmethod
    async def start(self) -> None:
        """启动传输。"""
        pass

    @abstractmethod
    async def send(self, message: MCPMessage) -> None:
        """发送消息。"""
        pass

    @abstractmethod
    async def receive(self) -> AsyncGenerator[MCPMessage, None]:
        """接收消息的异步生成器。"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭传输。"""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """是否已连接。"""
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Stdio Transport (for subprocess communication)
# ──────────────────────────────────────────────────────────────────────────────

class StdioTransport(Transport):
    """Stdio 传输方式 - 通过 stdin/stdout 与子进程通信。

    适用于:
    - MCP Server 作为子进程运行
    - 调试环境
    """

    def __init__(
        self,
        stdin: Optional[asyncio.StreamReader] = None,
        stdout: Optional[asyncio.StreamWriter] = None,
        stderr: Optional[asyncio.StreamWriter] = None,
    ):
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        self._running = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._protocol: Optional[asyncio.StreamReaderProtocol] = None

    async def start(self) -> None:
        """启动 stdio 传输。"""
        if self._running:
            return

        loop = asyncio.get_event_loop()

        # 使用标准流
        if sys.platform == "win32":
            # Windows: 使用ProactorEventLoop 或直接使用 sys.stdin/stdout
            self._reader = asyncio.StreamReader()
            self._protocol = asyncio.StreamReaderProtocol(self._reader)
        else:
            self._reader = asyncio.StreamReader()
            self._protocol = asyncio.StreamReaderProtocol(self._reader)

        # Unix: 直接连接管道
        if sys.platform != "win32":
            await loop.connect_read_pipe(lambda: self._protocol, sys.stdin)

        # 创建写入管道
        transport, self._writer = await loop.create_write_pipe(
            asyncio.transports.WritePipeTransport
        )

        self._running = True
        logger.debug("StdioTransport started")

    async def send(self, message: MCPMessage) -> None:
        """通过 stdout 发送消息。"""
        if not self._running or self._writer is None:
            raise TransportClosed("Transport not running")

        data = message.to_json() + "\n"
        self._writer.write(data.encode("utf-8"))
        await self._writer.drain()

    async def receive(self) -> AsyncGenerator[MCPMessage, None]:
        """从 stdin 读取消息。"""
        if not self._running or self._reader is None:
            raise TransportClosed("Transport not running")

        while self._running:
            try:
                line = await self._reader.readline()
                if not line:
                    break

                raw = line.decode("utf-8").strip()
                if not raw:
                    continue

                yield MCPMessage.from_json(raw)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"StdioTransport receive error: {e}")
                break

    async def close(self) -> None:
        """关闭 stdio 传输。"""
        self._running = False
        if self._writer:
            self._writer.close()
            self._writer = None
        self._reader = None
        self._protocol = None
        logger.debug("StdioTransport closed")

    @property
    def is_connected(self) -> bool:
        return self._running


# ──────────────────────────────────────────────────────────────────────────────
# HTTP/SSE Transport (for network communication)
# ──────────────────────────────────────────────────────────────────────────────

class HttpSSETransport(Transport):
    """HTTP/SSE 传输方式 - 通过 HTTP POST + SSE 进行通信。

    适用于:
    - 远程 MCP Server
    - Web 环境
    """

    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ):
        """
        Args:
            base_url: MCP Server 基础 URL
            headers: 额外 HTTP 头
            timeout: 请求超时（秒）
        """
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._timeout = timeout
        self._session = None
        self._running = False
        self._receive_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue[MCPMessage] = asyncio.Queue()
        self._event_reader: Optional[asyncio.StreamReader] = None

    async def start(self) -> None:
        """启动 HTTP/SSE 传输。"""
        if self._running:
            return

        import aiohttp
        self._session = aiohttp.ClientSession(
            headers={**self._headers, "Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=self._timeout),
        )
        self._running = True
        logger.debug(f"HttpSSETransport started: {self._base_url}")

    async def _send_http(self, method: str, path: str, data: Optional[Dict] = None) -> Dict:
        """发送 HTTP 请求。"""
        if self._session is None:
            raise TransportClosed("Session not initialized")

        url = f"{self._base_url}{path}"
        async with self._session.request(method, url, json=data) as resp:
            return await resp.json()

    async def send(self, message: MCPMessage) -> None:
        """通过 HTTP POST 发送消息。"""
        if not self._running:
            raise TransportClosed("Transport not running")

        try:
            await self._send_http("POST", "/", message.to_dict())
        except Exception as e:
            raise TransportError(f"Failed to send message: {e}")

    async def receive(self) -> AsyncGenerator[MCPMessage, None]:
        """通过 SSE 接收消息。"""
        if not self._running or self._session is None:
            raise TransportClosed("Transport not running")

        try:
            async with self._session.get(f"{self._base_url}/sse") as resp:
                async for line in resp.content:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data:
                            yield MCPMessage.from_json(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"HttpSSETransport receive error: {e}")

    async def close(self) -> None:
        """关闭 HTTP 会话。"""
        self._running = False
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        if self._session:
            await self._session.close()
        self._session = None
        logger.debug("HttpSSETransport closed")

    @property
    def is_connected(self) -> bool:
        return self._running


# ──────────────────────────────────────────────────────────────────────────────
# In-Memory Transport (for testing)
# ──────────────────────────────────────────────────────────────────────────────

class InMemoryTransport(Transport):
    """内存传输方式 - 用于进程内通信和测试。

    两个端点直接通过队列传递消息。
    """

    def __init__(self):
        self._local_queue: asyncio.Queue[MCPMessage] = asyncio.Queue()
        self._remote_queue: asyncio.Queue[MCPMessage] = asyncio.Queue()
        self._running = False
        self._name = "InMemory"

    def pair(self) -> tuple["InMemoryTransport", "InMemoryTransport"]:
        """创建一对互联的 InMemoryTransport。"""
        t1 = InMemoryTransport()
        t2 = InMemoryTransport()
        t1._remote_queue = t2._local_queue
        t2._remote_queue = t1._local_queue
        t1._running = True
        t2._running = True
        return t1, t2

    async def start(self) -> None:
        self._running = True

    async def send(self, message: MCPMessage) -> None:
        if not self._running:
            raise TransportClosed("Transport not running")
        await self._remote_queue.put(message)

    async def receive(self) -> AsyncGenerator[MCPMessage, None]:
        while self._running:
            try:
                msg = await asyncio.wait_for(self._local_queue.get(), timeout=0.1)
                yield msg
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def close(self) -> None:
        self._running = False

    @property
    def is_connected(self) -> bool:
        return self._running


__all__ = [
    "Transport",
    "TransportError",
    "TransportClosed",
    "StdioTransport",
    "HttpSSETransport",
    "InMemoryTransport",
]