"""Redis Message Queue - Distributed messaging for MACS agents.

This module provides Redis-based message passing for distributed agent systems.
Supports publish/subscribe and queue patterns.

Usage:
    from macs_pkg.messaging import RedisMessageQueue

    # Create queue
    queue = RedisMessageQueue(host="localhost", port=6379)

    # Publish message
    await queue.publish("agent_channel", message)

    # Subscribe to channel
    async for message in queue.subscribe("agent_channel"):
        print(f"Received: {message}")
"""

from __future__ import annotations

import json
import asyncio
from typing import Any, Dict, List, Optional, AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import os

try:
    import redis.asyncio as redis
except ImportError:
    redis = None

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("redis_queue")


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QueuedMessage:
    """A message in the queue with metadata."""
    id: str
    channel: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    ttl_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "channel": self.channel,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        })

    @classmethod
    def from_json(cls, data: str) -> "QueuedMessage":
        obj = json.loads(data)
        return cls(
            id=obj["id"],
            channel=obj["channel"],
            payload=obj["payload"],
            priority=MessagePriority(obj.get("priority", "normal")),
            timestamp=datetime.fromisoformat(obj["timestamp"]),
            ttl_seconds=obj.get("ttl_seconds"),
            retry_count=obj.get("retry_count", 0),
            max_retries=obj.get("max_retries", 3),
        )


class RedisMessageQueue:
    """Redis-based message queue for distributed agent communication.

    Features:
    - Publish/Subscribe channels
    - Priority queues
    - Message TTL
    - Automatic retry with dead-letter queue
    - Distributed scaling

    Usage:
        # Pub/Sub (fire-and-forget)
        queue = RedisMessageQueue()
        await queue.publish("alerts", {"level": "high", "msg": "..."})

        # Queue (reliable delivery)
        await queue.enqueue("tasks", task_message)

        # Subscribe
        async for msg in queue.subscribe("alerts"):
            process(msg)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        ssl: bool = False,
        prefix: str = "macs:mq:",
    ):
        """Initialize Redis connection.

        Args:
            host: Redis host.
            port: Redis port.
            db: Redis database number.
            password: Redis password (optional).
            ssl: Use SSL connection.
            prefix: Key prefix for all MACS keys.
        """
        if redis is None:
            raise ImportError(
                "redis package not installed. Install with: pip install redis"
            )

        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._ssl = ssl
        self._prefix = prefix

        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._client is not None:
            return

        self._client = redis.Redis(
            host=self._host,
            port=self._port,
            db=self._db,
            password=self._password,
            ssl=self._ssl,
            decode_responses=False,
        )
        await self._client.ping()
        logger.info(f"Connected to Redis at {self._host}:{self._port}")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")

    async def __aenter__(self) -> "RedisMessageQueue":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    def _key(self, name: str) -> str:
        """Get full key with prefix."""
        return f"{self._prefix}{name}"

    # ==================== Pub/Sub ====================

    async def publish(self, channel: str, message: Dict[str, Any]) -> int:
        """Publish a message to a channel.

        Args:
            channel: Channel name.
            message: Message payload.

        Returns:
            Number of subscribers that received the message.
        """
        if self._client is None:
            await self.connect()

        key = self._key(f"channel:{channel}")
        payload = json.dumps(message)

        result = await self._client.publish(key, payload)
        logger.debug(f"Published to {channel}: {result} subscribers")
        return result

    async def subscribe(self, *channels: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to channels and yield messages.

        Usage:
            async for msg in queue.subscribe("alerts", "tasks"):
                print(f"Received: {msg}")

        Args:
            *channels: Channel names to subscribe to.

        Yields:
            Message dictionaries.
        """
        if self._client is None:
            await self.connect()

        pubsub = self._client.pubsub()

        # Subscribe to channels
        keys = [self._key(f"channel:{ch}") for ch in channels]
        await pubsub.subscribe(*keys)
        logger.info(f"Subscribed to channels: {channels}")

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        payload = json.loads(message["data"])
                        yield {
                            "channel": message["channel"],
                            "data": payload,
                        }
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in message: {message['data']}")
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()

    # ==================== Queue Operations ====================

    async def enqueue(
        self,
        queue_name: str,
        message: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """Add a message to a queue.

        Args:
            queue_name: Name of the queue.
            message: Message payload.
            priority: Message priority.
            ttl_seconds: Time-to-live in seconds.

        Returns:
            Message ID.
        """
        if self._client is None:
            await self.connect()

        import uuid
        msg_id = str(uuid.uuid4())

        queued_msg = QueuedMessage(
            id=msg_id,
            channel=queue_name,
            payload=message,
            priority=priority,
            ttl_seconds=ttl_seconds,
        )

        key = self._key(f"queue:{queue_name}")

        # Use priority as sorted set score for ordering
        score = self._priority_to_score(priority)

        # Store message body
        await self._client.hset(
            self._key("messages"),
            msg_id,
            queued_msg.to_json(),
        )

        # Add to sorted set (priority queue)
        await self._client.zadd(key, {msg_id: score})

        # Set TTL if specified
        if ttl_seconds:
            await self._client.expire(self._key(f"msg:{msg_id}"), ttl_seconds)

        logger.debug(f"Enqueued message {msg_id} to {queue_name} with priority {priority.value}")
        return msg_id

    async def dequeue(
        self,
        queue_name: str,
        timeout: int = 0,
    ) -> Optional[QueuedMessage]:
        """Remove and return a message from the queue.

        Args:
            queue_name: Name of the queue.
            timeout: Blocking timeout in seconds (0 = non-blocking).

        Returns:
            QueuedMessage or None if queue is empty.
        """
        if self._client is None:
            await self.connect()

        key = self._key(f"queue:{queue_name}")

        # Get highest priority message (lowest score)
        if timeout > 0:
            # Blocking pop
            result = await self._client.bzpopmin(key, timeout=timeout)
            if result is None:
                return None
            _, msg_id, score = result
        else:
            # Non-blocking
            result = await self._client.zpopmin(key, count=1)
            if not result:
                return None
            msg_id, score = result[0]

        msg_id = msg_id.decode() if isinstance(msg_id, bytes) else msg_id

        # Retrieve message body
        msg_data = await self._client.hget(self._key("messages"), msg_id)

        if msg_data:
            await self._client.hdel(self._key("messages"), msg_id)
            return QueuedMessage.from_json(msg_data)

        return None

    async def peek(
        self,
        queue_name: str,
        count: int = 1,
    ) -> List[QueuedMessage]:
        """View messages without removing them.

        Args:
            queue_name: Name of the queue.
            count: Number of messages to peek.

        Returns:
            List of QueuedMessages (highest priority first).
        """
        if self._client is None:
            await self.connect()

        key = self._key(f"queue:{queue_name}")

        # Get top N by priority (lowest score)
        msg_ids = await self._client.zrange(key, 0, count - 1)

        messages = []
        for msg_id in msg_ids:
            msg_id = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
            msg_data = await self._client.hget(self._key("messages"), msg_id)
            if msg_data:
                messages.append(QueuedMessage.from_json(msg_data))

        return messages

    async def get_queue_length(self, queue_name: str) -> int:
        """Get the number of messages in a queue."""
        if self._client is None:
            await self.connect()

        key = self._key(f"queue:{queue_name}")
        return await self._client.zcard(key)

    async def clear_queue(self, queue_name: str) -> int:
        """Clear all messages from a queue.

        Returns:
            Number of messages cleared.
        """
        if self._client is None:
            await self.connect()

        key = self._key(f"queue:{queue_name}")

        # Get all message IDs
        msg_ids = await self._client.zrange(key, 0, -1)

        if msg_ids:
            # Delete messages
            await self._client.hdel(
                self._key("messages"),
                *[mid.decode() if isinstance(mid, bytes) else mid for mid in msg_ids]
            )
            # Clear queue
            await self._client.delete(key)

        logger.info(f"Cleared {len(msg_ids)} messages from queue {queue_name}")
        return len(msg_ids)

    # ==================== Dead Letter Queue ====================

    async def move_to_dlq(self, message: QueuedMessage, error: str) -> None:
        """Move a failed message to the dead-letter queue.

        Args:
            message: The failed message.
            error: Error description.
        """
        if self._client is None:
            await self.connect()

        dlq_message = {
            "original": message.to_dict(),
            "error": error,
            "failed_at": datetime.now().isoformat(),
        }

        dlq_key = self._key(f"dlq:{message.channel}")
        await self._client.lpush(dlq_key, json.dumps(dlq_message))

        logger.warning(f"Moved message {message.id} to DLQ: {error}")

    async def get_dlq_messages(
        self,
        queue_name: str,
        count: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get messages from the dead-letter queue.

        Args:
            queue_name: Original queue name.
            count: Maximum messages to retrieve.

        Returns:
            List of failed message dictionaries.
        """
        if self._client is None:
            await self.connect()

        dlq_key = self._key(f"dlq:{queue_name}")
        messages = await self._client.lrange(dlq_key, 0, count - 1)

        return [json.loads(m.decode() if isinstance(m, bytes) else m) for m in messages]

    # ==================== Helpers ====================

    def _priority_to_score(self, priority: MessagePriority) -> float:
        """Convert priority to sorted set score (lower = higher priority)."""
        scores = {
            MessagePriority.CRITICAL: 0,
            MessagePriority.HIGH: 1,
            MessagePriority.NORMAL: 5,
            MessagePriority.LOW: 10,
        }
        return scores.get(priority, 5)

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health.

        Returns:
            Health status dictionary.
        """
        if self._client is None:
            return {"status": "disconnected"}

        try:
            await self._client.ping()
            info = await self._client.info("server")
            return {
                "status": "healthy",
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_seconds": info.get("uptime_in_seconds", 0),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


class DistributedAgentMessenger:
    """High-level API for agent-to-agent messaging via Redis.

    Usage:
        messenger = DistributedAgentMessenger()

        # Send task to executor
        await messenger.send_task("executor", {
            "task_id": "task_123",
            "description": "Process order",
        })

        # Receive tasks as executor
        async for task in messenger.receive_tasks("executor"):
            result = process(task)
            await messenger.send_result("planner", result)
    """

    def __init__(self, queue: RedisMessageQueue):
        self._queue = queue

    async def send_task(
        self,
        agent_name: str,
        task: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> str:
        """Send a task to an agent."""
        message = {
            "type": "task",
            "to": agent_name,
            "payload": task,
        }
        return await self._queue.enqueue(
            f"tasks:{agent_name}",
            message,
            priority=priority,
        )

    async def receive_tasks(self, agent_name: str) -> AsyncIterator[Dict[str, Any]]:
        """Receive tasks for this agent."""
        async for msg in self._queue.subscribe(f"tasks:{agent_name}"):
            if msg["data"]["type"] == "task":
                yield msg["data"]["payload"]

    async def send_result(
        self,
        to_agent: str,
        result: Dict[str, Any],
    ) -> str:
        """Send a result to an agent."""
        message = {
            "type": "result",
            "to": to_agent,
            "payload": result,
        }
        return await self._queue.publish(f"results:{to_agent}", message)

    async def broadcast(self, message: Dict[str, Any]) -> int:
        """Broadcast a message to all agents."""
        return await self._queue.publish("broadcast", message)
