"""Reviewer Agent - reviews and validates results with LLM integration."""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import asyncio

from ..core.agent import BaseAgent, AgentRole, Message, AgentState
from ..core.citation import CitationTracker
from ..core.react_agent import ReactAgent
from ..core.utils import extract_json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("reviewer")

if TYPE_CHECKING:
    from ..llm.base import LLMProvider

# Default system prompt for reviewer
DEFAULT_SYSTEM_PROMPT = """You are a Reviewer Agent specialized in quality assurance and validation.

Your responsibilities:
1. Review results against requirements and acceptance criteria
2. Validate completeness, correctness, and relevance
3. Provide constructive feedback for improvements
4. Approve or reject results based on quality threshold
5. Aggregate feedback from multiple reviews

When reviewing:
- Check against original requirements and acceptance criteria
- Be fair but strict - quality matters
- Provide specific, actionable feedback
- Suggest improvements when rejecting

Respond in JSON format for machine-readable reviews."""


class ReviewerAgent(ReactAgent):
    """Reviewer Agent for validating and quality-checking results.

    Responsibilities:
    - Review results from executors
    - Validate against requirements
    - Provide feedback for improvements
    - Approve or reject results
    - Aggregate multiple results

    Inherits from :class:`ReactAgent` — call ``think()`` before ``act()``,
    or use ``run()`` for the combined cycle.
    """

    def __init__(
        self,
        name: str = "reviewer",
        model: str = "gpt-4",
        system_prompt: Optional[str] = None,
        provider: Optional["LLMProvider"] = None,
        quality_threshold: float = 0.7,
        enable_llm: bool = True,
        citation_tracker: Optional[CitationTracker] = None,
    ):
        super().__init__(
            name=name,
            role=AgentRole.REVIEWER,
            model=model,
            system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
        )
        self._provider = provider
        self._enable_llm = enable_llm and provider is not None
        self.quality_threshold = quality_threshold
        self._reviews: Dict[str, Dict[str, Any]] = {}
        self._criteria: List[str] = [
            "completeness",
            "correctness",
            "relevance",
        ]
        self._citation_tracker = citation_tracker or CitationTracker()

    def set_provider(self, provider: "LLMProvider") -> None:
        """Set the LLM provider for this agent.

        Args:
            provider: LLM provider instance.
        """
        self._provider = provider
        self._enable_llm = True

    def set_criteria(self, criteria: List[str]) -> None:
        """Set review criteria.

        Args:
            criteria: List of criteria names.
        """
        self._criteria = criteria

    async def _think_impl(self, message: Message) -> Message:
        """Process review request and prepare review.

        Args:
            message: Incoming message with results to review.

        Returns:
            Response with review plan.
        """
        content = message.content

        action = content.get("action", "review") if isinstance(content, dict) else "review"

        if action == "review":
            results = content.get("results", [])
            review_plan = self._create_review_plan(results)

            response_content = {
                "action": "review_ready",
                "results_to_review": results,
                "review_plan": review_plan,
                "criteria": self._criteria,
            }
        elif action == "aggregate":
            response_content = await self._prepare_aggregation(content)
        elif action == "propose":
            # Generate review proposal for decentralized mode
            task = content.get("task", content)
            proposal = self._generate_review_proposal(task)
            response_content = {
                "action": "propose",
                "proposal": proposal,
                "proposer": self.name,
            }
        elif action == "vote":
            # Vote on a proposal
            vote_result = self._vote_on_proposal(content.get("proposal"))
            response_content = {
                "action": "vote",
                "vote": vote_result,
                "voter": self.name,
            }
        else:
            response_content = {
                "action": "unknown",
                "error": f"Unknown action: {action}",
            }

        return Message(
            sender=self.name,
            receiver=message.sender,
            content=response_content,
            msg_type="review",
            metadata={
                "original_id": message.id,
                "role": self.role.value,
            },
        )

    async def _act_impl(self, response: Message) -> List[Message]:
        """Execute review and send results.

        Args:
            response: The response from think phase.

        Returns:
            List of messages (review results).
        """
        outgoing = []

        content = response.content
        if content.get("action") == "review_ready":
            results = content.get("results_to_review", [])
            review_plan = content.get("review_plan", [])

            # Execute review
            if self._enable_llm and self._provider is not None:
                review_results = await self._review_results_with_llm(results)
            else:
                review_results = []
                for result_item in results:
                    review = await self._review_result_simple(result_item, review_plan)
                    review_results.append(review)

            # Aggregate review
            aggregated = self._aggregate_reviews(review_results)

            # Determine approval status
            approved = aggregated.get("overall_score", 0) >= self.quality_threshold

            # Store review
            review_id = f"review_{response.id}"
            self._reviews[review_id] = {
                "results": review_results,
                "aggregated": aggregated,
                "approved": approved,
            }

            # Create response message
            result_msg = Message(
                sender=self.name,
                receiver=response.sender,
                content={
                    "action": "review_complete",
                    "review_id": review_id,
                    "results": review_results,
                    "aggregated": aggregated,
                    "approved": approved,
                    "feedback": aggregated.get("feedback", []) if not approved else None,
                },
                msg_type="result",
                metadata={
                    "parent_id": response.metadata.get("original_id"),
                },
            )
            outgoing.append(result_msg)

            # Remember this review
            if self.has_long_term_memory():
                await self.remember(
                    content=f"Review {'approved' if approved else 'rejected'} - Score: {aggregated.get('overall_score', 0):.2f}",
                    memory_type="result",
                    metadata={
                        "review_id": review_id,
                        "approved": approved,
                        "score": aggregated.get("overall_score", 0),
                    },
                )

        self.add_to_memory(response)
        return outgoing

    def _create_review_plan(self, results: List[Any]) -> List[Dict[str, Any]]:
        """Create a review plan for the results.

        Args:
            results: Results to review.

        Returns:
            List of review steps.
        """
        plan = []

        for criterion in self._criteria:
            plan.append({
                "criterion": criterion,
                "check": f"validate_{criterion}",
            })

        # Add aggregation step
        plan.append({
            "criterion": "overall",
            "check": "aggregate_scores",
        })

        return plan

    async def _review_results_with_llm(self, results: List[Any]) -> List[Dict[str, Any]]:
        """Use LLM to review all results.

        Args:
            results: Results to review.

        Returns:
            List of review results with scores and feedback.
        """
        from ..llm.base import LLMMessage
        import json

        results_text = json.dumps(results, indent=2, default=str)

        prompt = f"""Review the following execution results against the criteria:
Criteria: {", ".join(self._criteria)}

Results to review:
{results_text}

For each result, evaluate:
1. Completeness - Is everything required present?
2. Correctness - Is the output correct and error-free?
3. Relevance - Does it address the original task?

Respond with a JSON array of reviews:
[
  {{
    "result": "the result being reviewed",
    "scores": {{
      "completeness": 0.0-1.0,
      "correctness": 0.0-1.0,
      "relevance": 0.0-1.0
    }},
    "feedback": ["specific feedback point 1", "specific feedback point 2"],
    "issues": ["issue 1 if any", "issue 2 if any"] (empty array if no issues)
  }}
]

Only respond with JSON."""

        try:
            response = await self._provider.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system=self.system_prompt,
                max_tokens=2048,
                temperature=0.3,
            )

            reviews = extract_json(response.content)
            if isinstance(reviews, list):
                return reviews

            logger.warning("LLM review did not return a list, using simple fallback")

        except Exception as e:
            logger.warning(f"LLM review failed: {e}, using simple fallback")

        # Fallback to simple reviews
        review_plan = self._create_review_plan(results)
        fallback_reviews = []
        for result_item in results:
            review = await self._review_result_simple(result_item, review_plan)
            fallback_reviews.append(review)
        return fallback_reviews

    async def _review_result_simple(
        self,
        result: Any,
        review_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Simple fallback review without LLM.

        Args:
            result: Result to review.
            review_plan: Plan of what to check.

        Returns:
            Review scores and feedback.
        """
        scores = {}
        feedback = {}

        for step in review_plan:
            criterion = step.get("criterion")

            if criterion == "completeness":
                scores["completeness"] = self._score_completeness(result)
                feedback["completeness"] = "Complete" if scores["completeness"] >= 0.7 else "Incomplete"

            elif criterion == "correctness":
                scores["correctness"] = self._score_correctness(result)
                feedback["correctness"] = "Correct" if scores["correctness"] >= 0.7 else "May have issues"

            elif criterion == "relevance":
                scores["relevance"] = self._score_relevance(result)
                feedback["relevance"] = "Relevant" if scores["relevance"] >= 0.7 else "Not relevant"

        return {
            "result": result,
            "scores": scores,
            "feedback": list(feedback.values()),
            "issues": [] if all(s >= 0.7 for s in scores.values()) else ["Needs improvement"],
        }

    async def _review_result(
        self,
        result: Any,
        review_plan: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Review a single result.

        Args:
            result: Result to review.
            review_plan: Plan of what to check.

        Returns:
            Review scores and feedback.
        """
        if self._enable_llm and self._provider is not None:
            # Use LLM for review
            return await self._review_result_with_llm(result)
        return await self._review_result_simple(result, review_plan)

    async def _review_result_with_llm(self, result: Any) -> Dict[str, Any]:
        """Use LLM to review a single result.

        Args:
            result: Result to review.

        Returns:
            Review scores and feedback.
        """
        from ..llm.base import LLMMessage
        import json

        prompt = f"""Review this result:
{json.dumps(result, indent=2, default=str)}

Evaluate:
1. Completeness: Is everything required present? (0.0-1.0)
2. Correctness: Is the output correct? (0.0-1.0)
3. Relevance: Does it address the task? (0.0-1.0)

Respond with JSON:
{{
  "scores": {{"completeness": X, "correctness": Y, "relevance": Z}},
  "feedback": ["feedback point 1", "feedback point 2"],
  "issues": ["issue if any"]
}}

Only respond with JSON."""

        try:
            response = await self._provider.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system=self.system_prompt,
                max_tokens=1024,
                temperature=0.3,
            )
            parsed = extract_json(response.content)
            if isinstance(parsed, dict):
                return parsed
        except Exception as e:
            logger.warning(f"LLM single-result review failed: {e}, using simple fallback")

        return await self._review_result_simple(result, self._create_review_plan([result]))

    def _score_completeness(self, result: Any) -> float:
        """Score completeness of a result."""
        if isinstance(result, dict):
            required_keys = ["subtask_id", "final_output"]
            present = sum(1 for k in required_keys if k in result)
            return present / len(required_keys)
        return 0.8 if result else 0.0

    def _score_correctness(self, result: Any) -> float:
        """Score correctness of a result."""
        if isinstance(result, dict):
            if "error" in result:
                return 0.0
            if "final_output" in result:
                return 0.9
        return 0.7

    def _score_relevance(self, result: Any) -> float:
        """Score relevance of a result."""
        if isinstance(result, dict):
            output = str(result.get("final_output", ""))
            if output and not output.startswith("Error"):
                return 0.85
        return 0.5

    def _aggregate_reviews(self, reviews: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate multiple review results.

        Args:
            reviews: List of individual reviews.

        Returns:
            Aggregated review results.
        """
        if not reviews:
            return {"overall_score": 0, "feedback": []}

        # Calculate average scores per criterion
        all_scores = {}
        for review in reviews:
            for criterion, score in review.get("scores", {}).items():
                if criterion not in all_scores:
                    all_scores[criterion] = []
                all_scores[criterion].append(score)

        avg_scores = {
            criterion: sum(scores) / len(scores)
            for criterion, scores in all_scores.items()
        }

        # Calculate overall score
        overall_score = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0

        # Collect feedback
        all_feedback = []
        for review in reviews:
            all_feedback.extend(review.get("feedback", []))

        return {
            "criterion_scores": avg_scores,
            "overall_score": overall_score,
            "feedback": list(set(all_feedback)),
        }

    async def _prepare_aggregation(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare for result aggregation."""
        results = content.get("results", [])
        return {
            "action": "aggregation_ready",
            "results": results,
            "count": len(results),
        }

    def _generate_review_proposal(self, task: Any) -> Dict[str, Any]:
        """Generate a review proposal for decentralized collaboration.

        Args:
            task: The task to generate proposal for.

        Returns:
            A proposal dictionary.
        """
        task_desc = task.get('description', task) if isinstance(task, dict) else str(task)
        return {
            "type": "review_proposal",
            "task": task_desc,
            "approach": "Review for quality, completeness, and correctness",
            "review_criteria": ["completeness", "correctness", "relevance"],
            "estimated_duration": "Short",
            "confidence": 0.8,
        }

    def _vote_on_proposal(self, proposal: Any) -> str:
        """Vote on a proposal.

        Args:
            proposal: The proposal to vote on.

        Returns:
            "approve" or "reject".
        """
        return BaseAgent.vote_on_proposal(proposal)

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get a stored review by ID."""
        return self._reviews.get(review_id)

    def get_all_reviews(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored reviews."""
        return self._reviews.copy()

    @property
    def citation_tracker(self) -> CitationTracker:
        """Return the citation tracker instance."""
        return self._citation_tracker

    # ── Citation helpers ───────────────────────────────────────────────────────

    def track_source(
        self,
        url: str,
        title: str,
        snippet: str = "",
    ) -> str:
        """Register a source and return its citation_id (e.g. 'source_1').

        Args:
            url: Source URL.
            title: Display title.
            snippet: Relevant excerpt.

        Returns:
            citation_id string to embed as [citation_id] in text.
        """
        label, _ = self._citation_tracker.track(
            url=url,
            title=title,
            snippet=snippet,
            agent_id=self.name,
        )
        return label

    def bind_claim(
        self,
        claim_content: str,
        source_ids: List[str],
        turn: int = 0,
    ) -> str:
        """Bind one or more citations to a claim.

        Args:
            claim_content: Natural-language claim text.
            source_ids: List of citation IDs from track_source().
            turn: Session turn number.

        Returns:
            claim_id string.
        """
        return self._citation_tracker.bind_claim(
            source_ids=source_ids,
            claim_content=claim_content,
            agent_id=self.name,
            turn=turn,
        )

    def get_citation_graph(self) -> Dict[str, Any]:
        """Return the full citation graph."""
        return self._citation_tracker.get_citation_graph()

    # ── Synthesis ─────────────────────────────────────────────────────────────

    async def synthesize(
        self,
        sections: List[Dict[str, Any]],
        *,
        format: str = "markdown",
        inject_citations: bool = True,
    ) -> Dict[str, Any]:
        """Synthesize a structured report from sections, binding citations.

        Args:
            sections: List of sections, each a dict with keys:
                - title (str): Section heading.
                - content (str): Section body. May contain [source_N] markers.
                - evidence (List[Dict], optional): List of {"url", "title", "snippet"}.
                - claims (List[str], optional): Claim texts to bind to evidence.
            format: Output format ("markdown" | "html").
            inject_citations: If True, call format_report() to format citation markers.

        Returns:
            Dict with keys:
                - report (str): Formatted report body.
                - citation_graph (dict): Full citation graph from get_citation_graph().
                - citations (list): List of all Citation dicts.
                - claim_count (int): Number of bound claims.
        """
        if self._enable_llm and self._provider is not None:
            return await self._synthesize_with_llm(sections, format=format, inject_citations=inject_citations)
        return self._synthesize_simple(sections, format=format, inject_citations=inject_citations)

    async def _synthesize_with_llm(
        self,
        sections: List[Dict[str, Any]],
        format: str,
        inject_citations: bool,
    ) -> Dict[str, Any]:
        """LLM-powered synthesis with citation binding."""
        from ..llm.base import LLMMessage
        import json

        # First pass: register all evidence sources
        for section in sections:
            for ev in section.get("evidence", []):
                self.track_source(
                    url=ev.get("url", ""),
                    title=ev.get("title", ""),
                    snippet=ev.get("snippet", ""),
                )

        # Second pass: bind claims
        for section in sections:
            for claim in section.get("claims", []):
                self.bind_claim(
                    claim_content=claim,
                    source_ids=list(self._citation_tracker._citations.keys()),
                    turn=0,
                )

        # Build synthesis prompt
        sections_json = json.dumps(sections, indent=2, default=str)
        prompt = f"""You are a research report synthesizer.

Given the following sections with evidence, produce a cohesive, well-structured report.

Sections:
{sections_json}

Requirements:
1. Integrate [source_N] markers where claims are made (e.g. "The sky is blue[source_1][source_2]").
2. Do NOT invent citation numbers — only use the markers already present in the sections.
3. Output ONLY the report content (no preamble or explanation).
4. Follow this structure: Abstract → Background → Findings → Conclusion → References.

Respond with JSON:
{{
  "report": "full report text with [source_N] markers in place",
}}

Only respond with JSON."""

        try:
            response = await self._provider.complete(
                messages=[LLMMessage(role="user", content=prompt)],
                system="You are a precise research report synthesizer. Cite all claims.",
                max_tokens=4096,
                temperature=0.3,
            )

            parsed = extract_json(response.content)
            if isinstance(parsed, dict) and "report" in parsed:
                report_body = parsed["report"]
            else:
                report_body = (response.content or "").strip()
        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}, using simple fallback")
            report_body = self._plaintext_synthesis(sections)

        if inject_citations:
            citations_list = list(self._citation_tracker._citations.values())
            report_body = self._citation_tracker.format_report(
                report_body, inline=True, footnotes=True
            )
        else:
            citations_list = list(self._citation_tracker._citations.values())

        return {
            "report": report_body,
            "citation_graph": self._citation_tracker.get_citation_graph(),
            "citations": [self._citation_tracker._citation_to_dict(c) for c in citations_list],
            "claim_count": len(self._citation_tracker._claims),
        }

    def _synthesize_simple(
        self,
        sections: List[Dict[str, Any]],
        format: str,
        inject_citations: bool,
    ) -> Dict[str, Any]:
        """Fallback synthesis without LLM — straight concatenation."""
        lines = []
        for section in sections:
            lines.append(f"## {section.get('title', '')}\n{section.get('content', '')}")

        report_body = "\n\n".join(lines)

        if inject_citations:
            report_body = self._citation_tracker.format_report(
                report_body, inline=True, footnotes=True
            )

        return {
            "report": report_body,
            "citation_graph": self._citation_tracker.get_citation_graph(),
            "citations": [
                self._citation_tracker._citation_to_dict(c)
                for c in self._citation_tracker._citations.values()
            ],
            "claim_count": len(self._citation_tracker._claims),
        }

    def _plaintext_synthesis(self, sections: List[Dict[str, Any]]) -> str:
        """Simple concatenation for fallback."""
        parts = []
        for section in sections:
            title = section.get("title", "")
            content = section.get("content", "")
            parts.append(f"## {title}\n{content}")
        return "\n\n".join(parts)
