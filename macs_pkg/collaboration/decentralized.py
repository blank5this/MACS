"""Decentralized collaboration mode (peer-to-peer协商)."""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
import asyncio

from ..core.agent import BaseAgent, AgentRole, Message
from .base import CollaborationMode, CollaborationConfig

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("decentralized")


@dataclass
class Vote:
    """Represents a vote from an agent."""
    agent_id: str
    value: Any
    weight: float = 1.0
    reasoning: str = ""  # Why the agent voted this way


@dataclass
class Proposal:
    """Represents a proposal for consensus."""
    id: str
    proposer: str
    value: Any
    votes: List[Vote] = field(default_factory=list)
    accepted: bool = False
    score: float = 0.0  # Weighted score based on votes


@dataclass
class NegotiationState:
    """State for ongoing negotiation."""
    proposals: List[Proposal]
    round: int
    completed: bool
    result: Optional[Any] = None


class DecentralizedMode(CollaborationMode):
    """Decentralized (peer-to-peer) collaboration mode.

    In this mode:
    1. All agents are peers with equal standing
    2. Agents communicate directly with each other
    3. Decisions are made through voting or consensus
    4. No single leader controls the process

    Flow:
    User Input → [Agent₁] ↔ [Agent₂] ↔ [Agent₃] (peer-to-peer)
                           ↓         ↓         ↓
                        [投票/共识机制]
                           ↓
                       Final Output
    """

    name = "decentralized"
    description = "Peer-to-peer negotiation with voting/consensus"

    def __init__(
        self,
        config: Optional[CollaborationConfig] = None,
        consensus_threshold: float = 0.5,
        max_rounds: int = 5,
    ):
        super().__init__(config)
        self.consensus_threshold = consensus_threshold
        self.max_rounds = max_rounds
        self._peers: List[BaseAgent] = []
        self._proposals: List[Proposal] = []
        self._current_round = 0

    def select_agents(
        self,
        task: Any,
        available_agents: List[BaseAgent],
    ) -> List[BaseAgent]:
        """Select agents for decentralized collaboration.

        All agents become peers with equal standing.
        """
        self._peers = list(available_agents)
        return self._peers

    async def execute(
        self,
        task: Any,
        agents: Dict[str, BaseAgent],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute decentralized collaboration.

        Args:
            task: The task to execute.
            agents: Dictionary of agents by name.
            context: Optional shared context.

        Returns:
            Consensus result or majority vote.
        """
        context = context or {}
        self._proposals = []
        self._current_round = 0

        # Ensure agents are selected as peers
        if not self._peers:
            self.select_agents(task, list(agents.values()))

        # Phase 1: Each agent proposes a solution
        initial_proposals = await self._collect_proposals(task, agents)

        if not initial_proposals:
            return None

        # Phase 2: Voting/consensus rounds
        result = await self._negotiate(initial_proposals, context)

        return result

    async def _collect_proposals(
        self,
        task: Any,
        agents: Dict[str, BaseAgent],
    ) -> List[Proposal]:
        """Collect initial proposals from all agents."""
        proposals = []
        logger.info(f"Collecting proposals from {len(agents)} agents")

        # Create tasks for all agents to propose
        async def get_proposal(agent: BaseAgent) -> Optional[Proposal]:
            msg = Message(
                sender="system",
                receiver=agent.name,
                content={
                    "action": "propose",
                    "task": task,
                },
                msg_type="propose",
                metadata={"phase": "proposal"},
            )
            try:
                response = await agent.think(msg)
                content = response.content if isinstance(response.content, dict) else {}
                proposal_value = content.get("proposal", content)
                logger.debug(f"{agent.name} proposed: {str(proposal_value)[:80]}...")
                return Proposal(
                    id=f"proposal_{agent.name}_{self._current_round}",
                    proposer=agent.name,
                    value={"action": "propose", "proposal": proposal_value, "proposer": agent.name},
                )
            except Exception as e:
                logger.error(f"{agent.name} failed to propose: {e}")
                return None

        results = await asyncio.gather(
            *[get_proposal(agent) for agent in agents.values()],
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Proposal):
                proposals.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Proposal collection exception: {result}")
                if self.config.stop_on_error:
                    raise result

        logger.info(f"Collected {len(proposals)} proposals")
        return proposals

    async def _negotiate(
        self,
        proposals: List[Proposal],
        context: Dict[str, Any],
    ) -> Any:
        """Run negotiation rounds until consensus or max rounds.

        Returns:
            Consensus result or best available after max rounds.
        """
        self._current_round = 0
        current_proposals = proposals

        # Track negotiation history
        history = []

        while self._current_round < self.max_rounds:
            self._current_round += 1

            # Run voting round
            vote_results = await self._run_voting_round(current_proposals, context)

            # Record round results
            round_info = {
                "round": self._current_round,
                "proposals": [
                    {
                        "id": p.id,
                        "proposer": p.proposer,
                        "score": p.score,
                        "votes_for": sum(1 for v in p.votes if v.value == "approve"),
                        "votes_against": sum(1 for v in p.votes if v.value == "reject"),
                        "accepted": p.accepted,
                    }
                    for p in vote_results
                ],
            }
            history.append(round_info)

            # Check for consensus (this may modify proposal.accepted)
            consensus = self._check_consensus(vote_results)
            if consensus is not None:
                # Record history AFTER consensus check so accepted flag is correct
                round_info = {
                    "round": self._current_round,
                    "proposals": [
                        {
                            "id": p.id,
                            "proposer": p.proposer,
                            "score": p.score,
                            "votes_for": sum(1 for v in p.votes if v.value == "approve"),
                            "votes_against": sum(1 for v in p.votes if v.value == "reject"),
                            "accepted": p.accepted,
                        }
                        for p in vote_results
                    ],
                }
                history.append(round_info)
                return {
                    "result": consensus,
                    "consensus": True,
                    "rounds": self._current_round,
                    "history": history,
                }

            # Select top proposals for next round
            current_proposals = self._select_top_proposals(vote_results)

            if len(current_proposals) <= 1:
                break

        # Return best result after max rounds
        if current_proposals:
            best = current_proposals[0]
            return {
                "result": best.value,
                "consensus": False,
                "rounds": self._current_round,
                "history": history,
                "best_proposal": best.id,
            }

        return {
            "result": None,
            "consensus": False,
            "rounds": self._current_round,
            "history": history,
        }

    async def _run_voting_round(
        self,
        proposals: List[Proposal],
        context: Dict[str, Any],
    ) -> List[Proposal]:
        """Run a single voting round where each agent votes on all proposals."""
        logger.info(f"Voting round {self._current_round} starting with {len(proposals)} proposals")

        # Collect all votes from all agents for all proposals
        all_votes: Dict[str, List[Vote]] = {p.id: [] for p in proposals}

        async def get_votes_from_agent(agent: BaseAgent) -> Dict[str, Optional[Vote]]:
            """Get this agent's votes on all proposals."""
            votes = {}
            for proposal in proposals:
                if agent.name == proposal.proposer:
                    votes[proposal.id] = None  # Don't vote on own proposal
                    continue
                msg = Message(
                    sender="system",
                    receiver=agent.name,
                    content={
                        "action": "vote",
                        "proposal": proposal.value,
                        "proposal_id": proposal.id,
                    },
                    msg_type="vote",
                    metadata={"round": self._current_round},
                )
                try:
                    response = await agent.think(msg)
                    # response is a Message, response.content is the dict
                    content = response.content if isinstance(response.content, dict) else {}
                    vote_value = content.get("vote", "approve")
                    if vote_value not in ("approve", "reject"):
                        logger.warning(f"{agent.name} returned unexpected vote: {vote_value}")
                        vote_value = "approve"
                    votes[proposal.id] = Vote(
                        agent_id=agent.name,
                        value=vote_value,
                        weight=1.0,
                    )
                    logger.debug(f"{agent.name} voted '{vote_value}' on proposal {proposal.id}")
                except Exception as e:
                    logger.error(f"{agent.name} failed to vote: {e}")
                    votes[proposal.id] = None
            return votes

        # Get votes from all agents in parallel
        vote_results = await asyncio.gather(
            *[get_votes_from_agent(agent) for agent in self._peers],
            return_exceptions=True,
        )

        # Aggregate votes by proposal
        for agent_votes in vote_results:
            if isinstance(agent_votes, dict):
                for proposal_id, vote in agent_votes.items():
                    if vote is not None and proposal_id in all_votes:
                        all_votes[proposal_id].append(vote)

        # Assign votes to proposals
        for proposal in proposals:
            proposal.votes = all_votes.get(proposal.id, [])

        return proposals

    def _check_consensus(self, proposals: List[Proposal]) -> Optional[Any]:
        """Check if any proposal has reached consensus.

        Consensus requires:
        1. All eligible voters approved (strong consensus)
        OR
        2. Majority approved (threshold consensus)
        """
        eligible_voters = len(self._peers) - 1
        logger.debug(f"Checking consensus: eligible_voters={eligible_voters}, threshold={self.consensus_threshold}")

        for proposal in proposals:
            if eligible_voters <= 0:
                continue

            votes = proposal.votes
            if not votes:
                logger.debug(f"Proposal {proposal.id} has no votes")
                continue

            approve_count = sum(1 for v in votes if v.value == "approve")
            reject_count = sum(1 for v in votes if v.value == "reject")

            # Calculate weighted score
            weighted_approve = sum(v.weight for v in votes if v.value == "approve")
            weighted_reject = sum(v.weight for v in votes if v.value == "reject")
            proposal.score = weighted_approve - weighted_reject

            logger.debug(f"Proposal {proposal.id} by {proposal.proposer}: "
                  f"approve={approve_count}/{len(votes)}, reject={reject_count}, score={proposal.score}")

            # Strong consensus: ALL eligible voters who voted approved
            if len(votes) >= eligible_voters:
                if approve_count == len(votes) and approve_count >= eligible_voters * self.consensus_threshold:
                    logger.info(f"Strong consensus reached for {proposal.id}")
                    proposal.accepted = True
                    return proposal.value

            # Threshold consensus: majority of eligible voters approved, no rejections
            if approve_count >= eligible_voters * self.consensus_threshold:
                if reject_count == 0:
                    logger.info(f"Threshold consensus reached for {proposal.id}")
                    proposal.accepted = True
                    return proposal.value

        # If no strong consensus, check for best proposal among all
        if proposals:
            best = max(proposals, key=lambda p: p.score)
            if best.score > 0 and len(best.votes) >= 2:
                return best.value

        return None

    def _select_top_proposals(
        self,
        proposals: List[Proposal],
        top_n: int = 2,
    ) -> List[Proposal]:
        """Select top N proposals by vote count for next round."""
        sorted_proposals = sorted(
            proposals,
            key=lambda p: sum(1 for v in p.votes if v.value == "approve"),
            reverse=True,
        )
        return sorted_proposals[:top_n]

    def get_required_roles(self) -> List[AgentRole]:
        """All roles can participate in decentralized mode."""
        return [AgentRole.PLANNER, AgentRole.EXECUTOR, AgentRole.REVIEWER]
