"""Structured observability and event tracing for PyCalcAgent (Criterion 4: Observability & Tracing)."""

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any


class EventTracer:
    """Structured JSON event logger and execution tracer for monitoring agent reasoning and tools."""

    def __init__(self, log_file: str = ".logs/calc_agent.jsonl", verbose: bool = False):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

        self.logger = logging.getLogger("pycalcagent.tracer")
        self.logger.setLevel(logging.INFO)

    def log_event(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Record a structured trace event with ISO timestamp."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data,
        }

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")

        if self.verbose:
            print(f"[TRACE - {event_type}]: {json.dumps(data, default=str)}")

        return payload

    def trace_tool(self, tool_name: str) -> Callable:
        """Decorator to trace tool execution latency, inputs, and outputs."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                self.log_event("TOOL_START", {"tool": tool_name, "args": args, "kwargs": kwargs})
                try:
                    result = func(*args, **kwargs)
                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    self.log_event("TOOL_SUCCESS", {
                        "tool": tool_name,
                        "duration_ms": duration_ms,
                        "result": result,
                    })
                    return result
                except Exception as e:
                    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    self.log_event("TOOL_ERROR", {
                        "tool": tool_name,
                        "duration_ms": duration_ms,
                        "error": str(e),
                    })
                    raise
            return wrapper
        return decorator


# Global default tracer instance
default_tracer = EventTracer()
