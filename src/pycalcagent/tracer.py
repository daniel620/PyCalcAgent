"""Structured OpenTelemetry observability, span linking, and PII redaction for PyCalcAgent (Criterion 4)."""

import json
import logging
import re
import time
from collections.abc import Callable
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# Initialize OpenTelemetry TracerProvider
provider = TracerProvider()
trace.set_tracer_provider(provider)
otel_tracer = trace.get_tracer("pycalcagent.tracer", "0.2.0")


class PIIRedactor:
    """Sanitizes and scrubs PII (emails, phones, SSNs, secrets) from trace events and spans."""

    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
    PHONE_REGEX = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
    SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    SECRET_REGEX = re.compile(r"(?:api[_-]?key|secret|token)\s*=\s*[\"']?([A-Za-z0-9_-]{16,})[\"']?", re.IGNORECASE)

    @classmethod
    def redact_text(cls, text: str) -> str:
        """Redact PII patterns from text."""
        if not isinstance(text, str):
            return str(text)
        text = cls.EMAIL_REGEX.sub("[REDACTED_EMAIL]", text)
        text = cls.PHONE_REGEX.sub("[REDACTED_PHONE]", text)
        text = cls.SSN_REGEX.sub("[REDACTED_SSN]", text)
        text = cls.SECRET_REGEX.sub("api_key=[REDACTED_SECRET]", text)
        return text

    @classmethod
    def redact_payload(cls, data: Any) -> Any:
        """Recursively redact PII from dictionaries, lists, or strings."""
        if isinstance(data, dict):
            return {cls.redact_text(str(k)): cls.redact_payload(v) for k, v in data.items()}
        elif isinstance(data, list | tuple):
            return [cls.redact_payload(item) for item in data]
        elif isinstance(data, str):
            return cls.redact_text(data)
        return data


class EventTracer:
    """Structured JSON event logger and OpenTelemetry span tracer with automatic PII redaction."""

    def __init__(self, log_file: str = ".logs/calc_agent.jsonl", verbose: bool = False):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

        self.logger = logging.getLogger("pycalcagent.tracer")
        self.logger.setLevel(logging.INFO)

    def log_event(self, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Record an OpenTelemetry span and structured JSON trace event with ISO timestamp and PII redaction."""
        # Scrub PII from all incoming data
        redacted_data = PIIRedactor.redact_payload(data)

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": redacted_data,
        }

        # Start OpenTelemetry Span with attributes
        with otel_tracer.start_as_current_span(f"pycalcagent.{event_type.lower()}") as span:
            span.set_attribute("event.type", event_type)
            for k, v in redacted_data.items():
                if isinstance(v, str | int | float | bool):
                    span.set_attribute(f"event.data.{k}", v)
                else:
                    span.set_attribute(f"event.data.{k}", json.dumps(v, default=str))

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")

        if self.verbose:
            print(f"[TRACE - {event_type}]: {json.dumps(redacted_data, default=str)}")

        return payload

    def trace_tool(self, tool_name: str) -> Callable:
        """Decorator to trace tool execution latency, OTel spans, inputs, and outputs with PII redaction."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.perf_counter()
                self.log_event("TOOL_START", {"tool": tool_name, "args": str(args), "kwargs": kwargs})
                with otel_tracer.start_as_current_span(f"tool.{tool_name}") as span:
                    try:
                        result = func(*args, **kwargs)
                        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        span.set_attribute("tool.duration_ms", duration_ms)
                        span.set_attribute("tool.status", "SUCCESS")
                        self.log_event("TOOL_SUCCESS", {
                            "tool": tool_name,
                            "duration_ms": duration_ms,
                            "result": result,
                        })
                        return result
                    except Exception as e:
                        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                        span.set_attribute("tool.duration_ms", duration_ms)
                        span.set_attribute("tool.status", "ERROR")
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
