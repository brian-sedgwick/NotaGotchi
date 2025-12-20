"""
Not-A-Gotchi Performance Metrics

Provides performance monitoring and metrics collection for the application.
Tracks frame times, database latency, and other key performance indicators.
"""

import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import deque
from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MetricsSample:
    """A single metrics sample with timestamp."""
    value: float
    timestamp: float = field(default_factory=time.time)


class MovingAverage:
    """
    Calculates a moving average over a fixed window of samples.
    """

    def __init__(self, window_size: int = 100):
        """
        Initialize moving average calculator.

        Args:
            window_size: Number of samples to keep in the window
        """
        self._samples: deque = deque(maxlen=window_size)
        self._sum: float = 0.0

    def add(self, value: float) -> None:
        """Add a sample to the moving average."""
        if len(self._samples) == self._samples.maxlen:
            # Remove oldest value from sum
            self._sum -= self._samples[0]
        self._samples.append(value)
        self._sum += value

    @property
    def average(self) -> float:
        """Get the current moving average."""
        if not self._samples:
            return 0.0
        return self._sum / len(self._samples)

    @property
    def min(self) -> float:
        """Get the minimum value in the window."""
        return min(self._samples) if self._samples else 0.0

    @property
    def max(self) -> float:
        """Get the maximum value in the window."""
        return max(self._samples) if self._samples else 0.0

    @property
    def count(self) -> int:
        """Get the number of samples in the window."""
        return len(self._samples)


class Timer:
    """
    Context manager for timing code blocks.

    Usage:
        with Timer() as t:
            # code to time
        print(f"Took {t.elapsed_ms:.2f}ms")
    """

    def __init__(self):
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def __enter__(self) -> 'Timer':
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        self.end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """Elapsed time in seconds."""
        return self.end_time - self.start_time

    @property
    def elapsed_ms(self) -> float:
        """Elapsed time in milliseconds."""
        return self.elapsed * 1000


class PerformanceMetrics:
    """
    Centralized performance metrics collector.

    Tracks various performance metrics across the application:
    - Frame time (main loop iteration time)
    - Database query latency
    - Display update time
    - WiFi operation latency
    """

    def __init__(self):
        """Initialize the metrics collector."""
        self._metrics: Dict[str, MovingAverage] = {
            'frame_time_ms': MovingAverage(100),
            'db_query_ms': MovingAverage(50),
            'display_update_ms': MovingAverage(30),
            'wifi_latency_ms': MovingAverage(20),
        }
        self._last_log_time = time.time()
        self._log_interval = 60.0  # Log summary every 60 seconds
        self._enabled = True

    def record(self, metric_name: str, value_ms: float) -> None:
        """
        Record a metric value.

        Args:
            metric_name: Name of the metric (e.g., 'frame_time_ms')
            value_ms: Value in milliseconds
        """
        if not self._enabled:
            return

        if metric_name not in self._metrics:
            self._metrics[metric_name] = MovingAverage(50)

        self._metrics[metric_name].add(value_ms)

        # Log periodic summary
        if time.time() - self._last_log_time >= self._log_interval:
            self._log_summary()
            self._last_log_time = time.time()

    def record_frame_time(self, elapsed_ms: float) -> None:
        """Record frame time (main loop iteration)."""
        self.record('frame_time_ms', elapsed_ms)

    def record_db_query(self, elapsed_ms: float) -> None:
        """Record database query latency."""
        self.record('db_query_ms', elapsed_ms)

    def record_display_update(self, elapsed_ms: float) -> None:
        """Record display update time."""
        self.record('display_update_ms', elapsed_ms)

    def record_wifi_latency(self, elapsed_ms: float) -> None:
        """Record WiFi operation latency."""
        self.record('wifi_latency_ms', elapsed_ms)

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        """
        Get a summary of all metrics.

        Returns:
            Dictionary mapping metric names to their stats (avg, min, max)
        """
        summary = {}
        for name, avg in self._metrics.items():
            if avg.count > 0:
                summary[name] = {
                    'avg': avg.average,
                    'min': avg.min,
                    'max': avg.max,
                    'count': avg.count
                }
        return summary

    def _log_summary(self) -> None:
        """Log a summary of performance metrics."""
        summary = self.get_summary()
        if not summary:
            return

        logger.info("=== Performance Metrics Summary ===")
        for name, stats in summary.items():
            logger.info(
                f"  {name}: avg={stats['avg']:.2f}ms, "
                f"min={stats['min']:.2f}ms, max={stats['max']:.2f}ms"
            )

    def enable(self) -> None:
        """Enable metrics collection."""
        self._enabled = True
        logger.info("Performance metrics enabled")

    def disable(self) -> None:
        """Disable metrics collection."""
        self._enabled = False
        logger.info("Performance metrics disabled")

    def set_log_interval(self, seconds: float) -> None:
        """Set the interval for logging metric summaries."""
        self._log_interval = seconds


# Global metrics instance
_metrics: Optional[PerformanceMetrics] = None


def get_metrics() -> PerformanceMetrics:
    """
    Get the global metrics instance.

    Returns:
        PerformanceMetrics singleton instance
    """
    global _metrics
    if _metrics is None:
        _metrics = PerformanceMetrics()
    return _metrics


def timed_operation(metric_name: str):
    """
    Decorator for timing function calls and recording to metrics.

    Usage:
        @timed_operation('db_query_ms')
        def fetch_data():
            # database query
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with Timer() as t:
                result = func(*args, **kwargs)
            get_metrics().record(metric_name, t.elapsed_ms)
            return result
        return wrapper
    return decorator


# Convenience functions
def record_frame_time(elapsed_ms: float) -> None:
    """Record frame time to global metrics."""
    get_metrics().record_frame_time(elapsed_ms)


def record_db_query(elapsed_ms: float) -> None:
    """Record database query latency to global metrics."""
    get_metrics().record_db_query(elapsed_ms)


def record_display_update(elapsed_ms: float) -> None:
    """Record display update time to global metrics."""
    get_metrics().record_display_update(elapsed_ms)


def record_wifi_latency(elapsed_ms: float) -> None:
    """Record WiFi latency to global metrics."""
    get_metrics().record_wifi_latency(elapsed_ms)
