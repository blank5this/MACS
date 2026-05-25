"""LangChain integration module for MACS."""

from __future__ import annotations

# Document loading
try:
    from macs_pkg.langchain.document_loader import (
        DocumentLoader,
        LangChainDocumentConverter,
        MultiFormatDocumentLoader,
    )
except (ImportError, OSError):
    DocumentLoader = None
    LangChainDocumentConverter = None
    MultiFormatDocumentLoader = None

# LCEL RAG Chain
try:
    from macs_pkg.langchain.rag_chain import LCELRAGChain, create_rag_chain
except (ImportError, OSError):
    LCELRAGChain = None
    create_rag_chain = None

# ReAct Agent (original)
try:
    from macs_pkg.langchain.agent import (
        LangChainReActAgent as LangChainReActAgentOriginal,
        create_langchain_tool as create_langchain_tool_original,
        create_calculator_tool as create_calculator_tool_original,
        create_search_tool as create_search_tool_original,
        create_rag_tool as create_rag_tool_original,
    )
except (ImportError, OSError):
    LangChainReActAgentOriginal = None
    create_langchain_tool_original = None
    create_calculator_tool_original = None
    create_search_tool_original = None
    create_rag_tool_original = None

# LLM Adapter
try:
    from macs_pkg.langchain.llm_adapter import (
        MACSChatModelWrapper, MiniMaxChatModel, DeepSeekChatModel, create_chat_model,
    )
except (ImportError, OSError):
    MACSChatModelWrapper = None
    MiniMaxChatModel = None
    DeepSeekChatModel = None
    create_chat_model = None

# Tool Adapter
try:
    from macs_pkg.langchain.tool_adapter import (
        MACSToolAdapter, create_langchain_tool as create_langchain_tool_new,
        create_calculator_tool as create_calculator_tool_new,
    )
except (ImportError, OSError):
    MACSToolAdapter = None
    create_langchain_tool_new = None
    create_calculator_tool_new = None

# Collaboration Chain
try:
    from macs_pkg.langchain.collaboration_chain import (
        CollaborationChain, create_hierarchical_chain, create_pipeline_chain, create_parallel_chain,
    )
except (ImportError, OSError):
    CollaborationChain = None
    create_hierarchical_chain = None
    create_pipeline_chain = None
    create_parallel_chain = None

# MACS Agent
try:
    from macs_pkg.langchain.macs_agent import MACSReActAgent, MACSReActAgentFactory
except (ImportError, OSError):
    MACSReActAgent = None
    MACSReActAgentFactory = None

# Memory Adapter
try:
    from macs_pkg.langchain.memory_adapter import (
        MACSMemoryAdapter, SharedMemoryAdapter, create_memory_adapter, create_memory_for_chain,
    )
except (ImportError, OSError):
    MACSMemoryAdapter = None
    SharedMemoryAdapter = None
    create_memory_adapter = None
    create_memory_for_chain = None

# RAG Adapter
try:
    from macs_pkg.langchain.rag_adapter import (
        RAGEngineRetriever, RAGEngineVectorStore, create_retriever, create_vectorstore,
    )
except (ImportError, OSError):
    RAGEngineRetriever = None
    RAGEngineVectorStore = None
    create_retriever = None
    create_vectorstore = None

__all__ = [
    "DocumentLoader", "LangChainDocumentConverter", "MultiFormatDocumentLoader",
    "LCELRAGChain", "create_rag_chain",
    "LangChainReActAgentOriginal", "create_langchain_tool_original",
    "create_calculator_tool_original", "create_search_tool_original", "create_rag_tool_original",
    "MACSChatModelWrapper", "MiniMaxChatModel", "DeepSeekChatModel", "create_chat_model",
    "MACSToolAdapter", "create_langchain_tool", "create_calculator_tool",
    "CollaborationChain", "create_hierarchical_chain", "create_pipeline_chain", "create_parallel_chain",
    "MACSReActAgent", "MACSReActAgentFactory",
    "MACSMemoryAdapter", "SharedMemoryAdapter", "create_memory_adapter", "create_memory_for_chain",
    "RAGEngineRetriever", "RAGEngineVectorStore", "create_retriever", "create_vectorstore",
]

LangChainReActAgent = LangChainReActAgentOriginal

if create_langchain_tool_new is not None:
    create_langchain_tool = create_langchain_tool_new
else:
    create_langchain_tool = create_langchain_tool_original

if create_calculator_tool_new is not None:
    create_calculator_tool = create_calculator_tool_new
else:
    create_calculator_tool = create_calculator_tool_original
