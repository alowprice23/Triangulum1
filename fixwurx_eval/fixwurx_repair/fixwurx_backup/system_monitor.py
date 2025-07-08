"""
monitoring/system_monitor.py
────────────────────────────
Light-weight *telemetry bridge* that publishes a handful of **core runtime
metrics**—tick counter, scope entropy (H₀), and agent utilisation—to whatever
metric back-end the deployment chooses (Prometheus, Datadog, ELK, stdout, …).

Abstractions
────────────
`MetricBus` is a *very thin* dependency-inversion layer: an object exposing a
single

    send(metric_name:str, value:float, tags:dict[str,str]|None) -> None

method.  In production we inject a Prometheus/StatsD/OTLP implementation; in
unit-tests we pass a tiny stub that records calls.

Usage
─────
```python
bus = PromMetricBus()          # your impl
mon = SystemMonitor(engine, metric_bus=bus)

while True:
    await engine.execute_tick()
    mon.emit_tick()            # push metrics for this tick
```
"""
from __future__ import annotations

from typing import Protocol, Dict, Optional

class Engine(Protocol):
    """Protocol for the Triangulum engine, defining the interface for monitoring."""
    @property
    def tick_count(self) -> int:
        ...

    @property
    def scope_entropy(self) -> float:
        ...

    @property
    def agent_utilization(self) -> Dict[str, float]:
        ...

class MetricBus(Protocol):
    """Protocol for a metric bus, defining the interface for sending metrics."""
    def send(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        ...

class SystemMonitor:
    """
    Publishes core runtime metrics from the Triangulum engine to a metric bus.
    """
    def __init__(self, engine: Engine, metric_bus: MetricBus):
        """
        Initialize the SystemMonitor.

        Args:
            engine: The Triangulum engine to monitor.
            metric_bus: The metric bus to send metrics to.
        """
        self.engine = engine
        self.metric_bus = metric_bus

    def emit_tick(self) -> None:
        """
        Emit metrics for the current engine tick.
        """
        self.metric_bus.send("triangulum.tick_count", self.engine.tick_count)
        self.metric_bus.send("triangulum.scope_entropy", self.engine.scope_entropy)

        for agent_id, utilization in self.engine.agent_utilization.items():
            self.metric_bus.send(
                "triangulum.agent_utilization",
                utilization,
                tags={"agent_id": agent_id}
            )
