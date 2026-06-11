"""Tests for DeepResearchMode."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from macs_pkg.collaboration.deep_research import (
    DeepResearchMode,
    SearchQuery,
    Evidence,
    ResearchClaim,
    ResearchReport,
)
from macs_pkg.collaboration.base import CollaborationConfig
from macs_pkg.core.agent import AgentRole


class TestDeepResearchMode:
    """Tests for DeepResearchMode."""

    def test_init_defaults(self):
        mode = DeepResearchMode()
        assert mode.name == "deep_research"
        assert mode._tracker is not None
        assert mode._max_search_queries == 5
        assert mode._quality_threshold == 0.7
        assert mode._enable_self_critique is True
        assert mode._critique_rounds == 2

    def test_init_custom_config(self):
        config = CollaborationConfig(max_iterations=5)
        mode = DeepResearchMode(
            config=config,
            max_search_queries=3,
            quality_threshold=0.8,
            enable_self_critique=False,
        )
        assert mode.config.max_iterations == 5
        assert mode._max_search_queries == 3
        assert mode._quality_threshold == 0.8
        assert mode._enable_self_critique is False

    def test_select_agents_with_roles(self):
        mode = DeepResearchMode()
        planner = MagicMock()
        planner.role = AgentRole.PLANNER
        planner.name = "planner"
        reviewer = MagicMock()
        reviewer.role = AgentRole.REVIEWER
        reviewer.name = "reviewer"

        selected = mode.select_agents(
            task={"topic": "test"},
            available_agents=[planner, reviewer],
        )
        assert planner in selected
        assert reviewer in selected
        assert mode._planner is planner
        assert mode._reviewer is reviewer

    def test_select_agents_fallback_to_executor(self):
        mode = DeepResearchMode()
        executor = MagicMock()
        executor.role = AgentRole.EXECUTOR
        executor.name = "executor"

        selected = mode.select_agents(task={}, available_agents=[executor])
        assert executor in selected
        assert mode._planner is executor

    def test_get_required_roles(self):
        mode = DeepResearchMode()
        roles = mode.get_required_roles()
        assert AgentRole.PLANNER in roles
        assert AgentRole.REVIEWER in roles

    def test_heuristic_query_planning(self):
        mode = DeepResearchMode(max_search_queries=3)
        queries = mode._plan_queries_heuristic("量子计算")

        assert len(queries) == 3
        assert all(isinstance(q, SearchQuery) for q in queries)
        assert all("量子计算" in q.text for q in queries)
        assert [q.purpose for q in queries] == [
            "background", "methods", "findings"
        ]

    def test_heuristic_query_planning_respects_max(self):
        mode = DeepResearchMode(max_search_queries=2)
        queries = mode._plan_queries_heuristic("AI研究")
        assert len(queries) == 2

    def test_extract_topic_from_str(self):
        mode = DeepResearchMode()
        assert mode._extract_topic("量子计算最新进展") == "量子计算最新进展"

    def test_extract_topic_from_dict(self):
        mode = DeepResearchMode()
        assert mode._extract_topic({"topic": "量子计算"}) == "量子计算"
        assert mode._extract_topic({"description": "研究AI"}) == "研究AI"
        assert mode._extract_topic({"title": "论文"}) == "论文"

    def test_reset_clears_state(self):
        mode = DeepResearchMode()
        mode._iteration = 5
        mode._current_queries = [SearchQuery(id="x", text="x", purpose="p")]
        mode._evidence = [Evidence(query_id="x", source_url="u", source_title="t", snippet="s")]
        mode._claims = [ResearchClaim(id="c", text="claim")]

        mode._reset()

        assert mode._iteration == 0
        assert mode._current_queries == []
        assert mode._evidence == []
        assert mode._claims == []

    def test_search_query_dataclass(self):
        q = SearchQuery(id="q1", text="What is AI?", purpose="background", priority=2)
        assert q.id == "q1"
        assert q.text == "What is AI?"
        assert q.purpose == "background"
        assert q.priority == 2

    def test_evidence_dataclass(self):
        e = Evidence(
            query_id="q1",
            source_url="https://example.com",
            source_title="Example",
            snippet="This is an example.",
            relevance_score=0.8,
            agent_id="search",
        )
        assert e.query_id == "q1"
        assert e.relevance_score == 0.8

    def test_research_claim_dataclass(self):
        c = ResearchClaim(
            id="c1",
            text="AI is important.",
            supporting_sources=["source_1", "source_2"],
            turn=1,
        )
        assert c.id == "c1"
        assert len(c.supporting_sources) == 2
        assert c.turn == 1

    def test_research_report_dataclass(self):
        r = ResearchReport(
            title="AI研究",
            abstract="本报告研究AI。",
            sections=[{"title": "背景", "content": "AI的历史。"}],
            citations=[{"url": "https://x.com", "title": "X"}],
            claim_count=5,
            iteration=2,
            quality_score=0.85,
        )
        assert r.title == "AI研究"
        assert r.iteration == 2
        assert r.quality_score == 0.85
        assert len(r.sections) == 1
        assert len(r.citations) == 1

    @pytest.mark.asyncio
    async def test_plan_queries_with_llm_calls_planner(self):
        mode = DeepResearchMode()
        mock_planner = MagicMock()
        mock_planner.name = "planner"
        mock_planner.role = AgentRole.PLANNER

        mock_response = MagicMock()
        mock_response.content = {"subqueries": [
            {"id": "q1", "text": "query1", "purpose": "bg"},
            {"id": "q2", "text": "query2", "purpose": "ev"},
        ]}
        mock_planner.think = AsyncMock(return_value=mock_response)
        mock_planner.act = AsyncMock(return_value=[
            MagicMock(content={"subqueries": [
                {"id": "q1", "text": "query1", "purpose": "bg"},
                {"id": "q2", "text": "query2", "purpose": "ev"},
            ]})
        ])

        mode._planner = mock_planner
        queries = await mode._plan_queries_with_llm("AI研究")

        mock_planner.think.assert_called_once()
        mock_planner.act.assert_called_once()
        assert len(queries) == 2
        assert queries[0].text == "query1"
        assert queries[1].purpose == "ev"

    @pytest.mark.asyncio
    async def test_extract_claims_groups_by_query_id(self):
        mode = DeepResearchMode()
        evidence = [
            Evidence(query_id="q1", source_url="https://a.com", source_title="A", snippet="A片段", agent_id="s"),
            Evidence(query_id="q1", source_url="https://b.com", source_title="B", snippet="B片段", agent_id="s"),
            Evidence(query_id="q2", source_url="https://c.com", source_title="C", snippet="C片段", agent_id="s"),
        ]

        claims = await mode._extract_claims(evidence)

        assert len(claims) == 2  # one per unique query_id
        # Each claim should have bound sources
        for claim in claims:
            assert len(claim.supporting_sources) >= 1
            assert claim.turn == 0  # before execute() is called, iteration=0

    @pytest.mark.asyncio
    async def test_self_critique_without_reviewer(self):
        mode = DeepResearchMode()
        report = ResearchReport(title="Test", quality_score=0.0)

        ok, score = await mode._self_critique(report)

        assert ok is True
        assert score == 0.75

    @pytest.mark.asyncio
    async def test_self_critique_with_reviewer(self):
        mode = DeepResearchMode(quality_threshold=0.7)
        mock_reviewer = MagicMock()
        mock_reviewer.name = "reviewer"
        mock_reviewer.role = AgentRole.REVIEWER

        mock_think = MagicMock()
        mock_think.content = {}
        mock_reviewer.think = AsyncMock(return_value=mock_think)
        mock_reviewer.act = AsyncMock(return_value=[
            MagicMock(content={
                "action": "review_complete",
                "aggregated": {"overall_score": 0.85},
            })
        ])

        mode._reviewer = mock_reviewer
        report = ResearchReport(title="Test", quality_score=0.0)

        ok, score = await mode._self_critique(report)

        assert ok is True
        assert score == 0.85

    def test_deduplicate_by_url(self):
        mode = DeepResearchMode()
        evidence = [
            Evidence(query_id="q1", source_url="https://a.com", source_title="A", snippet="A片段"),
            Evidence(query_id="q2", source_url="https://a.com", source_title="A", snippet="A again"),
            Evidence(query_id="q3", source_url="https://b.com", source_title="B", snippet="B片段"),
        ]

        deduped = mode._deduplicate_evidence(evidence)

        assert len(deduped) == 2
        urls = {e.source_url for e in deduped}
        assert urls == {"https://a.com", "https://b.com"}

    def test_deduplicate_evidence_method(self):
        """Helper _deduplicate_evidence exists and works."""
        mode = DeepResearchMode()
        evidence = [
            Evidence(query_id="q1", source_url="https://x.com", source_title="X", snippet="x"),
        ]
        result = mode._deduplicate_evidence(evidence)
        assert len(result) == 1
