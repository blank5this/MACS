"""Web Search Tool - 支持多种搜索后端.

支持的后端:
- DuckDuckGo (免费, 无需 API Key)
- Tavily AI (需要 API Key, 效果更好)

使用方式::

    tool = DuckDuckGoSearchTool()
    result = await tool.run("量子计算最新进展")
    # result.items[0].url / result.items[0].title / result.items[0].snippet

    tool = TavilySearchTool(api_key="your_key")
    result = await tool.run("AI研究进展", num_results=10)
"""

from __future__ import annotations

import os
import re
import json
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional

from .base import (
    BaseTool,
    ToolParameter,
    ToolResult,
    ToolSpec,
    TypedToolResult,
    SearchResultOutput,
)


@dataclass
class _RawSearchResult:
    """Internal raw search result before Pydantic validation."""
    title: str
    url: str
    snippet: str
    source: str = ""


class BaseSearchTool(BaseTool):
    """搜索工具基类 — 返回 TypedToolResult[SearchResultOutput]。

    run() 返回 ToolResult，但内部调用 _search() 返回 List[SearchResultOutput]。
    子类只需实现 _search()。
    """

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_search",
            description="Search the web for information. Returns structured results with url, title, snippet.",
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="The search query (in Chinese or English)",
                ),
                ToolParameter(
                    name="num_results",
                    type="integer",
                    description="Number of results to return (default: 5)",
                    required=False,
                    default=5,
                ),
            ],
        )

    @abstractmethod
    async def _search(
        self, query: str, num_results: int
    ) -> List[SearchResultOutput]:
        """执行搜索 — 子类实现此方法返回结构化结果。"""
        pass

    async def run(self, query: str, num_results: int = 5) -> ToolResult:
        """Execute search and return typed results.

        Returns ToolResult whose output is a formatted string AND whose
        metadata["items"] holds List[SearchResultOutput] for structured access.
        """
        try:
            items = await self._search(query, num_results)

            # Build formatted string for LLM consumption
            output = "\n".join(
                f"[{i+1}] {r.title}\n   URL: {r.url}\n   {r.snippet}"
                for i, r in enumerate(items)
            )

            typed = TypedToolResult(
                success=True,
                items=items,
                metadata={"query": query, "num_results": len(items)},
            )
            # Carry items through metadata for structured access
            result = typed.to_tool_result()
            result.metadata["items"] = [
                it.model_dump() if hasattr(it, "model_dump") else {
                    "url": it.url,
                    "title": it.title,
                    "snippet": it.snippet,
                    "source": it.source,
                    "score": it.score,
                }
                for it in items
            ]
            result.metadata["query"] = query
            return result

        except Exception as e:
            typed = TypedToolResult.from_search_results(
                [], query=query, error=str(e)
            )
            return typed.to_tool_result()


class DuckDuckGoSearchTool(BaseSearchTool):
    """DuckDuckGo 搜索 (免费, 无需 API Key)."""

    def __init__(self):
        self._cache: dict[str, _RawSearchResult] = {}

    async def _search(
        self, query: str, num_results: int
    ) -> List[SearchResultOutput]:
        cache_key = f"{query}:{num_results}"
        if cache_key in self._cache:
            raw = self._cache[cache_key]
            return [
                SearchResultOutput(
                    url=raw.url,
                    title=raw.title,
                    snippet=raw.snippet,
                    source=raw.source,
                    score=None,
                )
            ]

        try:
            import urllib.request
            import urllib.parse

            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8")

            raw_results: List[_RawSearchResult] = []
            # Pattern 1: full result with snippet
            pattern1 = re.compile(
                r'<a class="result__a" href="([^"]+)">([^<]+)</a>.*?'
                r'<a class="result__snippet"[^>]*>([^<]+)</a>',
                re.DOTALL,
            )
            for match in pattern1.finditer(html):
                url, title, snippet = match.groups()
                snippet = re.sub(r"<[^>]+>", "", snippet)
                raw_results.append(
                    _RawSearchResult(
                        title=title.strip(),
                        url=url.strip(),
                        snippet=snippet.strip()[:200],
                        source="DuckDuckGo",
                    )
                )
                if len(raw_results) >= num_results:
                    break

            # Pattern 2: fallback when snippet not present
            if not raw_results:
                pattern2 = re.compile(
                    r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
                )
                for match in pattern2.finditer(html):
                    raw_results.append(
                        _RawSearchResult(
                            title=match.group(2).strip(),
                            url=match.group(1).strip(),
                            snippet="",
                            source="DuckDuckGo",
                        )
                    )
                    if len(raw_results) >= num_results:
                        break

            items = [
                SearchResultOutput(
                    url=r.url,
                    title=r.title,
                    snippet=r.snippet,
                    source=r.source,
                    score=None,
                )
                for r in raw_results
            ]
            self._cache[cache_key] = raw_results[0] if raw_results else _RawSearchResult(
                title="No results", url="", snippet="", source="DuckDuckGo"
            )
            return items

        except Exception as e:
            return [
                SearchResultOutput(
                    url="",
                    title="Search Error",
                    snippet=str(e),
                    source="error",
                    score=None,
                )
            ]


class TavilySearchTool(BaseSearchTool):
    """Tavily AI 搜索 (需要 API Key, 效果更好).

    注册: https://tavily.com
    """

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("TAVILY_API_KEY", "")
        self._cache: dict[str, List[SearchResultOutput]] = {}

    async def _search(
        self, query: str, num_results: int
    ) -> List[SearchResultOutput]:
        import urllib.request
        import urllib.error

        cache_key = f"{query}:{num_results}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        payload = json.dumps({
            "api_key": self._api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": num_results,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                self.BASE_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            items = [
                SearchResultOutput(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    snippet=r.get("content", ""),
                    source="Tavily",
                    score=r.get("score"),
                )
                for r in data.get("results", [])
            ]
            self._cache[cache_key] = items
            return items

        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else "Unknown error"
            return [
                SearchResultOutput(
                    url="",
                    title="Tavily API Error",
                    snippet=f"Status {e.code}: {body}",
                    source="error",
                    score=None,
                )
            ]
        except Exception as e:
            return [
                SearchResultOutput(
                    url="",
                    title="Search Error",
                    snippet=str(e),
                    source="error",
                    score=None,
                )
            ]


# Backward-compatibility alias: old code imports SearchResult from here
SearchResult = SearchResultOutput


def create_search_tool(
    backend: str = "duckduckgo",
    api_key: Optional[str] = None,
) -> BaseSearchTool:
    """创建搜索工具.

    Args:
        backend: 后端类型 ("duckduckgo", "tavily")
        api_key: API Key (tavily 需要)

    Returns:
        BaseSearchTool 实例
    """
    backend = backend.lower()
    if backend in ("duckduckgo", "ddg"):
        return DuckDuckGoSearchTool()
    elif backend == "tavily":
        return TavilySearchTool(api_key=api_key)
    else:
        raise ValueError(f"Unknown backend: {backend}")
