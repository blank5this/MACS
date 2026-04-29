"""Token usage tracking and budget management for LLM providers.

Usage::

    from macs_pkg.utils.token_budget import TokenBudget, BudgetExceededError

    budget = TokenBudget(
        daily_limit=100000,
        monthly_limit=1000000,
    )

    # Track usage after each LLM call
    budget.track(model="MiniMax-M2.7", input_tokens=500, output_tokens=800)

    # Check before making a call
    budget.check_available(model="MiniMax-M2.7", estimated_tokens=1000)

    # Get current usage
    usage = budget.get_usage()
"""

from __future__ import annotations

import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict


class BudgetExceededError(Exception):
    """Raised when token budget is exceeded."""
    pass


@dataclass
class TokenBudgetConfig:
    """Configuration for token budgets."""
    daily_limit: int = 100_000
    monthly_limit: int = 1_000_000
    per_model_daily_limit: Optional[Dict[str, int]] = None
    warn_at_percent: float = 0.80  # Warn when 80% of budget used


@dataclass
class TokenUsage:
    """Token usage record."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    calls: int = 0
    date: str = ""  # YYYY-MM-DD
    month: str = ""  # YYYY-MM


class TokenBudget:
    """Track and limit token usage across LLM providers.

    Supports:
    - Daily and monthly budgets
    - Per-model budgets
    - Usage reporting and alerts
    """

    def __init__(self, config: Optional[TokenBudgetConfig] = None):
        self.config = config or TokenBudgetConfig()
        self._daily_usage: Dict[str, TokenUsage] = defaultdict(lambda: TokenUsage())
        self._monthly_usage: Dict[str, TokenUsage] = defaultdict(lambda: TokenUsage())
        self._last_warning: Dict[str, float] = {}  # model -> timestamp

    def _current_date(self) -> str:
        return time.strftime("%Y-%m-%d")

    def _current_month(self) -> str:
        return time.strftime("%Y-%m")

    # ─── Tracking ─────────────────────────────────────────────────────────────

    def track(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        calls: int = 1,
    ) -> None:
        """Record token usage from an LLM call.

        Args:
            model: Model name (e.g., "MiniMax-M2.7").
            input_tokens: Tokens in the input request.
            output_tokens: Tokens in the output response.
            calls: Number of calls (default 1).
        """
        date = self._current_date()
        month = self._current_month()
        total = input_tokens + output_tokens

        # Daily usage
        usage_day = self._daily_usage[f"{model}:{date}"]
        usage_day.input_tokens += input_tokens * calls
        usage_day.output_tokens += output_tokens * calls
        usage_day.total_tokens += total * calls
        usage_day.calls += calls
        usage_day.date = date

        # Monthly usage
        usage_month = self._monthly_usage[f"{model}:{month}"]
        usage_month.input_tokens += input_tokens * calls
        usage_month.output_tokens += output_tokens * calls
        usage_month.total_tokens += total * calls
        usage_month.calls += calls
        usage_month.month = month

    def check_available(
        self,
        model: str,
        estimated_tokens: int,
        input_tokens: Optional[int] = None,
    ) -> bool:
        """Check if budget allows the estimated token cost.

        Args:
            model: Model name.
            estimated_tokens: Estimated total tokens for the call.
            input_tokens: Optional input token count (if known).

        Returns:
            True if within budget.

        Raises:
            BudgetExceededError: If budget would be exceeded.
        """
        date = self._current_date()
        month = self._current_month()

        daily_key = f"{model}:{date}"
        monthly_key = f"{model}:{month}"

        # Get current usage
        daily_used = self._daily_usage.get(daily_key, TokenUsage()).total_tokens
        monthly_used = self._monthly_usage.get(monthly_key, TokenUsage()).total_tokens

        # Check daily limit
        per_model = (self.config.per_model_daily_limit or {}).get(model, 0)
        effective_daily = per_model if per_model > 0 else self.config.daily_limit

        if daily_used + estimated_tokens > effective_daily:
            raise BudgetExceededError(
                f"Daily budget exceeded for {model}: "
                f"{daily_used}/{effective_daily} tokens. "
                f"Estimated additional: {estimated_tokens}"
            )

        # Check monthly limit
        if monthly_used + estimated_tokens > self.config.monthly_limit:
            raise BudgetExceededError(
                f"Monthly budget exceeded for {model}: "
                f"{monthly_used}/{self.config.monthly_limit} tokens"
            )

        # Warning at threshold
        daily_pct = (daily_used + estimated_tokens) / effective_daily
        if daily_pct >= self.config.warn_at_percent:
            last_warn = self._last_warning.get(model, 0)
            now = time.time()
            if now - last_warn > 3600:  # Max 1 warning per hour
                self._last_warning[model] = now
                # Log warning (would use logger in production)

        return True

    # ─── Usage Reporting ─────────────────────────────────────────────────────

    def get_usage(self, model: Optional[str] = None) -> Dict:
        """Get current token usage.

        Args:
            model: Optional model filter. If None, returns all.

        Returns:
            Dict with daily/monthly usage by model.
        """
        date = self._current_date()
        month = self._current_month()

        if model:
            daily = self._daily_usage.get(f"{model}:{date}", TokenUsage())
            monthly = self._monthly_usage.get(f"{model}:{month}", TokenUsage())
            return {
                "model": model,
                "daily_tokens": daily.total_tokens,
                "daily_calls": daily.calls,
                "monthly_tokens": monthly.total_tokens,
                "monthly_calls": monthly.calls,
                "daily_limit": (
                    self.config.per_model_daily_limit.get(model, 0)
                    or self.config.daily_limit
                ),
                "monthly_limit": self.config.monthly_limit,
            }

        # All models
        all_models: Dict[str, Dict] = {}
        for key, usage in self._daily_usage.items():
            if ":" not in key:
                continue
            m, d = key.split(":", 1)
            if d == date:
                if m not in all_models:
                    all_models[m] = {"daily": usage, "monthly": None}
                else:
                    all_models[m]["daily"] = usage

        for key, usage in self._monthly_usage.items():
            if ":" not in key:
                continue
            m, mo = key.split(":", 1)
            if mo == month:
                if m not in all_models:
                    all_models[m] = {"daily": None, "monthly": usage}
                else:
                    all_models[m]["monthly"] = usage

        return {
            "models": {
                m: {
                    "daily_tokens": (v["daily"].total_tokens if v["daily"] else 0),
                    "daily_calls": (v["daily"].calls if v["daily"] else 0),
                    "monthly_tokens": (v["monthly"].total_tokens if v["monthly"] else 0),
                    "monthly_calls": (v["monthly"].calls if v["monthly"] else 0),
                }
                for m, v in all_models.items()
            },
            "global_daily_limit": self.config.daily_limit,
            "global_monthly_limit": self.config.monthly_limit,
        }

    def reset_daily(self, model: Optional[str] = None) -> None:
        """Reset daily usage counters.

        Args:
            model: If provided, reset only that model. Otherwise reset all.
        """
        date = self._current_date()
        if model:
            key = f"{model}:{date}"
            if key in self._daily_usage:
                del self._daily_usage[key]
        else:
            self._daily_usage.clear()

    def reset_monthly(self, model: Optional[str] = None) -> None:
        """Reset monthly usage counters.

        Args:
            model: If provided, reset only that model. Otherwise reset all.
        """
        month = self._current_month()
        if model:
            key = f"{model}:{month}"
            if key in self._monthly_usage:
                del self._monthly_usage[key]
        else:
            self._monthly_usage.clear()
