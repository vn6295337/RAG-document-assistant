# src/monitoring/anomaly_detector.py
"""Anomaly detection for RAG pipeline monitoring."""

import logging
import statistics
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    """Detected anomaly."""
    timestamp: str
    metric_name: str
    value: float
    threshold: float
    anomaly_type: str  # spike, drop, drift, outlier
    severity: str  # info, warning, critical
    message: str


@dataclass
class AnomalyReport:
    """Anomaly detection report."""
    period_start: str
    period_end: str
    anomalies_detected: int
    critical_count: int
    warning_count: int
    anomalies: List[Anomaly]
    metric_summaries: Dict[str, Dict[str, float]]


class MetricBuffer:
    """Rolling buffer for metric values."""

    def __init__(self, max_size: int = 1000):
        self.values = deque(maxlen=max_size)
        self.timestamps = deque(maxlen=max_size)

    def add(self, value: float, timestamp: str = None):
        self.values.append(value)
        self.timestamps.append(timestamp or datetime.utcnow().isoformat())

    def get_stats(self) -> Dict[str, float]:
        if len(self.values) < 2:
            return {"mean": 0, "std": 0, "min": 0, "max": 0, "count": len(self.values)}

        values = list(self.values)
        return {
            "mean": statistics.mean(values),
            "std": statistics.stdev(values),
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }


class AnomalyDetector:
    """
    Detects anomalies in RAG pipeline metrics.

    Monitors:
    - Latency spikes
    - Error rate increases
    - Token usage anomalies
    - Retrieval quality drops
    - Query pattern changes
    """

    def __init__(
        self,
        latency_threshold_ms: float = 5000,
        error_rate_threshold: float = 0.1,
        z_score_threshold: float = 3.0,
        min_samples: int = 10
    ):
        self.latency_threshold_ms = latency_threshold_ms
        self.error_rate_threshold = error_rate_threshold
        self.z_score_threshold = z_score_threshold
        self.min_samples = min_samples

        # Metric buffers
        self._metrics: Dict[str, MetricBuffer] = {
            "latency": MetricBuffer(),
            "token_usage": MetricBuffer(),
            "retrieval_score": MetricBuffer(),
            "error_count": MetricBuffer(),
            "query_length": MetricBuffer()
        }

        # Detected anomalies
        self._anomalies: List[Anomaly] = []

    def record_metric(self, metric_name: str, value: float):
        """Record a metric value."""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = MetricBuffer()
        self._metrics[metric_name].add(value)

        # Check for anomaly
        anomaly = self._check_anomaly(metric_name, value)
        if anomaly:
            self._anomalies.append(anomaly)
            self._log_anomaly(anomaly)

    def record_request(
        self,
        latency_ms: float,
        token_count: int,
        retrieval_score: float,
        is_error: bool,
        query_length: int
    ):
        """Record metrics for a request."""
        self.record_metric("latency", latency_ms)
        self.record_metric("token_usage", token_count)
        self.record_metric("retrieval_score", retrieval_score)
        self.record_metric("error_count", 1 if is_error else 0)
        self.record_metric("query_length", query_length)

    def _check_anomaly(self, metric_name: str, value: float) -> Optional[Anomaly]:
        """Check if a value is anomalous."""
        buffer = self._metrics.get(metric_name)
        if not buffer or len(buffer.values) < self.min_samples:
            return None

        stats = buffer.get_stats()
        mean = stats["mean"]
        std = stats["std"]

        if std == 0:
            return None

        # Calculate z-score
        z_score = abs(value - mean) / std

        # Check for anomaly
        if z_score >= self.z_score_threshold:
            # Determine type and severity
            if value > mean:
                anomaly_type = "spike"
            else:
                anomaly_type = "drop"

            if z_score >= self.z_score_threshold * 2:
                severity = "critical"
            elif z_score >= self.z_score_threshold * 1.5:
                severity = "warning"
            else:
                severity = "info"

            return Anomaly(
                timestamp=datetime.utcnow().isoformat(),
                metric_name=metric_name,
                value=value,
                threshold=mean + (self.z_score_threshold * std),
                anomaly_type=anomaly_type,
                severity=severity,
                message=f"{metric_name} {anomaly_type}: {value:.2f} (z-score: {z_score:.2f})"
            )

        # Check absolute thresholds
        if metric_name == "latency" and value > self.latency_threshold_ms:
            return Anomaly(
                timestamp=datetime.utcnow().isoformat(),
                metric_name=metric_name,
                value=value,
                threshold=self.latency_threshold_ms,
                anomaly_type="threshold_exceeded",
                severity="warning",
                message=f"Latency exceeded threshold: {value:.0f}ms > {self.latency_threshold_ms}ms"
            )

        return None

    def _log_anomaly(self, anomaly: Anomaly):
        """Log detected anomaly."""
        if anomaly.severity == "critical":
            logger.error(f"ANOMALY [CRITICAL]: {anomaly.message}")
        elif anomaly.severity == "warning":
            logger.warning(f"ANOMALY [WARNING]: {anomaly.message}")
        else:
            logger.info(f"ANOMALY [INFO]: {anomaly.message}")

    def check_error_rate(self, window_size: int = 100) -> Optional[Anomaly]:
        """Check if error rate exceeds threshold."""
        buffer = self._metrics.get("error_count")
        if not buffer or len(buffer.values) < window_size:
            return None

        recent = list(buffer.values)[-window_size:]
        error_rate = sum(recent) / len(recent)

        if error_rate > self.error_rate_threshold:
            anomaly = Anomaly(
                timestamp=datetime.utcnow().isoformat(),
                metric_name="error_rate",
                value=error_rate,
                threshold=self.error_rate_threshold,
                anomaly_type="threshold_exceeded",
                severity="critical" if error_rate > 0.3 else "warning",
                message=f"Error rate elevated: {error_rate:.1%} > {self.error_rate_threshold:.1%}"
            )
            self._anomalies.append(anomaly)
            return anomaly

        return None

    def detect_drift(self, metric_name: str, window_size: int = 50) -> Optional[Anomaly]:
        """Detect gradual drift in a metric."""
        buffer = self._metrics.get(metric_name)
        if not buffer or len(buffer.values) < window_size * 2:
            return None

        values = list(buffer.values)
        old_window = values[-window_size * 2:-window_size]
        new_window = values[-window_size:]

        old_mean = statistics.mean(old_window)
        new_mean = statistics.mean(new_window)

        if old_mean == 0:
            return None

        drift_pct = (new_mean - old_mean) / old_mean

        if abs(drift_pct) > 0.2:  # 20% drift
            anomaly = Anomaly(
                timestamp=datetime.utcnow().isoformat(),
                metric_name=metric_name,
                value=new_mean,
                threshold=old_mean,
                anomaly_type="drift",
                severity="warning",
                message=f"{metric_name} drift: {drift_pct:+.1%} change"
            )
            self._anomalies.append(anomaly)
            return anomaly

        return None

    def generate_report(self, hours: int = 24) -> AnomalyReport:
        """Generate anomaly report."""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)

        # Filter recent anomalies
        recent = [
            a for a in self._anomalies
            if datetime.fromisoformat(a.timestamp.replace("Z", "")) > cutoff
        ]

        # Get metric summaries
        summaries = {}
        for name, buffer in self._metrics.items():
            summaries[name] = buffer.get_stats()

        return AnomalyReport(
            period_start=cutoff.isoformat(),
            period_end=now.isoformat(),
            anomalies_detected=len(recent),
            critical_count=sum(1 for a in recent if a.severity == "critical"),
            warning_count=sum(1 for a in recent if a.severity == "warning"),
            anomalies=recent[-20:],  # Last 20
            metric_summaries=summaries
        )

    def clear_old_anomalies(self, days: int = 7):
        """Clear anomalies older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        self._anomalies = [
            a for a in self._anomalies
            if datetime.fromisoformat(a.timestamp.replace("Z", "")) > cutoff
        ]


# Module-level singleton
_detector = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get singleton anomaly detector instance."""
    global _detector
    if _detector is None:
        _detector = AnomalyDetector()
    return _detector


def record_metric(metric_name: str, value: float):
    """Record a metric value (convenience function)."""
    get_anomaly_detector().record_metric(metric_name, value)


def record_request_metrics(
    latency_ms: float,
    token_count: int = 0,
    retrieval_score: float = 0.0,
    is_error: bool = False,
    query_length: int = 0
):
    """Record request metrics (convenience function)."""
    get_anomaly_detector().record_request(
        latency_ms, token_count, retrieval_score, is_error, query_length
    )


def get_anomaly_report(hours: int = 24) -> AnomalyReport:
    """Get anomaly report (convenience function)."""
    return get_anomaly_detector().generate_report(hours)
