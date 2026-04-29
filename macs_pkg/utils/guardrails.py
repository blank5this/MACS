"""Guardrails — input validation, security filtering, and resource limits.

Prevents agent from:
- Accessing blocked topics (passwords, credit cards, etc.)
- Exceeding max tool calls per task
- Exceeding max iterations
- Generating harmful content

Usage::

    from macs_pkg.utils.guardrails import AgentGuardrails, SecurityError

    guardrails = AgentGuardrails(
        blocked_topics=["password", "credit_card", "ssn"],
        max_tool_calls=10,
        max_iterations=5,
    )

    result = await guardrails.execute(agent, task)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
import re


class SecurityError(Exception):
    """Raised when guardrails detect a policy violation."""
    pass


class RateLimitError(SecurityError):
    """Raised when a rate limit is exceeded."""
    pass


class ResourceLimitError(SecurityError):
    """Raised when a resource limit (tool calls, iterations) is exceeded."""
    pass


@dataclass
class GuardrailsConfig:
    """Configuration for agent guardrails."""
    blocked_topics: List[str] = field(default_factory=list)
    max_tool_calls: int = 10
    max_iterations: int = 5
    max_token_budget: int = 8000  # Max tokens per request
    allow_destructive_actions: bool = False
    blocked_patterns: List[str] = field(default_factory=list)  # Regex patterns
    allowed_domains: List[str] = field(default_factory=list)  # For HTTP tool


class AgentGuardrails:
    """Security guardrails for agent execution.

    Provides:
    - Input topic blocking (passwords, credit cards, etc.)
    - Resource limits (max_tool_calls, max_iterations)
    - Pattern matching for sensitive data
    - Domain allowlisting for HTTP requests
    """

    # Default blocked topics for enterprise security
    DEFAULT_BLOCKED = [
        "password", "passwd", "pwd",
        "credit card", "credit_card", "ccnumber",
        "social security", "ssn", "national id",
        "bank account", "routing number",
        "secret key", "api key", "private key",
        "admin password", "root password",
    ]

    # Suspicious patterns for regex detection
    DEFAULT_PATTERNS = [
        r"\b\d{3}-\d{2}-\d{4}\b",      # SSN
        r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",  # Credit card
        r"password[\s:=]+\S+",           # password:=something
        r"api[_-]?key[\s:=]+\S+",       # api_key:=something
        r"sk-[a-zA-Z0-9]{20,}",         # OpenAI/MiniMax key pattern
    ]

    def __init__(self, config: Optional[GuardrailsConfig] = None):
        self.config = config or GuardrailsConfig()
        self._blocked_set: Set[str] = set(t.lower() for t in self.config.blocked_topics)
        self._blocked_patterns: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in self.config.blocked_patterns
        ] + [re.compile(p, re.IGNORECASE) for p in self.DEFAULT_PATTERNS]

    # ─── Input Validation ───────────────────────────────────────────────────

    def check_input(self, text: str) -> None:
        """Check input text for blocked topics or patterns.

        Args:
            text: Input text to check.

        Raises:
            SecurityError: If blocked content detected.
        """
        text_lower = text.lower()

        # Check blocked topics
        for topic in self._blocked_set:
            if topic in text_lower:
                raise SecurityError(f"Blocked topic detected: '{topic}'")

        # Check regex patterns
        for pattern in self._blocked_patterns:
            if pattern.search(text):
                raise SecurityError(f"Blocked pattern matched: '{pattern.pattern}'")

    def check_url(self, url: str) -> None:
        """Check if a URL is on an allowed domain.

        Args:
            url: URL to check.

        Raises:
            SecurityError: If domain not allowlisted.
        """
        if not self.config.allowed_domains:
            return  # No restriction

        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        allowed = False
        for allowed_domain in self.config.allowed_domains:
            if domain == allowed_domain or domain.endswith(f".{allowed_domain}"):
                allowed = True
                break

        if not allowed:
            raise SecurityError(f"URL domain not allowlisted: '{domain}'")

    # ─── Execution with Guardrails ─────────────────────────────────────────

    async def execute(self, agent: Any, task: str, **kwargs: Any) -> Any:
        """Execute an agent task with guardrails.

        Args:
            agent: The agent to execute.
            task: Task description.
            **kwargs: Additional arguments for agent execution.

        Returns:
            Execution result.

        Raises:
            SecurityError: If input or output violates policies.
            ResourceLimitError: If limits exceeded.
        """
        # Check input
        self.check_input(task)

        # Execute with resource tracking
        tool_call_count = 0
        iteration_count = 0
        result = None

        for iteration in range(self.config.max_iterations):
            iteration_count += 1

            step_result = await agent.step(task, **kwargs)

            # Count tool calls
            tool_calls = getattr(step_result, "tool_calls", []) or []
            tool_call_count += len(tool_calls)

            # Check tool call limit
            if tool_call_count > self.config.max_tool_calls:
                raise ResourceLimitError(
                    f"Max tool calls ({self.config.max_tool_calls}) exceeded. "
                    f"Task terminated after {tool_call_count} calls."
                )

            # Check if terminal
            is_terminal = getattr(step_result, "is_terminal", True)
            if is_terminal:
                result = step_result
                break

            # Provide feedback for next iteration
            if iteration < self.config.max_iterations - 1:
                feedback = getattr(step_result, "feedback", None)
                if feedback:
                    task = f"{task}\n\nPrevious attempt feedback: {feedback}"

        if result is None:
            raise ResourceLimitError(
                f"Max iterations ({self.config.max_iterations}) reached. "
                f"Task did not complete."
            )

        # Check output for sensitive data leakage
        output = getattr(result, "content", str(result))
        self.check_input(str(output))

        return result

    # ─── Simple Helpers ──────────────────────────────────────────────────────

    def is_safe(self, text: str) -> bool:
        """Quick check if text passes guardrails.

        Args:
            text: Text to check.

        Returns:
            True if safe, False if blocked.
        """
        try:
            self.check_input(text)
            return True
        except SecurityError:
            return False

    def redact_sensitive(self, text: str) -> str:
        """Redact sensitive patterns from text.

        Args:
            text: Text to redact.

        Returns:
            Text with sensitive data replaced by [REDACTED].
        """
        result = text
        for pattern in self._blocked_patterns:
            result = pattern.sub("[REDACTED]", result)
        return result
