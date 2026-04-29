"""Result aggregation for multi-agent collaboration."""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from .agent import Message


class AggregationStrategy(Enum):
    """Strategy for aggregating results."""

    FIRST_COMPLETE = "first_complete"  # Return first result that completes
    ALL_COMPLETE = "all_complete"  # Wait for all, return as list
    MAJORITY = "majority"  # Return majority vote
    CONSENSUS = "consensus"  # Require consensus
    WEIGHTED = "weighted"  # Weighted aggregation based on agent trust


@dataclass
class AggregatedResult:
    """Container for aggregated results."""

    id: str
    task_id: str
    strategy: str
    results: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class ResultAggregator:
    """Aggregates results from multiple agents.

    The aggregator handles:
    - Collecting results from subtasks
    - Applying aggregation strategies
    - Managing timeouts
    - Error handling
    """

    def __init__(
        self,
        strategy: AggregationStrategy = AggregationStrategy.ALL_COMPLETE,
        timeout: Optional[float] = None,
    ):
        self.strategy = strategy
        self.timeout = timeout
        self._pending_tasks: Dict[str, Dict[str, Any]] = {}
        self._completed_results: Dict[str, AggregatedResult] = {}

    def start_aggregation(self, task_id: str) -> str:
        """Start a new aggregation task.

        Args:
            task_id: The parent task ID.

        Returns:
            Aggregation ID.
        """
        agg_id = str(uuid.uuid4())
        self._pending_tasks[agg_id] = {
            "task_id": task_id,
            "subtask_results": {},
            "started_at": datetime.now(),
            "subtasks_expected": 0,
            "subtasks_received": 0,
        }
        return agg_id

    def set_expected_subtasks(self, agg_id: str, count: int) -> None:
        """Set the expected number of subtask results.

        Args:
            agg_id: Aggregation ID.
            count: Expected number of subtask results.
        """
        if agg_id in self._pending_tasks:
            self._pending_tasks[agg_id]["subtasks_expected"] = count

    def add_result(self, agg_id: str, agent_id: str, result: Any) -> None:
        """Add a result from a subtask.

        Args:
            agg_id: Aggregation ID.
            agent_id: ID of the agent that produced the result.
            result: The result content.
        """
        if agg_id not in self._pending_tasks:
            return

        task_info = self._pending_tasks[agg_id]
        task_info["subtask_results"][agent_id] = {
            "result": result,
            "received_at": datetime.now(),
        }
        task_info["subtasks_received"] += 1

    def is_complete(self, agg_id: str) -> bool:
        """Check if aggregation is complete.

        Args:
            agg_id: Aggregation ID.

        Returns:
            True if aggregation is complete.
        """
        if agg_id not in self._pending_tasks:
            return False

        task_info = self._pending_tasks[agg_id]
        expected = task_info["subtasks_expected"]

        if expected == 0:
            return False

        if self.strategy == AggregationStrategy.FIRST_COMPLETE:
            return task_info["subtasks_received"] >= 1
        else:
            return task_info["subtasks_received"] >= expected

    def get_result(self, agg_id: str) -> Optional[AggregatedResult]:
        """Get the aggregated result.

        Args:
            agg_id: Aggregation ID.

        Returns:
            Aggregated result or None if not complete.
        """
        if not self.is_complete(agg_id):
            return None

        task_info = self._pending_tasks[agg_id]
        agg_result = AggregatedResult(
            id=agg_id,
            task_id=task_info["task_id"],
            strategy=self.strategy.value,
            results=self._aggregate_results(task_info["subtask_results"]),
            completed_at=datetime.now(),
        )

        self._completed_results[agg_id] = agg_result
        del self._pending_tasks[agg_id]
        return agg_result

    def _aggregate_results(
        self, subtask_results: Dict[str, Dict[str, Any]]
    ) -> List[Any]:
        """Apply aggregation strategy to results."""
        results = [info["result"] for info in subtask_results.values()]

        if self.strategy == AggregationStrategy.ALL_COMPLETE:
            return results
        elif self.strategy == AggregationStrategy.FIRST_COMPLETE:
            return results[:1] if results else []
        elif self.strategy == AggregationStrategy.MAJORITY:
            return self._majority_vote(results)
        elif self.strategy == AggregationStrategy.CONSENSUS:
            return self._find_consensus(results)
        elif self.strategy == AggregationStrategy.WEIGHTED:
            return self._weighted_aggregate(results, subtask_results)
        else:
            return results

    def _majority_vote(self, results: List[Any]) -> List[Any]:
        """Return majority vote result."""
        if not results:
            return []
        # Simple majority - most common result
        from collections import Counter
        counter = Counter(str(r) for r in results)
        majority = counter.most_common(1)[0][0]
        return [r for r in results if str(r) == majority]

    def _find_consensus(self, results: List[Any]) -> List[Any]:
        """Find consensus among results."""
        if not results:
            return []
        # For consensus, all results must be identical
        unique_results = set(str(r) for r in results)
        if len(unique_results) == 1:
            return results
        return []  # No consensus

    def _weighted_aggregate(
        self, results: List[Any], subtask_results: Dict[str, Dict[str, Any]]
    ) -> List[Any]:
        """Apply weighted aggregation."""
        # Default implementation returns all results
        # Subclasses or custom aggregators can implement proper weighting
        return results

    def cancel_aggregation(self, agg_id: str) -> bool:
        """Cancel a pending aggregation.

        Args:
            agg_id: Aggregation ID.

        Returns:
            True if aggregation was cancelled, False if not found.
        """
        if agg_id in self._pending_tasks:
            del self._pending_tasks[agg_id]
            return True
        return False

    def get_pending_info(self, agg_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a pending aggregation.

        Args:
            agg_id: Aggregation ID.

        Returns:
            Dictionary with pending task info or None.
        """
        return self._pending_tasks.get(agg_id)


class HierarchicalAggregator(ResultAggregator):
    """Aggregator for hierarchical (tree) result structures.

    Used when subtasks themselves have nested subtasks.
    """

    def __init__(self, timeout: Optional[float] = None):
        super().__init__(AggregationStrategy.ALL_COMPLETE, timeout)
        self._tree_results: Dict[str, Any] = {}

    def add_result_at_path(
        self, agg_id: str, path: List[str], agent_id: str, result: Any
    ) -> None:
        """Add a result at a specific path in the tree.

        Args:
            agg_id: Aggregation ID.
            path: Path of indices to the result location.
            agent_id: ID of the producing agent.
            result: The result content.
        """
        if agg_id not in self._tree_results:
            self._tree_results[agg_id] = {}

        current = self._tree_results[agg_id]
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[path[-1]] = {"agent_id": agent_id, "result": result}
        self.add_result(agg_id, agent_id, result)

    def get_tree_result(self, agg_id: str) -> Optional[Dict[str, Any]]:
        """Get the complete tree result.

        Args:
            agg_id: Aggregation ID.

        Returns:
            Tree structure or None if not complete.
        """
        if self.is_complete(agg_id):
            return self._tree_results.get(agg_id)
        return None
