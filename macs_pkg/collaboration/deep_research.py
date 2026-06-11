"""Deep Research collaboration mode.

Implements an iterative deep-research orchestration loop:

    Query Planning → Parallel Search → Evidence Accumulation
    → Claim Extraction → Citation Binding → Report Synthesis
    → Self-Critique + Revision (loop until quality threshold)

Inspired by: STORM (Stanford, arXiv:2410.09663),
OpenAI Deep Research, and GAIA benchmark workflows.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from ..core.agent import BaseAgent, AgentRole, Message
from ..core.citation import CitationTracker
from .base import CollaborationMode, CollaborationConfig


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SearchQuery:
    """A single sub-query produced by the query planning phase."""
    id: str
    text: str
    purpose: str  # e.g. "background", "contradicting_view", "evidence"
    priority: int = 1


@dataclass
class Evidence:
    """A piece of evidence retrieved from a search or RAG query."""
    query_id: str
    source_url: str
    source_title: str
    snippet: str
    relevance_score: float = 0.0
    agent_id: str = ""


@dataclass
class ResearchClaim:
    """A claim extracted from evidence, bound to citation IDs."""
    id: str
    text: str
    supporting_sources: List[str] = field(default_factory=list)
    agent_id: str = ""
    turn: int = 0


@dataclass
class ResearchReport:
    """The final structured research report."""
    title: str
    abstract: str = ""
    sections: List[Dict[str, str]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    citation_graph: Dict[str, Any] = field(default_factory=dict)
    claim_count: int = 0
    iteration: int = 0
    quality_score: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# DeepResearchMode
# ─────────────────────────────────────────────────────────────────────────────


class DeepResearchMode(CollaborationMode):
    """Deep research orchestration loop.

    Args:
        config: CollaborationConfig with max_iterations, stop_on_error, etc.
        citation_tracker: Optional CitationTracker instance (created if None).
        max_search_queries: Maximum number of sub-queries per iteration (default 5).
        max_evidence_per_query: Maximum evidence items to keep per query (default 10).
        quality_threshold: Quality score (0-1) to stop iteration (default 0.7).
        enable_self_critique: Whether to run self-critique + revision loop (default True).
        critique_rounds: Maximum critique rounds before accepting (default 2).

    Flow (per iteration):
        1. Query Planning — PlannerAgent decomposes topic into sub-queries
        2. Parallel Search — Execute all sub-queries via web search + RAG
        3. Evidence Accum. — Deduplicate, score, and store evidence
        4. Claim Extraction — Extract claims and bind to citation sources
        5. Report Synthesis — ReviewerAgent.synthesize() generates structured report
        6. Self-Critique — Quality check; if < threshold → revise queries → loop
    """

    name = "deep_research"
    description = (
        "Iterative deep research: plan → search → evidence → claims → "
        "synthesize → self-critique → revise (loop)"
    )

    def __init__(
        self,
        config: Optional[CollaborationConfig] = None,
        citation_tracker: Optional[CitationTracker] = None,
        max_search_queries: int = 5,
        max_evidence_per_query: int = 10,
        quality_threshold: float = 0.7,
        enable_self_critique: bool = True,
        critique_rounds: int = 2,
    ):
        super().__init__(config)
        self._tracker = citation_tracker or CitationTracker()
        self._max_search_queries = max_search_queries
        self._max_evidence_per_query = max_evidence_per_query
        self._quality_threshold = quality_threshold
        self._enable_self_critique = enable_self_critique
        self._critique_rounds = critique_rounds

        self._planner: Optional[BaseAgent] = None
        self._reviewer: Optional[BaseAgent] = None
        self._search_tools: List[Any] = []   # BaseSearchTool instances
        self._rag_tools: List[Any] = []      # RAG tool instances

        self._iteration: int = 0
        self._current_queries: List[SearchQuery] = []
        self._evidence: List[Evidence] = []
        self._claims: List[ResearchClaim] = []

    # ── CollaborationMode abstract methods ──────────────────────────────────

    def select_agents(
        self,
        task: Any,
        available_agents: List[BaseAgent],
    ) -> List[BaseAgent]:
        """Select planner and reviewer for deep research."""
        selected = []
        agent_by_role = {agent.role: agent for agent in available_agents}

        if AgentRole.PLANNER in agent_by_role:
            self._planner = agent_by_role[AgentRole.PLANNER]
            selected.append(self._planner)
        elif AgentRole.EXECUTOR in agent_by_role:
            self._planner = agent_by_role[AgentRole.EXECUTOR]
            selected.append(self._planner)

        if AgentRole.REVIEWER in agent_by_role:
            self._reviewer = agent_by_role[AgentRole.REVIEWER]
            selected.append(self._reviewer)

        return selected

    async def execute(
        self,
        task: Any,
        agents: Dict[str, BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> ResearchReport:
        """Execute the deep research loop.

        Args:
            task: Research task dict with at least "topic" or "description".
            agents: Available agents by name.
            context: Optional shared context (search_tools, rag_tools, etc.).

        Returns:
            ResearchReport with sections, citations, and quality metadata.
        """
        context = context or {}
        self._reset()

        # Collect tools from context
        self._search_tools = context.get("search_tools", [])
        self._rag_tools = context.get("rag_tools", [])

        # Ensure agents are selected
        if self._planner is None and self._reviewer is None:
            self.select_agents(task, list(agents.values()))

        topic = self._extract_topic(task)
        max_iter = self.config.max_iterations

        # ── Main research loop ─────────────────────────────────────────────
        for i in range(max_iter):
            self._iteration = i + 1

            # Phase 1: Query Planning
            queries = await self._plan_queries(topic)
            self._current_queries = queries
            if not queries:
                queries = [
                    SearchQuery(
                        id="q_fallback",
                        text=topic,
                        purpose="main",
                        priority=1,
                    )
                ]
                self._current_queries = queries

            # Phase 2: Parallel Search
            all_evidence = await self._parallel_search(queries)
            self._evidence = all_evidence

            # Phase 3: Claim Extraction + Citation Binding
            claims = await self._extract_claims(all_evidence)
            self._claims = claims

            # Phase 4: Report Synthesis
            report = await self._synthesize_report(topic, claims, all_evidence)

            # Phase 5: Self-Critique + Revision
            if self._enable_self_critique:
                quality_ok, quality_score = await self._self_critique(report)
                report.quality_score = quality_score

                if quality_ok or i == max_iter - 1:
                    return report

                # Revise topic based on gaps identified
                topic = f"{topic} (请重点关注上一轮研究中存在的空白和不足)"
            else:
                return report

        return report

    def get_required_roles(self) -> List[AgentRole]:
        """Roles required: Planner (for query planning) and optionally Reviewer."""
        return [AgentRole.PLANNER, AgentRole.REVIEWER]

    # ── Phase 1: Query Planning ────────────────────────────────────────────────

    async def _plan_queries(self, topic: str) -> List[SearchQuery]:
        """Decompose the research topic into focused sub-queries."""
        if self._planner is not None:
            return await self._plan_queries_with_llm(topic)
        return self._plan_queries_heuristic(topic)

    async def _plan_queries_with_llm(self, topic: str) -> List[SearchQuery]:
        """LLM-powered query planning via PlannerAgent."""
        msg = Message(
            sender="deep_research",
            receiver=self._planner.name,
            content={
                "action": "decompose",
                "task": {
                    "description": (
                        f"Decompose the following research topic into {self._max_search_queries} "
                        "focused sub-queries for a deep research task. "
                        "Each sub-query should cover a distinct aspect: "
                        "background, methods, findings, limitations, related work, or counterarguments."
                    ),
                    "topic": topic,
                },
            },
            msg_type="research_planning",
        )

        response = await self._planner.think(msg)
        actions = await self._planner.act(response)

        # Extract sub-queries from act() results
        sub_queries: List[SearchQuery] = []
        for action in actions:
            content = action.content
            if isinstance(content, dict):
                sq = (
                    content.get("subqueries")
                    or content.get("subtasks")
                    or content.get("queries")
                )
                if isinstance(sq, list):
                    for item in sq:
                        if isinstance(item, dict):
                            sub_queries.append(
                                SearchQuery(
                                    id=item.get("id", f"q_{len(sub_queries)}"),
                                    text=item.get("text", "") or item.get("query", "") or item.get("description", ""),
                                    purpose=item.get("purpose", "main"),
                                    priority=item.get("priority", 1),
                                )
                            )
                        elif isinstance(item, str):
                            sub_queries.append(
                                SearchQuery(
                                    id=f"q_{len(sub_queries)}",
                                    text=item,
                                    purpose="main",
                                    priority=1,
                                )
                            )

        # Also check think() response content
        if not sub_queries:
            content = response.content
            if isinstance(content, dict):
                sq = (
                    content.get("subqueries")
                    or content.get("subtasks")
                    or content.get("queries")
                )
                if isinstance(sq, list):
                    for item in sq:
                        if isinstance(item, dict):
                            sub_queries.append(
                                SearchQuery(
                                    id=item.get("id", f"q_{len(sub_queries)}"),
                                    text=item.get("text", "") or item.get("query", ""),
                                    purpose=item.get("purpose", "main"),
                                    priority=item.get("priority", 1),
                                )
                            )

        return sub_queries[: self._max_search_queries]

    def _plan_queries_heuristic(self, topic: str) -> List[SearchQuery]:
        """Fallback heuristic query planning without LLM."""
        base_purposes = [
            ("背景与动机", "background"),
            ("主要方法", "methods"),
            ("核心发现", "findings"),
            ("局限性", "limitations"),
            ("相关工作对比", "related_work"),
        ]
        queries = []
        for i, (label, purpose) in enumerate(base_purposes[: self._max_search_queries]):
            queries.append(
                SearchQuery(
                    id=f"q_{i}",
                    text=f"{topic}：{label}",
                    purpose=purpose,
                    priority=len(base_purposes) - i,
                )
            )
        return queries

    # ── Phase 2: Parallel Search ──────────────────────────────────────────────

    async def _parallel_search(self, queries: List[SearchQuery]) -> List[Evidence]:
        """Execute all search queries in parallel, merge with RAG results."""
        tasks = [self._search_single_query(q) for q in queries]
        results_per_query = await asyncio.gather(*tasks, return_exceptions=True)

        all_evidence: List[Evidence] = []
        for result in results_per_query:
            if isinstance(result, Exception):
                continue
            all_evidence.extend(result)

        # Deduplicate by URL
        seen_urls: Set[str] = set()
        deduped = []
        for ev in all_evidence:
            if ev.source_url and ev.source_url not in seen_urls:
                seen_urls.add(ev.source_url)
                deduped.append(ev)

        return deduped

    async def _search_single_query(self, query: SearchQuery) -> List[Evidence]:
        """Search using all available search tools for one query."""
        evidence_list: List[Evidence] = []

        async def run_search_tool(tool: Any) -> List[Evidence]:
            try:
                result = await tool.run(query.text, num_results=self._max_evidence_per_query)
                if not result.success or not result.output:
                    return []
                return self._parse_search_result(result.output, query.id, tool)
            except Exception:
                return []

        # Run all search tools in parallel
        tool_tasks = [run_search_tool(t) for t in self._search_tools]
        tool_results = await asyncio.gather(*tool_tasks, return_exceptions=True)

        for r in tool_results:
            if isinstance(r, Exception):
                continue
            evidence_list.extend(r)

        # Also run RAG tools
        for tool in self._rag_tools:
            try:
                result = await tool.run(query.text, top_k=self._max_evidence_per_query)
                if result.success and result.output:
                    evidence_list.extend(
                        self._parse_rag_result(result.output, query.id, tool)
                    )
            except Exception:
                continue

        return evidence_list

    def _parse_search_result(
        self, output: str, query_id: str, tool: Any
    ) -> List[Evidence]:
        """Parse search tool output into Evidence list."""
        evidence = []
        spec = getattr(tool, "spec", None)
        tool_name = spec.name if spec else getattr(tool, "__class__", None).__name__

        # Parse lines like "[1] Title\n URL: ...\n   snippet"
        entry_pattern = re.compile(
            r"\[\d+\]\s+(.+?)\n\s*URL:\s*(\S+)\n\s+(.+?)(?=\n\[\d+\]|\Z)",
            re.DOTALL,
        )
        for match in entry_pattern.finditer(output):
            title, url, snippet = match.groups()
            self._tracker.track(
                url=url.strip(),
                title=title.strip(),
                snippet=snippet.strip()[:300],
                agent_id=f"search:{tool_name}",
            )
            evidence.append(
                Evidence(
                    query_id=query_id,
                    source_url=url.strip(),
                    source_title=title.strip(),
                    snippet=snippet.strip()[:300],
                    relevance_score=0.5,
                    agent_id=f"search:{tool_name}",
                )
            )
        return evidence

    def _parse_rag_result(
        self, output: str, query_id: str, tool: Any
    ) -> List[Evidence]:
        """Parse RAG tool output into Evidence list."""
        evidence = []
        tool_name = getattr(tool, "__class__", None).__name__

        entry_pattern = re.compile(
            r"\[(\d+)\]\s*(.+?)\n\s*URL:\s*(\S+)\n\s*(.+?)(?=\n\[\d+\]|\Z)",
            re.DOTALL,
        )
        for match in entry_pattern.finditer(output):
            score_str, title, url, snippet = match.groups()
            evidence.append(
                Evidence(
                    query_id=query_id,
                    source_url=url.strip(),
                    source_title=title.strip(),
                    snippet=snippet.strip()[:300],
                    relevance_score=float(score_str) / 100.0 if score_str else 0.5,
                    agent_id=f"rag:{tool_name}",
                )
            )
        return evidence

    # ── Phase 3: Claim Extraction + Citation Binding ─────────────────────────

    async def _extract_claims(
        self, evidence: List[Evidence]
    ) -> List[ResearchClaim]:
        """Extract claims from evidence and bind them to citations."""
        claims: List[ResearchClaim] = []

        # Group evidence by query_id
        by_query: Dict[str, List[Evidence]] = {}
        for ev in evidence:
            by_query.setdefault(ev.query_id, []).append(ev)

        for query_id, evs in by_query.items():
            snippets = [e.snippet for e in evs if e.snippet]
            if not snippets:
                continue

            # Bind each evidence URL to the claim via CitationTracker
            source_labels = []
            for e in evs:
                label, _ = self._tracker.track(
                    url=e.source_url,
                    title=e.source_title,
                    snippet=e.snippet,
                    agent_id=e.agent_id,
                )
                source_labels.append(label)

            claim_text = (
                f"Regarding '{query_id}': "
                f"evidence from {len(evs)} sources indicates: "
                f"{snippets[0][:200]}"
            )
            claim_id = str(uuid.uuid4())[:8]
            claims.append(
                ResearchClaim(
                    id=claim_id,
                    text=claim_text,
                    supporting_sources=source_labels,
                    turn=self._iteration,
                )
            )

        return claims

    # ── Phase 4: Report Synthesis ───────────────────────────────────────────

    async def _synthesize_report(
        self,
        topic: str,
        claims: List[ResearchClaim],
        evidence: List[Evidence],
    ) -> ResearchReport:
        """Build sections from claims and synthesize via ReviewerAgent."""
        # Build sections
        sections: List[Dict[str, Any]] = []

        # Abstract
        sections.append({
            "title": "摘要",
            "content": (
                f"本报告围绕「{topic}」展开系统研究，"
                f"综合 {len(evidence)} 条来源，形成 {len(claims)} 条核心声明。"
            ),
            "evidence": [
                {"url": e.source_url, "title": e.source_title, "snippet": e.snippet}
                for e in evidence[:3]
            ],
            "claims": [c.text for c in claims[:3]],
        })

        # Group claims into thematic sections (simple first-come bucket)
        theme_buckets: List[Dict[str, Any]] = []
        for claim in claims:
            if len(theme_buckets) < 4:
                theme_buckets.append({
                    "title": f"第{len(theme_buckets) + 1}节：核心发现",
                    "content": claim.text,
                    "evidence": [
                        {"url": e.source_url, "title": e.source_title, "snippet": e.snippet}
                        for e in evidence
                        if any(s in e.snippet for s in claim.text.split()[:5])
                    ][:3],
                    "claims": [claim.text],
                })
            else:
                theme_buckets[-1]["content"] += f"\n\n{claim.text}"
                theme_buckets[-1]["claims"].append(claim.text)

        sections.extend(theme_buckets)

        # 参考文献
        cited_urls = {e.source_url for e in evidence if e.source_url}
        ref_sources: List[Dict[str, str]] = []
        for e in evidence:
            if e.source_url in cited_urls and not any(
                r["url"] == e.source_url for r in ref_sources
            ):
                ref_sources.append({
                    "url": e.source_url,
                    "title": e.source_title,
                    "snippet": e.snippet,
                })
                cited_urls.discard(e.source_url)

        sections.append({
            "title": "参考文献",
            "content": "\n".join(f"- {s['title']}: {s['url']}" for s in ref_sources),
            "evidence": ref_sources,
            "claims": [],
        })

        # Use ReviewerAgent.synthesize() if available
        if self._reviewer is not None:
            try:
                synthesis = await self._reviewer.synthesize(sections)
                return ResearchReport(
                    title=topic,
                    abstract=sections[0]["content"],
                    sections=[{
                        "title": s["title"],
                        "content": synthesis.get("report", s["content"]),
                    } for s in sections[1:]],
                    citations=synthesis.get("citations", []),
                    citation_graph=synthesis.get("citation_graph", {}),
                    claim_count=synthesis.get("claim_count", len(claims)),
                    iteration=self._iteration,
                    quality_score=0.0,
                )
            except Exception:
                pass

        # Fallback: plain-text synthesis
        plain_parts = []
        for s in sections:
            plain_parts.append(f"## {s['title']}\n{s['content']}")

        return ResearchReport(
            title=topic,
            abstract=sections[0]["content"],
            sections=[{"title": s["title"], "content": s["content"]} for s in sections[1:]],
            citations=[{"url": e.source_url, "title": e.source_title} for e in evidence],
            citation_graph=self._tracker.get_citation_graph(),
            claim_count=len(claims),
            iteration=self._iteration,
            quality_score=0.0,
        )

    # ── Phase 5: Self-Critique + Revision ──────────────────────────────────

    async def _self_critique(self, report: ResearchReport) -> tuple[bool, float]:
        """Evaluate report quality and decide if revision is needed.

        Returns (quality_ok, quality_score).
        """
        if self._reviewer is None:
            return True, 0.75

        try:
            review_msg = Message(
                sender="deep_research",
                receiver=self._reviewer.name,
                content={
                    "action": "review",
                    "results": [{
                        "report_title": report.title,
                        "sections_count": len(report.sections),
                        "citations_count": len(report.citations),
                        "claim_count": report.claim_count,
                        "abstract": report.abstract,
                    }],
                },
                msg_type="quality_review",
            )
            think_resp = await self._reviewer.think(review_msg)
            act_resp = await self._reviewer.act(think_resp)

            score = 0.0
            for action in act_resp:
                content = action.content
                if isinstance(content, dict):
                    agg = content.get("aggregated", {})
                    score = agg.get("overall_score", 0.0)
                    break
            if score == 0.0 and isinstance(think_resp.content, dict):
                score = think_resp.content.get("aggregated", {}).get("overall_score", 0.0)

            quality_ok = score >= self._quality_threshold
            return quality_ok, score

        except Exception:
            return True, 0.5

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _extract_topic(self, task: Any) -> str:
        """Extract the research topic string from a task dict."""
        if isinstance(task, str):
            return task
        if isinstance(task, dict):
            return (
                task.get("topic")
                or task.get("description")
                or task.get("title", "")
                or str(task)
            )
        return str(task)

    def _deduplicate_evidence(self, evidence: List[Evidence]) -> List[Evidence]:
        """Deduplicate evidence by URL, preserving first-seen order."""
        seen_urls: Set[str] = set()
        deduped = []
        for ev in evidence:
            if ev.source_url and ev.source_url not in seen_urls:
                seen_urls.add(ev.source_url)
                deduped.append(ev)
        return deduped

    def _reset(self) -> None:
        """Reset per-run state."""
        self._iteration = 0
        self._current_queries = []
        self._evidence = []
        self._claims = []
        self._tracker = CitationTracker()
