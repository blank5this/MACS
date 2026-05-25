"""MACS - Multi-Agent Collaboration System"""

__version__ = "0.1.0"

from .agent import BaseAgent, AgentRole, Message, AgentState, SimpleAgent
from .message import MessageType
from .agent_template import (
    AgentTemplate,
    AgentTemplateRegistry,
    AgentTemplateConfig,
    get_template_registry,
)

__all__ = [
    "BaseAgent",
    "AgentRole",
    "Message",
    "MessageType",
    "AgentTemplate",
    "AgentTemplateRegistry",
    "AgentTemplateConfig",
    "get_template_registry",
]
