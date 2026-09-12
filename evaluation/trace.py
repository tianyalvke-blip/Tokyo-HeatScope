"""Normalized, observable Agent execution traces. Never stores hidden reasoning."""
from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any


class TraceCollector:
    """Small collector used by adapters; event schemas remain intentionally open."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self._started = perf_counter()

    def record(self, event_type: str, name: str | None = None, *, input: Any = None,
               output: Any = None, success: bool | None = None,
               duration_ms: float | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        event = {
            "step": len(self.events) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "name": name,
            "input": input,
            "output": output,
            "success": success,
            "duration_ms": duration_ms,
            "metadata": metadata or {},
        }
        self.events.append(event)
        return event

    @property
    def latency_ms(self) -> int:
        return round((perf_counter() - self._started) * 1000)
