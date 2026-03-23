# src/governance/token_budget.py
"""Token and cost governance for LLM usage."""

import logging
import time
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage record."""
    timestamp: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    request_id: str


@dataclass
class BudgetStatus:
    """Current budget status."""
    total_tokens_used: int
    total_cost: float
    requests_count: int
    budget_remaining: float
    tokens_remaining: int
    is_over_budget: bool
    period_start: str
    period_end: str


@dataclass
class CostConfig:
    """Cost configuration per model."""
    input_cost_per_1k: float
    output_cost_per_1k: float


# Cost per 1K tokens for common models (as of 2024)
MODEL_COSTS: Dict[str, CostConfig] = {
    # Gemini (free tier, but track anyway)
    "gemini/gemini-2.5-flash": CostConfig(0.0, 0.0),
    "gemini/gemini-pro": CostConfig(0.0, 0.0),

    # Groq (free tier)
    "groq/llama-3.1-8b-instant": CostConfig(0.0, 0.0),
    "groq/llama-3.1-70b-versatile": CostConfig(0.0, 0.0),

    # OpenRouter (various)
    "openrouter/google/gemma-3-27b-it:free": CostConfig(0.0, 0.0),
    "openrouter/llama-3.1-8b-instruct": CostConfig(0.0, 0.0),

    # OpenAI (for reference if used)
    "openai/gpt-4o-mini": CostConfig(0.00015, 0.0006),
    "openai/gpt-4o": CostConfig(0.005, 0.015),
    "openai/gpt-3.5-turbo": CostConfig(0.0005, 0.0015),

    # Anthropic (for reference)
    "anthropic/claude-3-haiku": CostConfig(0.00025, 0.00125),
    "anthropic/claude-3-sonnet": CostConfig(0.003, 0.015),

    # Default for unknown models
    "default": CostConfig(0.001, 0.002),
}


class TokenBudgetManager:
    """
    Manages token budgets and cost tracking.

    Features:
    - Per-request token tracking
    - Daily/monthly budget limits
    - Cost estimation
    - Usage alerts
    """

    def __init__(
        self,
        daily_token_limit: int = None,
        monthly_token_limit: int = None,
        daily_cost_limit: float = None,
        monthly_cost_limit: float = None,
        alert_threshold: float = 0.8
    ):
        self.daily_token_limit = daily_token_limit or int(os.getenv("DAILY_TOKEN_LIMIT", "1000000"))
        self.monthly_token_limit = monthly_token_limit or int(os.getenv("MONTHLY_TOKEN_LIMIT", "10000000"))
        self.daily_cost_limit = daily_cost_limit or float(os.getenv("DAILY_COST_LIMIT", "10.0"))
        self.monthly_cost_limit = monthly_cost_limit or float(os.getenv("MONTHLY_COST_LIMIT", "100.0"))
        self.alert_threshold = alert_threshold

        # In-memory tracking (for Lambda, use DynamoDB for persistence)
        self._daily_usage: Dict[str, List[TokenUsage]] = defaultdict(list)
        self._monthly_usage: Dict[str, List[TokenUsage]] = defaultdict(list)

    def get_model_cost(self, model: str) -> CostConfig:
        """Get cost configuration for a model."""
        # Normalize model name
        model_lower = model.lower()

        # Try exact match
        if model_lower in MODEL_COSTS:
            return MODEL_COSTS[model_lower]

        # Try prefix match
        for key in MODEL_COSTS:
            if model_lower.startswith(key.split("/")[0]):
                return MODEL_COSTS[key]

        return MODEL_COSTS["default"]

    def estimate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estimate cost for token usage."""
        config = self.get_model_cost(model)
        input_cost = (input_tokens / 1000) * config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * config.output_cost_per_1k
        return round(input_cost + output_cost, 6)

    def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        request_id: str = None
    ) -> TokenUsage:
        """
        Record token usage.

        Args:
            provider: LLM provider (e.g., "gemini", "groq")
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            request_id: Optional request ID

        Returns:
            TokenUsage record
        """
        total_tokens = input_tokens + output_tokens
        estimated_cost = self.estimate_cost(f"{provider}/{model}", input_tokens, output_tokens)

        usage = TokenUsage(
            timestamp=datetime.utcnow().isoformat(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            request_id=request_id or ""
        )

        # Store in daily and monthly buckets
        today = datetime.utcnow().strftime("%Y-%m-%d")
        month = datetime.utcnow().strftime("%Y-%m")

        self._daily_usage[today].append(usage)
        self._monthly_usage[month].append(usage)

        # Check for alerts
        self._check_alerts(today, month)

        return usage

    def get_daily_status(self, date: str = None) -> BudgetStatus:
        """Get budget status for a day."""
        date = date or datetime.utcnow().strftime("%Y-%m-%d")
        usage_list = self._daily_usage.get(date, [])

        total_tokens = sum(u.total_tokens for u in usage_list)
        total_cost = sum(u.estimated_cost for u in usage_list)

        return BudgetStatus(
            total_tokens_used=total_tokens,
            total_cost=round(total_cost, 4),
            requests_count=len(usage_list),
            budget_remaining=round(self.daily_cost_limit - total_cost, 4),
            tokens_remaining=self.daily_token_limit - total_tokens,
            is_over_budget=(total_tokens > self.daily_token_limit or total_cost > self.daily_cost_limit),
            period_start=f"{date}T00:00:00Z",
            period_end=f"{date}T23:59:59Z"
        )

    def get_monthly_status(self, month: str = None) -> BudgetStatus:
        """Get budget status for a month."""
        month = month or datetime.utcnow().strftime("%Y-%m")
        usage_list = self._monthly_usage.get(month, [])

        total_tokens = sum(u.total_tokens for u in usage_list)
        total_cost = sum(u.estimated_cost for u in usage_list)

        # Calculate period dates
        year, mon = month.split("-")
        period_start = f"{month}-01T00:00:00Z"
        # Approximate end of month
        if int(mon) == 12:
            period_end = f"{int(year)+1}-01-01T00:00:00Z"
        else:
            period_end = f"{year}-{int(mon)+1:02d}-01T00:00:00Z"

        return BudgetStatus(
            total_tokens_used=total_tokens,
            total_cost=round(total_cost, 4),
            requests_count=len(usage_list),
            budget_remaining=round(self.monthly_cost_limit - total_cost, 4),
            tokens_remaining=self.monthly_token_limit - total_tokens,
            is_over_budget=(total_tokens > self.monthly_token_limit or total_cost > self.monthly_cost_limit),
            period_start=period_start,
            period_end=period_end
        )

    def check_budget(self) -> Dict[str, Any]:
        """
        Check if within budget limits.

        Returns:
            Dict with budget status and any warnings
        """
        daily = self.get_daily_status()
        monthly = self.get_monthly_status()

        warnings = []

        # Check daily limits
        if daily.is_over_budget:
            warnings.append("Daily budget exceeded")
        elif daily.total_tokens_used > self.daily_token_limit * self.alert_threshold:
            warnings.append(f"Daily token usage at {daily.total_tokens_used / self.daily_token_limit * 100:.1f}%")

        # Check monthly limits
        if monthly.is_over_budget:
            warnings.append("Monthly budget exceeded")
        elif monthly.total_tokens_used > self.monthly_token_limit * self.alert_threshold:
            warnings.append(f"Monthly token usage at {monthly.total_tokens_used / self.monthly_token_limit * 100:.1f}%")

        return {
            "within_budget": not (daily.is_over_budget or monthly.is_over_budget),
            "daily": {
                "tokens_used": daily.total_tokens_used,
                "tokens_limit": self.daily_token_limit,
                "cost": daily.total_cost,
                "cost_limit": self.daily_cost_limit
            },
            "monthly": {
                "tokens_used": monthly.total_tokens_used,
                "tokens_limit": self.monthly_token_limit,
                "cost": monthly.total_cost,
                "cost_limit": self.monthly_cost_limit
            },
            "warnings": warnings
        }

    def _check_alerts(self, date: str, month: str):
        """Check and log alerts if thresholds exceeded."""
        daily = self.get_daily_status(date)
        monthly = self.get_monthly_status(month)

        if daily.is_over_budget:
            logger.warning(f"BUDGET ALERT: Daily budget exceeded - {daily.total_tokens_used} tokens, ${daily.total_cost}")

        if monthly.is_over_budget:
            logger.warning(f"BUDGET ALERT: Monthly budget exceeded - {monthly.total_tokens_used} tokens, ${monthly.total_cost}")

    def should_throttle(self) -> bool:
        """Check if requests should be throttled due to budget."""
        status = self.check_budget()
        return not status["within_budget"]

    def get_usage_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get usage summary for recent days."""
        summary = []
        today = datetime.utcnow()

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            status = self.get_daily_status(date)
            summary.append({
                "date": date,
                "tokens": status.total_tokens_used,
                "cost": status.total_cost,
                "requests": status.requests_count
            })

        return summary


# Module-level singleton
_manager = None


def get_budget_manager() -> TokenBudgetManager:
    """Get singleton budget manager instance."""
    global _manager
    if _manager is None:
        _manager = TokenBudgetManager()
    return _manager


def record_llm_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    request_id: str = None
) -> TokenUsage:
    """Record LLM token usage (convenience function)."""
    return get_budget_manager().record_usage(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        request_id=request_id
    )


def check_budget() -> Dict[str, Any]:
    """Check current budget status (convenience function)."""
    return get_budget_manager().check_budget()


def should_throttle() -> bool:
    """Check if requests should be throttled (convenience function)."""
    return get_budget_manager().should_throttle()
