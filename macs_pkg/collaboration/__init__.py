"""Collaboration engine for multi-agent coordination."""

from .base import CollaborationMode, CollaborationConfig, CollaborationRegistry
from .hierarchical import HierarchicalMode
from .decentralized import DecentralizedMode
from .pipeline import PipelineMode, ParallelPipelineMode
from .dynamic_selector import DynamicSelector, AdaptiveSelector
from .deep_research import DeepResearchMode

__all__ = [
    "CollaborationMode",
    "CollaborationConfig",
    "CollaborationRegistry",
    "HierarchicalMode",
    "DecentralizedMode",
    "PipelineMode",
    "ParallelPipelineMode",
    "DynamicSelector",
    "AdaptiveSelector",
    "DeepResearchMode",
]
