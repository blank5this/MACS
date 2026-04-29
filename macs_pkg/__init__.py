"""MACS - Multi-Agent Collaboration System"""

__version__ = "0.1.0"

from .core.agent import BaseAgent, AgentRole, Message, AgentState, SimpleAgent
from .core.message import MessageType
from .core.context import ContextManager, TaskContext
from .core.router import MessageRouter
from .core.aggregator import ResultAggregator, AggregationStrategy

from .collaboration.base import CollaborationMode, CollaborationConfig, CollaborationRegistry
from .collaboration.hierarchical import HierarchicalMode
from .collaboration.decentralized import DecentralizedMode
from .collaboration.pipeline import PipelineMode, ParallelPipelineMode
from .collaboration.dynamic_selector import DynamicSelector, AdaptiveSelector

from .agents.planner import PlannerAgent
from .agents.executor import ExecutorAgent
from .agents.reviewer import ReviewerAgent
from .agents.tool_agent import ToolAgent, create_tool_agent_with_defaults

from .runtime.engine import RuntimeEngine, RuntimeConfig, create_runtime

from .tools import (
    BaseTool, FunctionTool, ToolParameter, ToolResult, ToolSpec, tool,
    ToolRegistry, get_default_registry,
    CalculatorTool, TextFormatterTool, FileReaderTool, FileWriterTool,
    HttpGetTool, JsonParserTool,
    register_builtin_tools, create_default_registry,
)

try:
    from .tools import RAGSearchTool
    _has_rag_tool = True
except ImportError:
    _has_rag_tool = False
    RAGSearchTool = None

from .llm import (
    LLMMessage, LLMProvider, LLMResponse,
    ClaudeProvider, ClaudeAgentMixin,
    LLMPlannerAgent, LLMExecutorAgent, LLMReviewerAgent,
    MiniMaxPlannerAgent, MiniMaxExecutorAgent, MiniMaxReviewerAgent,
    OpenAICompatibleProvider, MiniMaxProvider, MiniMaxAgentMixin,
)

from .monitoring import (
    Event, EventBus, EventType, get_event_bus,
    MetricsStore, SystemMonitor, get_monitor,
)
try:
    from .monitoring import PrometheusExporter
    _has_prometheus = True
except ImportError:
    _has_prometheus = False
    PrometheusExporter = None

from .utils import (
    MACSErrorCode, MACSException,
    AgentException, CollaborationException, LLMException,
    MemoryException, ToolException, RuntimeException, ConfigException,
)
from .utils.logger import get_logger, MACSLogger

from .visualization import ExecutionTracer, TracedRuntimeMixin

from .rag import (
    RAGConfig,
    RAGEngine,
    RAGEnabledExecutor,
    Document, DocumentChunker, DocumentProcessor,
    Embedder, DummyEmbedder, create_embedder,
    VectorStore, SearchResult, InMemoryVectorStore, create_vector_store,
)

from .messaging import (
    RedisMessageQueue,
    DistributedAgentMessenger,
    QueuedMessage,
    MessagePriority,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "BaseAgent", "AgentRole", "AgentState", "Message", "MessageType", "SimpleAgent",
    "ContextManager", "TaskContext",
    "MessageRouter",
    "ResultAggregator", "AggregationStrategy",
    # Collaboration
    "CollaborationMode", "CollaborationConfig", "CollaborationRegistry",
    "HierarchicalMode", "DecentralizedMode", "PipelineMode", "ParallelPipelineMode",
    "DynamicSelector", "AdaptiveSelector",
    # Agents
    "PlannerAgent", "ExecutorAgent", "ReviewerAgent",
    "ToolAgent", "create_tool_agent_with_defaults",
    # Runtime
    "RuntimeEngine", "RuntimeConfig", "create_runtime",
    # Tools
    "BaseTool", "FunctionTool", "ToolParameter", "ToolResult", "ToolSpec", "tool",
    "ToolRegistry", "get_default_registry",
    "CalculatorTool", "TextFormatterTool", "FileReaderTool", "FileWriterTool",
    "HttpGetTool", "JsonParserTool",
    "register_builtin_tools", "create_default_registry",
    "RAGSearchTool",
    # LLM
    "LLMMessage", "LLMProvider", "LLMResponse",
    "ClaudeProvider", "ClaudeAgentMixin",
    "OpenAICompatibleProvider", "MiniMaxProvider", "MiniMaxAgentMixin",
    "LLMPlannerAgent", "LLMExecutorAgent", "LLMReviewerAgent",
    "MiniMaxPlannerAgent", "MiniMaxExecutorAgent", "MiniMaxReviewerAgent",
    # Monitoring
    "Event", "EventBus", "EventType", "get_event_bus",
    "MetricsStore", "SystemMonitor", "get_monitor",
    # Utils
    "MACSErrorCode", "MACSException",
    "AgentException", "CollaborationException", "LLMException",
    "MemoryException", "ToolException", "RuntimeException", "ConfigException",
    "get_logger", "MACSLogger",
    # Visualization
    "ExecutionTracer", "TracedRuntimeMixin",
    # RAG
    "RAGConfig", "RAGEngine", "RAGEnabledExecutor",
    "Document", "DocumentChunker", "DocumentProcessor",
    "Embedder", "DummyEmbedder", "create_embedder",
    "VectorStore", "SearchResult", "InMemoryVectorStore", "create_vector_store",
    # Messaging
    "RedisMessageQueue", "DistributedAgentMessenger",
    "QueuedMessage", "MessagePriority",
]
if _has_prometheus:
    __all__.append("PrometheusExporter")
