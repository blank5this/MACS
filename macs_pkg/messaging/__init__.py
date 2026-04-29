"""Messaging module for distributed MACS agents.

Supports:
- Redis pub/sub for real-time messaging
- Redis-based priority queues
- Dead-letter queue for failed messages
- Distributed agent communication

Usage:
    from macs_pkg.messaging import RedisMessageQueue, DistributedAgentMessenger

    # Queue-based messaging
    queue = RedisMessageQueue(host="localhost", port=6379)
    await queue.enqueue("tasks", {"task_id": "123", "data": "..."})

    # High-level agent messenger
    messenger = DistributedAgentMessenger(queue)
    await messenger.send_task("executor", {"task": "process_order"})
"""

from .redis_queue import (
    RedisMessageQueue,
    DistributedAgentMessenger,
    QueuedMessage,
    MessagePriority,
)

__all__ = [
    "RedisMessageQueue",
    "DistributedAgentMessenger",
    "QueuedMessage",
    "MessagePriority",
]
