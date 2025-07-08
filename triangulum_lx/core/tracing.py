"""
Observability and Tracing for Triangulum LX.

This module provides end-to-end tracing capabilities for the Triangulum system,
allowing operators to track the complete execution flow of bug-fixing attempts
and identify performance bottlenecks.
"""

import time
import uuid
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass, field

@dataclass
class Span:
    """
    Represents a single traced operation.
    """
    span_id: str
    name: str
    start_time: float
    end_time: Optional[float] = None
    parent_id: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Returns the span duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000
    
    def add_attribute(self, key: str, value: Any) -> None:
        """Adds an attribute to the span."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Adds an event to the span."""
        event = {
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        }
        self.events.append(event)

class TracingContext:
    """
    Manages the current tracing context and active spans.
    """
    
    def __init__(self):
        self.spans: Dict[str, Span] = {}
        self.active_span_stack: List[str] = []
        self.trace_id: Optional[str] = None
    
    def start_trace(self, name: str) -> str:
        """Starts a new trace."""
        self.trace_id = str(uuid.uuid4())
        root_span_id = self.start_span(name)
        return root_span_id
    
    def start_span(self, name: str, parent_id: Optional[str] = None) -> str:
        """Starts a new span."""
        span_id = str(uuid.uuid4())
        
        if parent_id is None and self.active_span_stack:
            parent_id = self.active_span_stack[-1]
        
        span = Span(
            span_id=span_id,
            name=name,
            start_time=time.time(),
            parent_id=parent_id
        )
        
        self.spans[span_id] = span
        self.active_span_stack.append(span_id)
        return span_id
    
    def end_span(self, span_id: str) -> None:
        """Ends a span."""
        if span_id in self.spans:
            self.spans[span_id].end_time = time.time()
        
        if self.active_span_stack and self.active_span_stack[-1] == span_id:
            self.active_span_stack.pop()
    
    def get_current_span(self) -> Optional[Span]:
        """Returns the currently active span."""
        if not self.active_span_stack:
            return None
        current_span_id = self.active_span_stack[-1]
        return self.spans.get(current_span_id)
    
    def add_attribute(self, key: str, value: Any) -> None:
        """Adds an attribute to the current span."""
        current_span = self.get_current_span()
        if current_span:
            current_span.add_attribute(key, value)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Adds an event to the current span."""
        current_span = self.get_current_span()
        if current_span:
            current_span.add_event(name, attributes)

# Global tracing context
_tracing_context = TracingContext()

@contextmanager
def trace_span(name: str, **attributes):
    """
    Context manager for creating traced spans.
    
    Usage:
        with trace_span("llm_generation", provider="openai", model="gpt-4"):
            # Your code here
            pass
    """
    span_id = _tracing_context.start_span(name)
    
    # Add initial attributes
    for key, value in attributes.items():
        _tracing_context.add_attribute(key, value)
    
    try:
        yield _tracing_context.get_current_span()
    finally:
        _tracing_context.end_span(span_id)

def start_trace(name: str) -> str:
    """Starts a new trace."""
    return _tracing_context.start_trace(name)

def add_attribute(key: str, value: Any) -> None:
    """Adds an attribute to the current span."""
    _tracing_context.add_attribute(key, value)

def add_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """Adds an event to the current span."""
    _tracing_context.add_event(name, attributes)

def get_trace_data() -> Dict[str, Any]:
    """Returns the current trace data."""
    return {
        "trace_id": _tracing_context.trace_id,
        "spans": [
            {
                "span_id": span.span_id,
                "name": span.name,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "duration_ms": span.duration_ms,
                "parent_id": span.parent_id,
                "attributes": span.attributes,
                "events": span.events
            }
            for span in _tracing_context.spans.values()
        ]
    }

def export_trace_to_json() -> str:
    """Exports the current trace as JSON."""
    import json
    return json.dumps(get_trace_data(), indent=2, default=str)

def clear_trace() -> None:
    """Clears the current trace data."""
    _tracing_context.spans.clear()
    _tracing_context.active_span_stack.clear()
    _tracing_context.trace_id = None

class TracingMiddleware:
    """
    Middleware that can be integrated into the RequestManager and AutoGenCoordinator
    to automatically trace LLM calls and debugging steps.
    """
    
    @staticmethod
    def trace_llm_request(provider_name: str, model_name: str, prompt: str):
        """Returns a context manager for tracing LLM requests."""
        return trace_span(
            "llm_request",
            provider=provider_name,
            model=model_name,
            prompt_length=len(prompt),
            operation_type="llm_generation"
        )
    
    @staticmethod
    def trace_debugging_step(step_name: str, agent_name: str):
        """Returns a context manager for tracing debugging steps."""
        return trace_span(
            f"debug_step_{step_name}",
            agent=agent_name,
            step=step_name,
            operation_type="debugging"
        )
    
    @staticmethod
    def trace_patch_application(patch_size: int):
        """Returns a context manager for tracing patch applications."""
        return trace_span(
            "patch_application",
            patch_size=patch_size,
            operation_type="code_modification"
        )
