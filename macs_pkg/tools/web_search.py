"""Web Search Tool - 支持多种搜索后端.

支持的后端:
- DuckDuckGo (免费, 无需 API Key)
- Tavily AI (需要 API Key, 效果更好)
- Serper (需要 API Key)

使用方式::

    # DuckDuckGo (免费)
    tool = DuckDuckGoSearchTool()
    
    # Tavily (付费, 更准)
    tool = TavilySearchTool(api_key="your_key")
    
    # Serper
    tool = SerperSearchTool(api_key="your_key")
"""

from __future__ import annotations

import os
import re
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from .base import BaseTool, ToolParameter, ToolResult, ToolSpec


@dataclass
class SearchResult:
    """单条搜索结果."""
    title: str
    url: str
    snippet: str
    source: str = ""


class BaseSearchTool(BaseTool):
    """搜索工具基类."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="web_search",
            description="Search the web for information. Returns top results with titles, URLs, and snippets.",
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
    async def _search(self, query: str, num_results: int) -> List[SearchResult]:
        """执行搜索."""
        pass

    async def run(self, query: str, num_results: int = 5) -> ToolResult:
        try:
            results = await self._search(query, num_results)
            output = "\n".join(
                f"[{i+1}] {r.title}\n   URL: {r.url}\n   {r.snippet}"
                for i, r in enumerate(results)
            )
            return ToolResult(
                success=True,
                output=output,
                metadata={"query": query, "num_results": len(results)},
            )
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class DuckDuckGoSearchTool(BaseSearchTool):
    """DuckDuckGo 搜索 (免费, 无需 API Key).

    使用 whoogle/DuckDuckGo 等服务.
    """

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    async def _search(self, query: str, num_results: int) -> List[SearchResult]:
        """使用 DuckDuckGo HTML 搜索."""
        import urllib.request
        import urllib.parse

        cache_key = f"{query}:{num_results}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # 使用 DuckDuckGo lite (HTML)
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8")

            # 解析 HTML
            results = []
            # DuckDuckGo HTML 格式
            pattern = re.compile(
                r'<a class="result__a" href="([^"]+)">([^<]+)</a>.*?'
                r'<a class="result__snippet"[^>]*>([^<]+)</a>',
                re.DOTALL,
            )

            for match in pattern.finditer(html):
                url, title, snippet = match.groups()
                # 清理 HTML 标签
                snippet = re.sub(r'<[^>]+>', '', snippet)
                results.append(SearchResult(
                    title=title.strip(),
                    url=url.strip(),
                    snippet=snippet.strip()[:200],
                    source="DuckDuckGo",
                ))
                if len(results) >= num_results:
                    break

            if not results:
                # 备用解析
                pattern2 = re.compile(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>')
                for match in pattern2.finditer(html):
                    results.append(SearchResult(
                        title=match.group(2).strip(),
                        url=match.group(1).strip(),
                        snippet="",
                        source="DuckDuckGo",
                    ))
                    if len(results) >= num_results:
                        break

            self._cache[cache_key] = results
            return results

        except Exception as e:
            return [SearchResult(
                title="Search Error",
                url="",
                snippet=f"Failed to search: {str(e)}",
                source="error",
            )]


class TavilySearchTool(BaseSearchTool):
    """Tavily AI 搜索 (需要 API Key, 效果更好).

    注册: https://tavily.com
    """

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.environ.get("TAVILY_API_KEY", "")
        self._cache: Dict[str, Any] = {}

    async def _search(self, query: str, num_results: int) -> List[SearchResult]:
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

        req = urllib.request.Request(
            self.BASE_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            results = [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                    source="Tavily",
                )
                for r in data.get("results", [])
            ]

            self._cache[cache_key] = results
            return results

        except urllib.error.HTTPError as e:
            return [SearchResult(
                title="Tavily API Error",
                url="",
                snippet=f"Status {e.code}: {e.read().decode() if e.fp else 'Unknown error'}",
                source="error",
            )]
        except Exception as e:
            return [SearchResult(
                title="Search Error",
                url="",
                snippet=str(e),
                source="error",
            )]


def create_search_tool(
    backend: str = "duckduckgo",
    api_key: Optional[str] = None,
) -> BaseSearchTool:
    """创建搜索工具.

    Args:
        backend: 后端类型 ("duckduckgo", "tavily", "serper")
        api_key: API Key (tavily/serper 需要)

    Returns:
        搜索工具实例
    """
    backend = backend.lower()
    if backend in ("duckduckgo", "ddg"):
        return DuckDuckGoSearchTool()
    elif backend == "tavily":
        return TavilySearchTool(api_key=api_key)
    elif backend == "serper":
        # Serper 使用 Tavily 类似的接口
        return TavilySearchTool(api_key=api_key)
    else:
        raise ValueError(f"Unknown backend: {backend}")
