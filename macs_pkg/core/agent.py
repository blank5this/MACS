"""Agent base classes and role definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from ..memory.mempalace_client import MemPalaceClient, MemoryConfig
    from ..memory.agent_memory import AgentMemory, AgentMemoryConfig, MemoryEntry


class AgentRole(Enum):
    """Agent roles in the collaboration system."""

    PLANNER = "planner"  # 规划 - 分解任务, 分析需求
    EXECUTOR = "executor"  # 执行 - 执行具体子任务
    REVIEWER = "reviewer"  # 审查 - 审核结果, 质量把控
    TOOL = "tool"  # 工具 - 调用外部工具


class AgentState(Enum):
    """Agent lifecycle states."""

    IDLE = "idle"  # 空闲
    THINKING = "thinking"  # 思考中
    ACTING = "acting"  # 执行中
    WAITING = "waiting"  # 等待中
    DONE = "done"  # 完成


@dataclass
class Message:
    """Standardized message format for inter-agent communication."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""  # 发送者名称
    receiver: str = ""  # 接收者名称, "*" 表示广播
    content: Any = None  # 消息内容
    msg_type: str = "text"  # 消息类型: text, action, result, error
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "msg_type": self.msg_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Each agent has a name, role, model configuration, and maintains
    its own message history (memory).
    """

    # Shared memory client for all agents (initialized once)
    _shared_memory_client: Optional["MemPalaceClient"] = None
    _shared_memory_initialized: bool = False

    def __init__(
        self,
        name: str,
        role: AgentRole,
        model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        memory_config: Optional["AgentMemoryConfig"] = None,
        mempalace_client: Optional["MemPalaceClient"] = None,
    ):
        self.name = name
        self.role = role
        self.model = model
        self.system_prompt = system_prompt or self._default_system_prompt()
        self.memory: List[Message] = []  # Short-term memory (runtime)
        self.state = AgentState.IDLE
        self._context: Dict[str, Any] = {}

        # Initialize long-term memory
        self._init_long_term_memory(memory_config, mempalace_client)

    def _init_long_term_memory(
        self,
        memory_config: Optional["AgentMemoryConfig"],
        mempalace_client: Optional["MemPalaceClient"],
    ) -> None:
        """Initialize long-term memory with MemPalace."""
        # Use provided client or get shared client
        if mempalace_client:
            client = mempalace_client
        elif BaseAgent._shared_memory_client is None:
            from ..memory.mempalace_client import MemPalaceClient, MemoryConfig
            BaseAgent._shared_memory_client = MemPalaceClient()
            BaseAgent._shared_memory_initialized = False

        client = BaseAgent._shared_memory_client

        if client:
            from ..memory.agent_memory import AgentMemory, AgentMemoryConfig
            self._long_term_memory: Optional["AgentMemory"] = AgentMemory(
                agent_name=self.name,
                agent_role=self.role.value,
                client=client,
                config=memory_config,
            )
        else:
            self._long_term_memory = None

    async def init_memory(self) -> None:
        """Initialize memory system. Call this before using long-term memory."""
        if self._long_term_memory and not BaseAgent._shared_memory_initialized:
            await self._long_term_memory.initialize()
            BaseAgent._shared_memory_initialized = True

    @classmethod
    def get_shared_memory_client(cls) -> Optional["MemPalaceClient"]:
        """Get the shared memory client."""
        return cls._shared_memory_client

    @classmethod
    async def init_shared_memory(
        cls,
        config: Optional["MemoryConfig"] = None,
    ) -> None:
        """Initialize the shared memory client for all agents."""
        if cls._shared_memory_client is None:
            from ..memory.mempalace_client import MemPalaceClient, MemoryConfig
            cls._shared_memory_client = MemPalaceClient(config or MemoryConfig())

        await cls._shared_memory_client.initialize()
        cls._shared_memory_initialized = True

    def _default_system_prompt(self) -> str:
        """Generate default system prompt based on role."""
        prompts = {
            AgentRole.PLANNER: "You are a Planner Agent. Your role is to analyze complex tasks, "
                              "break them down into smaller subtasks, and create an execution plan.",
            AgentRole.EXECUTOR: "You are an Executor Agent. Your role is to execute specific "
                                "subtasks assigned to you and report results accurately.",
            AgentRole.REVIEWER: "You are a Reviewer Agent. Your role is to review and validate "
                                "results, provide feedback, and ensure quality standards.",
            AgentRole.TOOL: "You are a Tool Agent. Your role is to execute specific tools "
                            "and return results to the requesting agent.",
        }
        return prompts.get(self.role, "You are a general-purpose agent.")

    @abstractmethod
    async def think(self, message: Message) -> Message:
        """Process incoming message and generate response.

        This is the thinking phase where the agent processes the input
        and prepares its response.

        Args:
            message: The incoming message to process.

        Returns:
            The response message.
        """
        pass

    @abstractmethod
    async def act(self, response: Message) -> List[Message]:
        """Execute actions based on the response.

        This is the acting phase where the agent may produce multiple
        downstream messages or trigger tool calls.

        Args:
            response: The response generated from the think phase.

        Returns:
            List of messages to send to other agents.
        """
        pass

    def add_to_memory(self, message: Message) -> None:
        """Add a message to the agent's memory."""
        self.memory.append(message)

    def get_memory(self) -> List[Message]:
        """Retrieve all messages from memory."""
        return self.memory.copy()

    def clear_memory(self) -> None:
        """Clear all messages from memory."""
        self.memory.clear()

    @staticmethod
    def vote_on_proposal(proposal: Any) -> str:
        """Vote on a proposal based on confidence.

        Args:
            proposal: The proposal to vote on (dict with optional 'confidence' key).

        Returns:
            "approve" if confidence >= 0.5, otherwise "reject".
        """
        if isinstance(proposal, dict):
            confidence = proposal.get("confidence", 0.5)
            return "approve" if confidence >= 0.5 else "reject"
        return "approve"

    # ==================== Long-term Memory Methods ====================

    async def remember(
        self,
        content: str,
        memory_type: str = "interaction",
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Store a long-term memory via MemPalace.

        Args:
            content: Content to remember.
            memory_type: Type of memory (interaction, decision, result, error).
            task_id: Associated task ID.
            metadata: Additional metadata.

        Returns:
            Memory ID if successful.
        """
        if self._long_term_memory:
            return await self._long_term_memory.remember(
                content=content,
                memory_type=memory_type,
                task_id=task_id,
                metadata=metadata,
            )
        return None

    async def recall(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> List["MemoryEntry"]:
        """Recall relevant memories based on a query.

        Args:
            query: Search query.
            memory_type: Optional filter by memory type.
            limit: Maximum number of results.

        Returns:
            List of relevant memory entries.
        """
        if self._long_term_memory:
            return await self._long_term_memory.recall(
                query=query,
                memory_type=memory_type,
                limit=limit,
            )
        return []

    async def recall_context(
        self,
        task_id: str,
        limit: int = 10,
    ) -> List["MemoryEntry"]:
        """Recall memories related to a specific task.

        Args:
            task_id: Task identifier.
            limit: Maximum number of results.

        Returns:
            List of memory entries for the task.
        """
        if self._long_term_memory:
            return await self._long_term_memory.recall_context(
                task_id=task_id,
                limit=limit,
            )
        return []

    async def remember_interaction(
        self,
        message_content: str,
        sender: str,
        receiver: str,
        task_id: Optional[str] = None,
    ) -> Optional[str]:
        """Remember an interaction with another agent."""
        if self._long_term_memory:
            return await self._long_term_memory.remember_interaction(
                message_content=message_content,
                sender=sender,
                receiver=receiver,
                task_id=task_id,
            )
        return None

    async def remember_decision(
        self,
        decision: str,
        rationale: str,
        task_id: Optional[str] = None,
    ) -> Optional[str]:
        """Remember a decision made by the agent."""
        if self._long_term_memory:
            return await self._long_term_memory.remember_decision(
                decision=decision,
                rationale=rationale,
                task_id=task_id,
            )
        return None

    async def remember_result(
        self,
        action: str,
        result: Any,
        success: bool,
        task_id: Optional[str] = None,
    ) -> Optional[str]:
        """Remember a result from an action."""
        if self._long_term_memory:
            return await self._long_term_memory.remember_result(
                action=action,
                result=result,
                success=success,
                task_id=task_id,
            )
        return None

    async def remember_error(
        self,
        error: str,
        context: str,
        task_id: Optional[str] = None,
    ) -> Optional[str]:
        """Remember an error encountered."""
        if self._long_term_memory:
            return await self._long_term_memory.remember_error(
                error=error,
                context=context,
                task_id=task_id,
            )
        return None

    def get_short_term_memories(self, limit: int = 10) -> List["MemoryEntry"]:
        """Get recent short-term memories (in-memory only).

        Args:
            limit: Maximum number to return.

        Returns:
            List of recent messages.
        """
        return [MemoryEntry(
            id=m.id,
            content=str(m.content),
            timestamp=m.timestamp,
            memory_type="interaction",
            related_agent=m.sender,
            metadata=m.metadata,
        ) for m in self.memory[-limit:]]

    async def get_all_long_term_memories(self, limit: int = 100) -> List["MemoryEntry"]:
        """Get all long-term memories for this agent."""
        if self._long_term_memory:
            return await self._long_term_memory.get_all_memories(limit=limit)
        return []

    async def clear_long_term_memory(self) -> None:
        """Clear all long-term memories for this agent."""
        if self._long_term_memory:
            await self._long_term_memory.clear()

    def has_long_term_memory(self) -> bool:
        """Check if long-term memory is available."""
        return self._long_term_memory is not None

    def set_context(self, key: str, value: Any) -> None:
        """Set agent-specific context."""
        self._context[key] = value

    def get_context(self, key: str) -> Optional[Any]:
        """Get agent-specific context."""
        return self._context.get(key)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name}, role={self.role.value})>"


class SimpleAgent(BaseAgent):
    """A simple text-based agent implementation using LLM.

    This is a basic implementation that can be extended for more complex scenarios.
    """

    def __init__(
        self,
        name: str,
        role: AgentRole,
        model: str = "gpt-4",
        memory_config: Optional["AgentMemoryConfig"] = None,
    ):
        super().__init__(name, role, model, memory_config=memory_config)

    async def think(self, message: Message) -> Message:
        """Process the message with simple pass-through logic."""
        self.state = AgentState.THINKING

        # Retrieve relevant long-term memories for context
        memories = []
        if self.has_long_term_memory():
            memories = await self.recall(str(message.content), limit=3)

        # Build context from memories
        context_str = ""
        if memories:
            context_str = "\n\nRelevant past context:\n"
            for m in memories:
                context_str += f"- {m.content}\n"

        response = Message(
            sender=self.name,
            receiver=message.sender,
            content=f"[{self.role.value}] Processed: {message.content}{context_str}",
            msg_type="result",
            metadata={"original_id": message.id},
        )

        # Remember this interaction
        if self.has_long_term_memory():
            await self.remember_interaction(
                message_content=str(message.content),
                sender=message.sender,
                receiver=self.name,
                task_id=message.metadata.get("task_id"),
            )

        self.state = AgentState.IDLE
        return response

    async def act(self, response: Message) -> List[Message]:
        """Return the response as a single message to sender."""
        self.state = AgentState.ACTING
        self.add_to_memory(response)
        self.state = AgentState.IDLE
        return [response]
