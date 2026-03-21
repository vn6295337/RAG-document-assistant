# src/monitoring/failover_tracker.py
"""LLM failover frequency tracking and monitoring."""

import logging
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class FailoverEvent:
    """Record of a failover event."""
    timestamp: str
    primary_provider: str
    fallback_provider: str
    reason: str  # error, timeout, rate_limit
    latency_ms: int
    request_id: str


@dataclass
class ProviderHealth:
    """Health status of an LLM provider."""
    provider: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_latency_ms: float
    last_failure: Optional[str]
    last_success: Optional[str]


@dataclass
class FailoverReport:
    """Failover frequency report."""
    period_start: str
    period_end: str
    total_requests: int
    failover_count: int
    failover_rate: float
    provider_health: Dict[str, ProviderHealth]
    recent_failures: List[FailoverEvent]
    recommendations: List[str]


class FailoverTracker:
    """
    Tracks LLM provider failover frequency and health.

    Monitors:
    - Primary provider success rate
    - Failover frequency
    - Per-provider latency and errors
    - Patterns in failures
    """

    def __init__(
        self,
        warning_threshold: float = 0.1,  # Warn if >10% failover
        critical_threshold: float = 0.3,  # Critical if >30% failover
        history_days: int = 7
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.history_days = history_days

        # In-memory tracking (use DynamoDB for persistence in Lambda)
        self._events: List[FailoverEvent] = []
        self._provider_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failed": 0,
            "latencies": [],
            "last_failure": None,
            "last_success": None
        })

    def record_request(
        self,
        provider: str,
        success: bool,
        latency_ms: int,
        request_id: str = ""
    ):
        """Record a request to a provider."""
        stats = self._provider_stats[provider]
        stats["total"] += 1

        if success:
            stats["success"] += 1
            stats["last_success"] = datetime.utcnow().isoformat()
        else:
            stats["failed"] += 1
            stats["last_failure"] = datetime.utcnow().isoformat()

        # Keep last 1000 latencies for avg calculation
        stats["latencies"].append(latency_ms)
        if len(stats["latencies"]) > 1000:
            stats["latencies"] = stats["latencies"][-1000:]

    def record_failover(
        self,
        primary_provider: str,
        fallback_provider: str,
        reason: str,
        latency_ms: int,
        request_id: str = ""
    ):
        """Record a failover event."""
        event = FailoverEvent(
            timestamp=datetime.utcnow().isoformat(),
            primary_provider=primary_provider,
            fallback_provider=fallback_provider,
            reason=reason,
            latency_ms=latency_ms,
            request_id=request_id
        )
        self._events.append(event)

        # Record failure for primary
        self.record_request(primary_provider, False, latency_ms, request_id)

        # Keep only recent events
        cutoff = datetime.utcnow() - timedelta(days=self.history_days)
        self._events = [
            e for e in self._events
            if datetime.fromisoformat(e.timestamp.replace("Z", "")) > cutoff
        ]

        logger.warning(
            f"LLM Failover: {primary_provider} -> {fallback_provider} "
            f"(reason: {reason}, latency: {latency_ms}ms)"
        )

    def get_provider_health(self, provider: str) -> ProviderHealth:
        """Get health stats for a provider."""
        stats = self._provider_stats.get(provider, {
            "total": 0, "success": 0, "failed": 0,
            "latencies": [], "last_failure": None, "last_success": None
        })

        total = stats["total"]
        success_rate = stats["success"] / total if total > 0 else 1.0
        avg_latency = sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0

        return ProviderHealth(
            provider=provider,
            total_requests=total,
            successful_requests=stats["success"],
            failed_requests=stats["failed"],
            success_rate=round(success_rate, 3),
            avg_latency_ms=round(avg_latency, 1),
            last_failure=stats["last_failure"],
            last_success=stats["last_success"]
        )

    def generate_report(self, hours: int = 24) -> FailoverReport:
        """Generate failover report for recent period."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)

        # Filter recent events
        recent_events = [
            e for e in self._events
            if datetime.fromisoformat(e.timestamp.replace("Z", "")) > cutoff
        ]

        # Calculate totals
        total_requests = sum(s["total"] for s in self._provider_stats.values())
        failover_count = len(recent_events)
        failover_rate = failover_count / total_requests if total_requests > 0 else 0

        # Provider health
        provider_health = {}
        for provider in self._provider_stats.keys():
            health = self.get_provider_health(provider)
            provider_health[provider] = health

        # Recommendations
        recommendations = []
        if failover_rate >= self.critical_threshold:
            recommendations.append("CRITICAL: High failover rate. Check primary LLM provider status.")
        elif failover_rate >= self.warning_threshold:
            recommendations.append("WARNING: Elevated failover rate. Monitor primary provider.")

        for provider, health in provider_health.items():
            if health.success_rate < 0.9 and health.total_requests > 10:
                recommendations.append(
                    f"Provider '{provider}' has low success rate ({health.success_rate:.1%})"
                )
            if health.avg_latency_ms > 5000:
                recommendations.append(
                    f"Provider '{provider}' has high latency ({health.avg_latency_ms:.0f}ms)"
                )

        if not recommendations:
            recommendations.append("All providers healthy. No action needed.")

        return FailoverReport(
            period_start=(now - timedelta(hours=hours)).isoformat(),
            period_end=now.isoformat(),
            total_requests=total_requests,
            failover_count=failover_count,
            failover_rate=round(failover_rate, 3),
            provider_health=provider_health,
            recent_failures=recent_events[-10:],  # Last 10
            recommendations=recommendations
        )


# Module-level singleton
_tracker = None


def get_failover_tracker() -> FailoverTracker:
    """Get singleton failover tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = FailoverTracker()
    return _tracker


def record_failover(
    primary: str,
    fallback: str,
    reason: str,
    latency_ms: int = 0,
    request_id: str = ""
):
    """Record a failover event (convenience function)."""
    get_failover_tracker().record_failover(
        primary, fallback, reason, latency_ms, request_id
    )


def record_llm_request(provider: str, success: bool, latency_ms: int):
    """Record an LLM request (convenience function)."""
    get_failover_tracker().record_request(provider, success, latency_ms)


def get_failover_report(hours: int = 24) -> FailoverReport:
    """Get failover report (convenience function)."""
    return get_failover_tracker().generate_report(hours)
