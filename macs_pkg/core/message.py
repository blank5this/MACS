"""Message types and protocols for agent communication."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid


class MessageType(Enum):
    """Standard message types in the system."""

    # Text-based messages
    TEXT = "text"  # Plain text message
    ACTION = "action"  # Action request
    RESULT = "result"  # Result response
    ERROR = "error"  # Error message

    # Collaboration messages
    TASK = "task"  # Task assignment
    SUBTASK = "subtask"  # Subtask decomposition
    REVIEW = "review"  # Review request/response
    APPROVAL = "approval"  # Approval decision

    # System messages
    REGISTER = "register"  # Agent registration
    HEARTBEAT = "heartbeat"  # Keep-alive signal
    TERMINATE = "terminate"  # Shutdown signal

    # Consensus messages
    VOTE = "vote"  # Voting message
    PROPOSE = "propose"  # Proposal message
    CONSENSUS = "consensus"  # Consensus reached


@dataclass
class MessageContent:
    """Structured content for messages."""

    text: Optional[str] = None  # Text content
    data: Optional[Dict[str, Any]] = None  # Structured data
    attachments: List[str] = field(default_factory=list)  # Attachment references
    references: List[str] = field(default_factory=list)  # Reference message IDs


@dataclass
class MessageMetadata:
    """Metadata attached to messages."""

    task_id: Optional[str] = None  # Associated task ID
    subtask_id: Optional[str] = None  # Associated subtask ID
    priority: int = 0  # Priority level (higher = more important)
    ttl: int = 300  # Time to live in seconds
    retry_count: int = 0  # Retry counter
    tags: List[str] = field(default_factory=list)  # Categorization tags


def create_message(
    sender: str,
    receiver: str,
    content: Any,
    msg_type: str = "text",
    **metadata,
) -> Dict[str, Any]:
    """Factory function to create a message dictionary.

    Args:
        sender: Name of the sending agent.
        receiver: Name of the receiving agent ("*" for broadcast).
        content: The message content.
        msg_type: Type of message.
        **metadata: Additional metadata fields.

    Returns:
        A message dictionary.
    """
    return {
        "id": str(uuid.uuid4()),
        "sender": sender,
        "receiver": receiver,
        "content": content,
        "msg_type": msg_type,
        "metadata": metadata,
        "timestamp": datetime.now().isoformat(),
    }


def create_broadcast(sender: str, content: Any, msg_type: str = "text") -> Dict[str, Any]:
    """Create a broadcast message to all agents.

    Args:
        sender: Name of the sending agent.
        content: The message content.
        msg_type: Type of message.

    Returns:
        A broadcast message dictionary.
    """
    return create_message(sender, "*", content, msg_type)


def create_task_message(
    sender: str,
    receiver: str,
    task: str,
    task_id: str,
    **metadata,
) -> Dict[str, Any]:
    """Create a task assignment message.

    Args:
        sender: Name of the sending agent.
        receiver: Name of the receiving agent.
        task: Description of the task.
        task_id: Unique task identifier.
        **metadata: Additional metadata.

    Returns:
        A task message dictionary.
    """
    return create_message(
        sender,
        receiver,
        task,
        "task",
        task_id=task_id,
        **metadata,
    )
