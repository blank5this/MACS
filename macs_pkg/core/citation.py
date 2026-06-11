"""Citation tracking for research agent traceability.

Provides Claim-to-Source binding, citation graph, and formatted citation markup.
Used by DeepResearchMode and ReviewerAgent to inject [source_N] references into output.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Data models
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Citation:
    """A single source citation.

    Attributes:
        id: Internal citation ID (e.g. "source_1").
        url: Source URL.
        title: Display title of the source.
        snippet: Relevant excerpt from the source.
        accessed_at: ISO timestamp when the source was retrieved.
        agent_id: Which agent retrieved this source.
    """

    id: str
    url: str
    title: str
    snippet: str = ""
    accessed_at: str = ""
    agent_id: str = ""

    @classmethod
    def create(
        cls,
        url: str,
        title: str,
        snippet: str = "",
        agent_id: str = "",
    ) -> Tuple[Citation, str]:
        """Factory: create a Citation and assign it the next sequential ID.

        Returns (citation, citation_mark) where citation_mark is "source_N".
        """
        citation = cls(
            id="",  # filled below
            url=url,
            title=title,
            snippet=snippet,
            accessed_at=datetime.now(timezone.utc).isoformat(),
            agent_id=agent_id,
        )
        # ID assigned externally by CitationTracker._next_label()
        return citation, ""


@dataclass
class Claim:
    """A claim made by an agent, bound to one or more citation sources.

    Attributes:
        id: Unique claim ID.
        content: Natural-language claim text.
        agent_id: Which agent made this claim.
        turn: Turn number in the session.
        source_ids: List of citation IDs supporting this claim.
    """

    id: str
    content: str
    agent_id: str = ""
    turn: int = 0
    source_ids: List[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# CitationTracker
# ─────────────────────────────────────────────────────────────────────────────


class CitationTracker:
    """Tracks citations and binds them to claims for research traceability.

    Usage::

        tracker = CitationTracker()
        tracker.track(url="https://...", title="Title", snippet="...", agent_id="executor")
        claim_id = tracker.bind_claim(["source_1"], "The earth is round")
        report = tracker.format_report("The earth is round[source_1]", citations)
    """

    def __init__(self) -> None:
        self._citations: Dict[str, Citation] = {}
        self._claims: Dict[str, Claim] = {}
        self._counter: int = 0

    # ── Internal helpers ────────────────────────────────────────────────────────

    def _next_label(self) -> str:
        self._counter += 1
        return f"source_{self._counter}"

    def _ensure_citation(self, citation_id: str) -> Optional[Citation]:
        return self._citations.get(citation_id)

    # ── Public API ────────────────────────────────────────────────────────────

    def track(
        self,
        url: str,
        title: str,
        snippet: str = "",
        agent_id: str = "",
    ) -> Tuple[str, Citation]:
        """Register a new source and return its (citation_id, Citation).

        Args:
            url: Source URL.
            title: Display title.
            snippet: Relevant excerpt (used for context in report).
            agent_id: Which agent retrieved this source.

        Returns:
            (citation_id, Citation) tuple.
            citation_id is the string to embed as [citation_id] in text.
        """
        citation = Citation(
            id="",  # filled below
            url=url,
            title=title,
            snippet=snippet,
            accessed_at=datetime.now(timezone.utc).isoformat(),
            agent_id=agent_id,
        )
        label = self._next_label()
        citation.id = label
        self._citations[label] = citation
        return label, citation

    def bind_claim(
        self,
        source_ids: List[str],
        claim_content: str,
        agent_id: str = "",
        turn: int = 0,
    ) -> str:
        """Bind one or more citations to a claim.

        Args:
            source_ids: List of citation IDs (e.g. ["source_1", "source_2"]).
            claim_content: Natural-language claim text.
            agent_id: Which agent made this claim.
            turn: Turn number in the session.

        Returns:
            claim_id (UUID-style string).
        """
        # Filter out non-existent citation IDs
        valid_sources = [sid for sid in source_ids if sid in self._citations]

        claim_id = str(uuid.uuid4())[:8]
        claim = Claim(
            id=claim_id,
            content=claim_content,
            agent_id=agent_id,
            turn=turn,
            source_ids=valid_sources,
        )
        self._claims[claim_id] = claim
        return claim_id

    def get_citation(self, citation_id: str) -> Optional[Citation]:
        """Get a single citation by ID."""
        return self._citations.get(citation_id)

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        """Get a single claim by ID."""
        return self._claims.get(claim_id)

    def get_citation_graph(self) -> Dict[str, Any]:
        """Return the full citation graph as a dict.

        Returns:
            {
                "citations": [list of Citation dicts],
                "claims": [list of Claim dicts],
                "edges": [{"claim_id": ..., "source_ids": [...]}],
            }
        """
        edges = []
        for claim in self._claims.values():
            if claim.source_ids:
                edges.append(
                    {
                        "claim_id": claim.id,
                        "claim_text": claim.content,
                        "source_ids": claim.source_ids,
                    }
                )

        return {
            "citations": [self._citation_to_dict(c) for c in self._citations.values()],
            "claims": [self._claim_to_dict(c) for c in self._claims.values()],
            "edges": edges,
        }

    def format_report(
        self,
        text: str,
        *,
        inline: bool = True,
        footnotes: bool = True,
    ) -> str:
        """Format text by injecting citation markers and optionally footnotes.

        Args:
            text: Raw report text that may contain [source_N] markers.
            inline: If True, keep [source_N] markers in place.
                   If False, replace them with superscript-style numbers.
            footnotes: If True, append a numbered references section at the end.

        Returns:
            Formatted text with citation markup.
        """
        # Collect all [source_N] labels mentioned in text
        mentioned = re.findall(r"\[(source_\d+)\]", text)
        cited: Dict[str, int] = {}
        for label in dict.fromkeys(mentioned):  # dedup preserve order
            if label in self._citations:
                cited[label] = len(cited) + 1

        if not cited:
            return text

        # Build formatted label (inline style)
        def replace_label(match: re.Match) -> str:
            label = match.group(1)
            if label not in cited:
                return match.group(0)
            n = cited[label]
            return f"[{n}]" if inline else f"[{n}]"

        formatted = re.sub(r"\[(source_\d+)\]", replace_label, text)

        if footnotes:
            formatted = self._append_footnotes(formatted, cited)

        return formatted

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _citation_to_dict(c: Citation) -> Dict[str, Any]:
        return {
            "id": c.id,
            "url": c.url,
            "title": c.title,
            "snippet": c.snippet,
            "accessed_at": c.accessed_at,
            "agent_id": c.agent_id,
        }

    @staticmethod
    def _claim_to_dict(c: Claim) -> Dict[str, Any]:
        return {
            "id": c.id,
            "content": c.content,
            "agent_id": c.agent_id,
            "turn": c.turn,
            "source_ids": c.source_ids,
        }

    def _append_footnotes(
        self,
        text: str,
        cited: Dict[str, int],
    ) -> str:
        """Append a numbered references section."""
        # Sort by display number
        sorted_labels = sorted(cited.items(), key=lambda x: x[1])

        lines = ["\n\n##参考文献\n"]
        for label, number in sorted_labels:
            citation = self._citations.get(label)
            if citation is None:
                continue
            lines.append(f"[{number}] {citation.title} — {citation.url}")

        return text + "\n".join(lines)