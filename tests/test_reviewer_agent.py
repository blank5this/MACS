"""Tests for Reviewer Agent."""

import pytest

from macs_pkg.agents.reviewer import ReviewerAgent
from macs_pkg.core.agent import AgentRole, Message


# ─────────────────────────────────────────────────────────────────────────────
# Mock provider helpers
# ─────────────────────────────────────────────────────────────────────────────

class _Resp:
    def __init__(self, content):
        self.content = content
        self.model = "mock"
        self.usage = {"input_tokens": 1, "output_tokens": 1}
        self.tool_calls = []
        self.stop_reason = "stop"


class _ListProvider:
    """Mock provider that returns a JSON list of reviews — what reviewer expects."""

    def __init__(self, content):
        self.content = content
        self.calls = 0

    async def complete(self, messages, system=None, tools=None,
                       max_tokens=1024, temperature=0.7, **kwargs):
        self.calls += 1
        return _Resp(self.content)

    def model_name(self):
        return "mock"


# ─────────────────────────────────────────────────────────────────────────────
# Initialization & configuration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_initialization_defaults():
    r = ReviewerAgent(name="r1")
    assert r.name == "r1"
    assert r.role == AgentRole.REVIEWER
    assert r.quality_threshold == 0.7
    assert r._criteria == ["completeness", "correctness", "relevance"]
    assert r._provider is None
    assert r._enable_llm is False


@pytest.mark.asyncio
async def test_reviewer_set_criteria():
    r = ReviewerAgent(name="r1")
    r.set_criteria(["accuracy", "safety"])
    assert r._criteria == ["accuracy", "safety"]


@pytest.mark.asyncio
async def test_reviewer_set_provider_enables_llm():
    r = ReviewerAgent(name="r1")
    assert r._enable_llm is False
    r.set_provider(_ListProvider("[]"))
    assert r._enable_llm is True


# ─────────────────────────────────────────────────────────────────────────────
# think() — action routing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_think_review_action():
    r = ReviewerAgent(name="r1")
    msg = Message(
        sender="leader",
        receiver="r1",
        content={"action": "review", "results": [{"final_output": "ok"}]},
        msg_type="task",
    )
    resp = await r.think(msg)
    assert resp.content["action"] == "review_ready"
    assert "review_plan" in resp.content
    assert "criteria" in resp.content


@pytest.mark.asyncio
async def test_reviewer_think_propose_and_vote():
    r = ReviewerAgent(name="r1")
    propose_msg = Message(sender="x", receiver="r1",
                          content={"action": "propose", "task": "audit a result"})
    resp = await r.think(propose_msg)
    assert resp.content["action"] == "propose"
    assert resp.content["proposer"] == "r1"
    assert "proposal" in resp.content

    # vote — confidence 0.9 → approve
    vote_msg = Message(sender="x", receiver="r1",
                       content={"action": "vote", "proposal": {"confidence": 0.9}})
    resp = await r.think(vote_msg)
    assert resp.content["vote"] == "approve"

    # vote — confidence 0.3 → reject
    vote_msg2 = Message(sender="x", receiver="r1",
                        content={"action": "vote", "proposal": {"confidence": 0.3}})
    resp = await r.think(vote_msg2)
    assert resp.content["vote"] == "reject"


@pytest.mark.asyncio
async def test_reviewer_think_unknown_action_reports_error():
    r = ReviewerAgent(name="r1")
    msg = Message(sender="x", receiver="r1",
                  content={"action": "blah"})
    resp = await r.think(msg)
    assert resp.content["action"] == "unknown"
    assert "blah" in resp.content["error"]


# ─────────────────────────────────────────────────────────────────────────────
# act() — review execution (simple fallback)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_act_simple_path_approves_good_result():
    r = ReviewerAgent(name="r1", quality_threshold=0.7)
    good = {"subtask_id": "1", "final_output": "completed successfully"}

    review_msg = Message(sender="leader", receiver="r1",
                         content={"action": "review", "results": [good]})
    response = await r.think(review_msg)
    outgoing = await r.act(response)

    assert len(outgoing) == 1
    payload = outgoing[0].content
    assert payload["action"] == "review_complete"
    assert payload["approved"] is True  # heuristic scoring ≥ 0.7
    assert "aggregated" in payload


@pytest.mark.asyncio
async def test_reviewer_act_rejects_error_result():
    r = ReviewerAgent(name="r1", quality_threshold=0.7)
    bad = {"error": "execution failed"}

    review_msg = Message(sender="leader", receiver="r1",
                         content={"action": "review", "results": [bad]})
    response = await r.think(review_msg)
    outgoing = await r.act(response)

    payload = outgoing[0].content
    # correctness=0.0 → overall drops below threshold
    assert payload["approved"] is False
    assert payload["feedback"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# act() — LLM-driven review path
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_act_llm_returns_list_of_reviews():
    provider = _ListProvider(
        '[{"result":"x","scores":{"completeness":0.9,"correctness":0.95,"relevance":0.9},'
        '"feedback":["solid"],"issues":[]}]'
    )
    r = ReviewerAgent(name="r1", provider=provider)
    review_msg = Message(sender="x", receiver="r1",
                         content={"action": "review",
                                  "results": [{"final_output": "ok"}]})
    response = await r.think(review_msg)
    outgoing = await r.act(response)
    assert provider.calls == 1
    assert outgoing[0].content["approved"] is True


@pytest.mark.asyncio
async def test_reviewer_act_llm_non_list_falls_back():
    # provider returns dict instead of list → reviewer must degrade to simple
    provider = _ListProvider('{"oops": "this should be a list"}')
    r = ReviewerAgent(name="r1", provider=provider)
    review_msg = Message(sender="x", receiver="r1",
                         content={"action": "review",
                                  "results": [{"final_output": "ok"}]})
    response = await r.think(review_msg)
    outgoing = await r.act(response)
    # we don't crash — we get a review_complete with whatever the simple
    # scorer produced
    assert outgoing[0].content["action"] == "review_complete"


# ─────────────────────────────────────────────────────────────────────────────
# ReactAgent lifecycle enforcement
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_act_before_think_raises():
    r = ReviewerAgent(name="r1")
    fake_response = Message(sender="r1", content={"action": "review_ready",
                                                  "results_to_review": [],
                                                  "review_plan": []})
    with pytest.raises(RuntimeError, match="act.*called before think"):
        await r.act(fake_response)


# ─────────────────────────────────────────────────────────────────────────────
# _aggregate_reviews
# ─────────────────────────────────────────────────────────────────────────────

def test_reviewer_aggregate_empty_returns_zero():
    r = ReviewerAgent(name="r1")
    agg = r._aggregate_reviews([])
    assert agg["overall_score"] == 0
    assert agg["feedback"] == []


def test_reviewer_aggregate_averages_scores():
    r = ReviewerAgent(name="r1")
    agg = r._aggregate_reviews([
        {"scores": {"a": 1.0, "b": 0.5}, "feedback": ["good"]},
        {"scores": {"a": 0.5, "b": 0.5}, "feedback": ["meh", "good"]},
    ])
    assert agg["criterion_scores"]["a"] == pytest.approx(0.75)
    assert agg["criterion_scores"]["b"] == pytest.approx(0.5)
    assert agg["overall_score"] == pytest.approx(0.625)
    # feedback is deduplicated
    assert sorted(agg["feedback"]) == ["good", "meh"]


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic scorers
# ─────────────────────────────────────────────────────────────────────────────

def test_reviewer_score_completeness():
    r = ReviewerAgent(name="r1")
    assert r._score_completeness({"subtask_id": "x", "final_output": "y"}) == 1.0
    assert r._score_completeness({"subtask_id": "x"}) == 0.5
    assert r._score_completeness({}) == 0.0
    assert r._score_completeness("non-dict truthy") == 0.8
    assert r._score_completeness(None) == 0.0


def test_reviewer_score_correctness_penalises_errors():
    r = ReviewerAgent(name="r1")
    assert r._score_correctness({"error": "x"}) == 0.0
    assert r._score_correctness({"final_output": "ok"}) == 0.9


# ─────────────────────────────────────────────────────────────────────────────
# Citation integration
# ─────────────────────────────────────────────────────────────────────────────

def test_reviewer_track_source_and_bind_claim():
    r = ReviewerAgent(name="r1")
    sid1 = r.track_source("https://a.test", "A", "snippet A")
    sid2 = r.track_source("https://b.test", "B", "snippet B")
    assert sid1 != sid2

    claim_id = r.bind_claim("The sky is blue.", [sid1, sid2], turn=1)
    assert isinstance(claim_id, str)

    graph = r.get_citation_graph()
    assert "citations" in graph
    assert len(graph["citations"]) == 2
