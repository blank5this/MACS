"""RAG Search Tool — enables LLM agents to query knowledge bases via tool calling."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .base import BaseTool, ToolParameter, ToolResult, ToolSpec
from ..rag import RAGEngine, RetrievedContext


@dataclass
class RAGSearchTool(BaseTool):
    """Tool that lets agents search a RAG knowledge base.

    This enables Agentic RAG: the LLM decides when to search the knowledge base
    based on the task context, rather than always retrieving upfront.

    Usage::

        from macs_pkg.tools import ToolRegistry
        from macs_pkg.tools.rag_tool import RAGSearchTool
        from macs_pkg.rag import RAGEngine

        rag_engine = RAGEngine(config)
        rag_tool = RAGSearchTool(rag_engine, name="erp_knowledge")
        registry = ToolRegistry()
        registry.register(rag_tool)

        # Executor will now call this tool when appropriate
        executor = LLMExecutorAgent("executor", provider=provider, tool_registry=registry)
    """

    def __init__(
        self,
        rag_engine: RAGEngine,
        name: str = "rag_search",
        description: str = "Search an ERP knowledge base for relevant policies and procedures. "
                          "Use this when you need to look up company policies, operational guidelines, "
                          "or procedural steps.",
        top_k: int = 5,
        similarity_threshold: float = 0.3,
    ):
        """Initialize RAG search tool.

        Args:
            rag_engine: RAGEngine instance to query.
            name: Tool name for function calling.
            description: Description shown to the LLM.
            top_k: Number of results to return.
            similarity_threshold: Minimum similarity score (0-1).
        """
        self._rag = rag_engine
        self._name = name
        self._description = description
        self._top_k = top_k
        self._similarity_threshold = similarity_threshold

    @property
    def spec(self) -> ToolSpec:
        """Return the tool specification for LLM function calling."""
        return ToolSpec(
            name=self._name,
            description=self._description,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query. Use keywords from the ERP domain "
                               "(e.g., 'purchase requisition', 'vendor rating', 'inventory reorder').",
                    required=True,
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Optional filter by ERP category "
                               "(e.g., '采购申请', '供应商管理', '库存管理', '财务审批', '销售订单', '系统管理').",
                    required=False,
                ),
                ToolParameter(
                    name="top_k",
                    type="number",
                    description=f"Number of results to return (default: {self._top_k}, max: 20).",
                    required=False,
                    default=self._top_k,
                ),
            ],
        )

    async def execute(self, query: str, category: Optional[str] = None, top_k: Optional[int] = None) -> ToolResult:
        """Execute the RAG search.

        Args:
            query: Search query string.
            category: Optional category filter.
            top_k: Override default top_k.

        Returns:
            ToolResult with search results.
        """
        try:
            k = min(top_k or self._top_k, 20)

            # Perform search
            results: List[RetrievedContext] = await self._rag.search(
                query=query,
                top_k=k,
            )

            # Format results for LLM consumption
            if not results:
                return ToolResult(
                    success=True,
                    output="No relevant documents found for the query.",
                    metadata={"query": query, "result_count": 0},
                )

            # Format as readable text
            formatted_results = []
            for i, r in enumerate(results, 1):
                source = r.metadata.get("source", "unknown") if r.metadata else "unknown"
                cat = r.metadata.get("category", "") if r.metadata else ""
                formatted_results.append(
                    f"[{i}] {r.content}\n"
                    f"    来源: {source}" + (f" | 类别: {cat}" if cat else "")
                )

            output = "\n\n".join(formatted_results)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "query": query,
                    "result_count": len(results),
                    "categories": [r.metadata.get("category") for r in results if r.metadata],
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"RAG search failed: {str(e)}",
                metadata={"query": query},
            )

    async def run(self, query: str, category: Optional[str] = None, top_k: Optional[int] = None) -> ToolResult:
        """Execute the tool (required by BaseTool interface)."""
        return await self.execute(query=query, category=category, top_k=top_k)

    def to_openai_schema(self) -> Dict[str, Any]:
        """Return OpenAI-compatible function schema."""
        return self.spec.to_openai_schema()

    def to_anthropic_schema(self) -> Dict[str, Any]:
        """Return Anthropic-compatible tool schema."""
        return self.spec.to_anthropic_schema()
