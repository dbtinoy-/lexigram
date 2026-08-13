"""Benchmark result data class."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BenchmarkResult:
    """Result of a single benchmark run."""

    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    ops_per_second: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the result to a plain dictionary.

        Returns:
            Dictionary representation of the benchmark result.
        """
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time": self.total_time,
            "avg_time_ms": self.avg_time * 1000,
            "min_time_ms": self.min_time * 1000,
            "max_time_ms": self.max_time * 1000,
            "ops_per_second": self.ops_per_second,
            "timestamp": self.timestamp.isoformat(),
        }


__all__ = [
    "BenchmarkResult",
]
