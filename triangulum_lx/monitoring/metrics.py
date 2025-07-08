import time
import json
from pathlib import Path
import numpy as np
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Union
from ..core.state import Phase

@dataclass
class ComprehensiveMetrics:
    """Comprehensive self-assessment metrics for Triangulum."""
    agility_score: float = 0.0
    bug_free_score: float = 0.0
    efficiency_score: float = 0.0
    self_awareness_score: float = 0.0
    operational_score: float = 0.0
    feature_completeness: float = 0.0
    assessment_timestamp: float = 0.0
    confidence_level: float = 0.0

@dataclass
class TickMetrics:
    """Metrics collected during a single tick of the system."""
    tick_number: int
    timestamp: float
    free_agents: int
    bugs_waiting: int
    bugs_in_repro: int
    bugs_in_patch: int
    bugs_in_verify: int
    bugs_done: int
    bugs_escalated: int
    entropy_bits: float
    
    @property
    def total_bugs(self) -> int:
        """Total number of bugs in the system."""
        return (self.bugs_waiting + self.bugs_in_repro + self.bugs_in_patch +
                self.bugs_in_verify + self.bugs_done + self.bugs_escalated)
    
    @property
    def completion_rate(self) -> float:
        """Percentage of bugs that are complete."""
        if self.total_bugs == 0:
            return 0
        return self.bugs_done / self.total_bugs


@dataclass
class AgentMetrics:
    """Metrics about agent performance."""
    agent_id: str
    agent_type: str
    tokens_in: int
    tokens_out: int
    processing_time: float
    success_rate: float


@dataclass
class BugMetrics:
    """Metrics about a specific bug."""
    bug_id: str
    current_phase: str
    time_in_system: int
    phase_transitions: List[Dict[str, Any]]
    severity: int
    file_path: Optional[str] = None


class MetricsCollector:
    """Collects and stores system metrics."""
    
    def __init__(self, storage_path: str = "metrics"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True, parents=True)
        
        self.current_run_id = int(time.time())
        self.run_path = self.storage_path / f"run_{self.current_run_id}"
        self.run_path.mkdir(exist_ok=True)
        
        self.tick_metrics: List[TickMetrics] = []
        self.agent_metrics: Dict[str, List[AgentMetrics]] = {}
        self.bug_metrics: Dict[str, BugMetrics] = {}
        self.comprehensive_metrics: Optional[ComprehensiveMetrics] = None
        
        # Performance summary
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.total_ticks = 0
        self.bugs_resolved = 0
        self.bugs_escalated = 0
        
        # General metrics storage
        self.general_metrics: Dict[str, Union[int, float, List]] = {}
    
    def record_metric(self, name: str, value: Union[int, float]) -> None:
        """Record a general metric value.
        
        Args:
            name: Metric name
            value: Metric value
        """
        if name not in self.general_metrics:
            self.general_metrics[name] = []
        
        if isinstance(self.general_metrics[name], list):
            self.general_metrics[name].append({
                'value': value,
                'timestamp': time.time() - self.start_time
            })
        else:
            # Convert to list if it was a single value
            old_value = self.general_metrics[name]
            self.general_metrics[name] = [
                {'value': old_value, 'timestamp': 0},
                {'value': value, 'timestamp': time.time() - self.start_time}
            ]
    
    def get_metric(self, name: str) -> Optional[Union[int, float, List]]:
        """Get a metric value.
        
        Args:
            name: Metric name
            
        Returns:
            Metric value or None if not found
        """
        return self.general_metrics.get(name)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all general metrics.
        
        Returns:
            Dictionary of all metrics
        """
        return self.general_metrics.copy()

    def record_comprehensive_metrics(self, metrics: ComprehensiveMetrics):
        """Records the comprehensive self-assessment metrics."""
        self.comprehensive_metrics = metrics
        self._save_comprehensive_metrics()

    def _save_comprehensive_metrics(self):
        """Save comprehensive metrics to disk."""
        if self.comprehensive_metrics:
            data = asdict(self.comprehensive_metrics)
            with open(self.run_path / 'comprehensive_metrics.json', 'w') as f:
                json.dump(data, f, indent=2)
    
    def record_tick(self, engine) -> TickMetrics:
        """Record metrics for the current tick."""
        # Count bugs in each phase
        phase_counts = {phase: 0 for phase in Phase}
        for bug in engine.bugs:
            phase_counts[bug.phase] += 1
        
        metrics = TickMetrics(
            tick_number=engine.tick_no,
            timestamp=time.time() - self.start_time,
            free_agents=engine.free_agents,
            bugs_waiting=phase_counts[Phase.WAIT],
            bugs_in_repro=phase_counts[Phase.REPRO],
            bugs_in_patch=phase_counts[Phase.PATCH],
            bugs_in_verify=phase_counts[Phase.VERIFY],
            bugs_done=phase_counts[Phase.DONE],
            bugs_escalated=phase_counts[Phase.ESCALATE],
            entropy_bits=engine.monitor.g_bits if hasattr(engine.monitor, 'g_bits') else 0.0
        )
        
        self.tick_metrics.append(metrics)
        self.total_ticks = engine.tick_no
        
        # Update bug counts
        self.bugs_resolved = phase_counts[Phase.DONE]
        self.bugs_escalated = phase_counts[Phase.ESCALATE]
        
        # Save metrics periodically
        if engine.tick_no % 5 == 0:
            self._save_tick_metrics()
        
        return metrics
    
    def record_agent_activity(self, agent_id: str, agent_type: str,
                             tokens_in: int, tokens_out: int,
                             processing_time: float, success: bool) -> None:
        """Record metrics for an agent's activity."""
        if agent_id not in self.agent_metrics:
            self.agent_metrics[agent_id] = []
        
        # Calculate success rate
        prev_metrics = self.agent_metrics[agent_id]
        if prev_metrics:
            success_rate = (prev_metrics[-1].success_rate * len(prev_metrics) + int(success)) / (len(prev_metrics) + 1)
        else:
            success_rate = float(success)
        
        metrics = AgentMetrics(
            agent_id=agent_id,
            agent_type=agent_type,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            processing_time=processing_time,
            success_rate=success_rate
        )
        
        self.agent_metrics[agent_id].append(metrics)
        
        # Save metrics periodically
        if len(self.agent_metrics[agent_id]) % 10 == 0:
            self._save_agent_metrics()
    
    def update_bug_metrics(self, bug_id: str, phase: Phase,
                          time_in_system: int, severity: int,
                          file_path: Optional[str] = None) -> None:
        """Update metrics for a specific bug."""
        timestamp = time.time() - self.start_time
        
        if bug_id in self.bug_metrics:
            # Update existing bug metrics
            bug_metrics = self.bug_metrics[bug_id]
            bug_metrics.current_phase = phase.name
            bug_metrics.time_in_system = time_in_system
            
            # Record phase transition if changed
            if bug_metrics.current_phase != phase.name:
                bug_metrics.phase_transitions.append({
                    'from': bug_metrics.current_phase,
                    'to': phase.name,
                    'time': timestamp,
                    'tick': self.total_ticks
                })
        else:
            # Create new bug metrics
            self.bug_metrics[bug_id] = BugMetrics(
                bug_id=bug_id,
                current_phase=phase.name,
                time_in_system=time_in_system,
                phase_transitions=[{
                    'from': 'CREATED',
                    'to': phase.name,
                    'time': timestamp,
                    'tick': self.total_ticks
                }],
                severity=severity,
                file_path=file_path
            )
        
        # Save bug metrics
        self._save_bug_metrics()
    
    def finalize_run(self) -> Dict[str, Any]:
        """Finalize the metrics collection and return summary."""
        self.end_time = time.time()
        
        # Calculate summary metrics
        total_time = self.end_time - self.start_time
        bugs_total = len(self.bug_metrics)
        success_rate = self.bugs_resolved / bugs_total if bugs_total > 0 else 0
        
        summary = {
            'run_id': self.current_run_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_time_seconds': total_time,
            'total_ticks': self.total_ticks,
            'bugs_total': bugs_total,
            'bugs_resolved': self.bugs_resolved,
            'bugs_escalated': self.bugs_escalated,
            'success_rate': success_rate
        }
        
        # Calculate agent performance metrics
        agent_summaries = {}
        for agent_id, metrics in self.agent_metrics.items():
            if not metrics:
                continue
                
            total_tokens_in = sum(m.tokens_in for m in metrics)
            total_tokens_out = sum(m.tokens_out for m in metrics)
            avg_time = np.mean([m.processing_time for m in metrics])
            success_rate = metrics[-1].success_rate if metrics else 0
            
            agent_summaries[agent_id] = {
                'total_activities': len(metrics),
                'total_tokens_in': total_tokens_in,
                'total_tokens_out': total_tokens_out,
                'avg_processing_time': avg_time,
                'success_rate': success_rate
            }
        
        summary['agent_summaries'] = agent_summaries
        
        # Save summary
        with open(self.run_path / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def _save_tick_metrics(self) -> None:
        """Save tick metrics to disk."""
        data = [asdict(m) for m in self.tick_metrics]
        with open(self.run_path / 'tick_metrics.json', 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_agent_metrics(self) -> None:
        """Save agent metrics to disk."""
        data = {
            agent_id: [asdict(m) for m in metrics]
            for agent_id, metrics in self.agent_metrics.items()
        }
        with open(self.run_path / 'agent_metrics.json', 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_bug_metrics(self) -> None:
        """Save bug metrics to disk."""
        data = {bug_id: asdict(metrics) for bug_id, metrics in self.bug_metrics.items()}
        with open(self.run_path / 'bug_metrics.json', 'w') as f:
            json.dump(data, f, indent=2)
