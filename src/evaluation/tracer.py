"""
Pipeline tracing for debugging and performance monitoring.

Captures detailed logs at each pipeline stage.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class StageTrace:
    """Trace data for a single pipeline stage."""
    name: str
    start_time: float
    end_time: float = 0.0
    input_summary: str = ""
    output_summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def latency_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


@dataclass
class TraceResult:
    """Complete trace of a pipeline run."""
    trace_id: str
    query: str
    timestamp: str
    stages: Dict[str, StageTrace]
    total_latency_ms: float
    success: bool
    final_answer: str = ""
    error: Optional[str] = None


class PipelineTracer:
    """
    Tracer for capturing pipeline execution details.

    Usage:
        tracer = PipelineTracer(query)
        with tracer.trace_stage("retrieval") as stage:
            chunks = retrieve(query)
            stage.metadata["chunks_found"] = len(chunks)
        result = tracer.get_result()
    """

    def __init__(self, query: str):
        self.trace_id = str(uuid.uuid4())[:8]
        self.query = query
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.stages: Dict[str, StageTrace] = {}
        self.start_time = time.time()
        self.success = True
        self.error: Optional[str] = None
        self.final_answer = ""

    def trace_stage(self, name: str):
        """Context manager for tracing a stage."""
        return _StageContext(self, name)

    def record_stage(
        self,
        name: str,
        input_summary: str = "",
        output_summary: str = "",
        metadata: Dict[str, Any] = None,
        latency_ms: float = 0,
        error: str = None
    ):
        """Manually record a stage trace."""
        now = time.time()
        self.stages[name] = StageTrace(
            name=name,
            start_time=now - (latency_ms / 1000),
            end_time=now,
            input_summary=input_summary,
            output_summary=output_summary,
            metadata=metadata or {},
            error=error
        )
        if error:
            self.success = False
            self.error = error

    def set_answer(self, answer: str):
        """Set the final answer."""
        self.final_answer = answer

    def set_error(self, error: str):
        """Mark the trace as failed."""
        self.success = False
        self.error = error

    def get_result(self) -> TraceResult:
        """Get the complete trace result."""
        total_latency = (time.time() - self.start_time) * 1000

        return TraceResult(
            trace_id=self.trace_id,
            query=self.query,
            timestamp=self.timestamp,
            stages=self.stages,
            total_latency_ms=total_latency,
            success=self.success,
            final_answer=self.final_answer[:200] if self.final_answer else "",
            error=self.error
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for logging/storage."""
        result = self.get_result()
        return {
            "trace_id": result.trace_id,
            "query": result.query,
            "timestamp": result.timestamp,
            "stages": {
                name: {
                    "latency_ms": stage.latency_ms,
                    "input": stage.input_summary[:100],
                    "output": stage.output_summary[:100],
                    "metadata": stage.metadata,
                    "error": stage.error
                }
                for name, stage in result.stages.items()
            },
            "total_latency_ms": result.total_latency_ms,
            "success": result.success,
            "error": result.error
        }


class _StageContext:
    """Context manager for stage tracing."""

    def __init__(self, tracer: PipelineTracer, name: str):
        self.tracer = tracer
        self.name = name
        self.stage: Optional[StageTrace] = None

    def __enter__(self):
        self.stage = StageTrace(
            name=self.name,
            start_time=time.time()
        )
        return self.stage

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.stage:
            self.stage.end_time = time.time()
            if exc_val:
                self.stage.error = str(exc_val)[:200]
                self.tracer.success = False
                self.tracer.error = str(exc_val)[:200]
            self.tracer.stages[self.name] = self.stage
        return False  # Don't suppress exceptions


def format_trace_summary(trace: TraceResult) -> str:
    """Format a trace as a human-readable summary."""
    lines = [
        f"=== Trace {trace.trace_id} ===",
        f"Query: {trace.query[:50]}...",
        f"Status: {'SUCCESS' if trace.success else 'FAILED'}",
        f"Total Latency: {trace.total_latency_ms:.0f}ms",
        "",
        "Stages:"
    ]

    for name, stage in trace.stages.items():
        status = "OK" if not stage.error else f"ERROR: {stage.error[:30]}"
        lines.append(f"  {name}: {stage.latency_ms:.0f}ms [{status}]")
        if stage.metadata:
            for k, v in list(stage.metadata.items())[:3]:
                lines.append(f"    {k}: {v}")

    if trace.error:
        lines.append(f"\nError: {trace.error}")

    return "\n".join(lines)
