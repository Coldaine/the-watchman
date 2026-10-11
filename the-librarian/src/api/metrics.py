"""Basic metrics collection for monitoring."""

import time
from collections import defaultdict, Counter
from typing import Dict, Any
from datetime import datetime


class MetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self):
        """Initialize metrics collector."""
        self.request_count = Counter()
        self.request_duration = defaultdict(list)
        self.validation_results = Counter()
        self.document_ingestions = Counter()
        self.start_time = time.time()

    def record_request(self, method: str, path: str, duration_ms: float, status: int) -> None:
        """
        Record API request metrics.

        Args:
            method: HTTP method
            path: Request path
            duration_ms: Request duration
            status: HTTP status code
        """
        key = f"{method}:{path}:{status}"
        self.request_count[key] += 1
        self.request_duration[f"{method}:{path}"].append(duration_ms)

    def record_validation(self, status: str) -> None:
        """
        Record validation result.

        Args:
            status: Validation status (approved, rejected, etc.)
        """
        self.validation_results[status] += 1

    def record_ingestion(self, doc_type: str, success: bool) -> None:
        """
        Record document ingestion.

        Args:
            doc_type: Type of document
            success: Whether ingestion succeeded
        """
        key = f"{doc_type}:{'success' if success else 'failure'}"
        self.document_ingestions[key] += 1

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot.

        Returns:
            Dictionary with collected metrics
        """
        uptime_seconds = time.time() - self.start_time

        # Calculate average durations
        avg_duration_ms = {}
        for key, durations in self.request_duration.items():
            if durations:
                avg_duration_ms[key] = sum(durations) / len(durations)

        return {
            "uptime_seconds": uptime_seconds,
            "timestamp": datetime.utcnow().isoformat(),
            "requests": {
                "total": sum(self.request_count.values()),
                "by_endpoint": dict(self.request_count),
                "avg_duration_ms": avg_duration_ms
            },
            "validations": {
                "total": sum(self.validation_results.values()),
                "by_status": dict(self.validation_results)
            },
            "ingestions": {
                "total": sum(self.document_ingestions.values()),
                "by_type": dict(self.document_ingestions)
            }
        }

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.request_count.clear()
        self.request_duration.clear()
        self.validation_results.clear()
        self.document_ingestions.clear()
        self.start_time = time.time()


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    return _metrics_collector
