"""Tests for CitationTracker."""

import pytest
from macs_pkg.core.citation import CitationTracker, Citation, Claim


class TestCitationTracker:
    """Tests for CitationTracker."""

    def test_track_single_source(self):
        tracker = CitationTracker()
        label, citation = tracker.track(
            url="https://example.com/paper",
            title="Example Paper",
            snippet="A groundbreaking study.",
            agent_id="executor",
        )

        assert label == "source_1"
        assert citation.id == "source_1"
        assert citation.url == "https://example.com/paper"
        assert citation.title == "Example Paper"
        assert citation.snippet == "A groundbreaking study."
        assert citation.agent_id == "executor"
        assert citation.accessed_at != ""

    def test_track_multiple_sources(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://a.com", title="A")
        l2, _ = tracker.track(url="https://b.com", title="B")
        l3, _ = tracker.track(url="https://c.com", title="C")

        assert l1 == "source_1"
        assert l2 == "source_2"
        assert l3 == "source_3"

    def test_get_citation(self):
        tracker = CitationTracker()
        label, _ = tracker.track(url="https://x.com", title="X Title")

        retrieved = tracker.get_citation(label)
        assert retrieved is not None
        assert retrieved.title == "X Title"

        assert tracker.get_citation("source_999") is None

    def test_bind_claim_single_source(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://x.com", title="X")

        claim_id = tracker.bind_claim(
            source_ids=[l1],
            claim_content="This proves X is true.",
            agent_id="reviewer",
            turn=1,
        )

        assert claim_id != ""
        claim = tracker.get_claim(claim_id)
        assert claim is not None
        assert claim.content == "This proves X is true."
        assert claim.agent_id == "reviewer"
        assert claim.turn == 1
        assert claim.source_ids == ["source_1"]

    def test_bind_claim_multiple_sources(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://a.com", title="A")
        l2, _ = tracker.track(url="https://b.com", title="B")

        claim_id = tracker.bind_claim(
            source_ids=[l1, l2],
            claim_content="Both A and B confirm the result.",
        )

        claim = tracker.get_claim(claim_id)
        assert claim is not None
        assert set(claim.source_ids) == {"source_1", "source_2"}

    def test_bind_claim_ignores_invalid_sources(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://a.com", title="A")

        claim_id = tracker.bind_claim(
            source_ids=["source_1", "source_99"],
            claim_content="Claim with one valid and one invalid source.",
        )

        claim = tracker.get_claim(claim_id)
        assert claim is not None
        assert claim.source_ids == ["source_1"]

    def test_get_citation_graph(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://a.com", title="A")
        l2, _ = tracker.track(url="https://b.com", title="B")

        c1 = tracker.bind_claim(source_ids=[l1], claim_content="Claim A")
        c2 = tracker.bind_claim(source_ids=[l1, l2], claim_content="Claim AB")

        graph = tracker.get_citation_graph()

        assert len(graph["citations"]) == 2
        assert len(graph["claims"]) == 2
        assert len(graph["edges"]) == 2

        edge1 = next(e for e in graph["edges"] if e["claim_id"] == c1)
        assert edge1["source_ids"] == ["source_1"]

        edge2 = next(e for e in graph["edges"] if e["claim_id"] == c2)
        assert set(edge2["source_ids"]) == {"source_1", "source_2"}

    def test_format_report_inline(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://a.com", title="A")
        l2, _ = tracker.track(url="https://b.com", title="B")

        tracker.bind_claim(source_ids=[l1], claim_content="Claim A")
        tracker.bind_claim(source_ids=[l2], claim_content="Claim B")

        text = "According to the data[source_1] and prior work[source_2], the hypothesis holds."
        result = tracker.format_report(text, inline=True, footnotes=False)

        assert "According to the data[1]" in result
        assert "prior work[2]" in result

    def test_format_report_footnotes(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://a.com", title="Article A")
        l2, _ = tracker.track(url="https://b.com", title="Article B")

        text = "This is true[source_1] and also true[source_2]."

        result = tracker.format_report(text, inline=True, footnotes=True)

        assert "[1]" in result
        assert "[2]" in result
        assert "##参考文献" in result
        assert "Article A" in result
        assert "Article B" in result

    def test_format_report_no_citations(self):
        tracker = CitationTracker()
        text = "Just a plain text with no citations."
        result = tracker.format_report(text)
        assert result == text

    def test_format_report_skips_invalid_labels(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://a.com", title="A")

        text = "Valid[source_1] and invalid[source_99]."
        result = tracker.format_report(text, inline=True, footnotes=False)

        assert "[1]" in result
        assert "[source_99]" in result  # not replaced

    def test_format_report_superscript_style(self):
        tracker = CitationTracker()
        l1, _ = tracker.track(url="https://a.com", title="A")

        text = "The result[source_1] is significant."
        result = tracker.format_report(text, inline=False, footnotes=False)

        assert "[1]" in result
        assert "[source_1]" not in result

    def test_empty_tracker(self):
        tracker = CitationTracker()
        graph = tracker.get_citation_graph()
        assert graph["citations"] == []
        assert graph["claims"] == []
        assert graph["edges"] == []

        result = tracker.format_report("No citations here.")
        assert result == "No citations here."


class TestCitationModel:
    """Tests for Citation and Claim dataclasses."""

    def test_citation_create(self):
        citation, mark = Citation.create(
            url="https://x.com",
            title="X",
            snippet="Important finding.",
            agent_id="executor",
        )
        assert mark == ""
        assert citation.url == "https://x.com"
        assert citation.title == "X"
        assert citation.snippet == "Important finding."
        assert citation.agent_id == "executor"

    def test_claim_default_fields(self):
        claim = Claim(id="test-id", content="Something is the case.")
        assert claim.agent_id == ""
        assert claim.turn == 0
        assert claim.source_ids == []