"""
Test Stubs for Triangulum Agentic System Testing

This module provides stub implementations of the agent classes for testing
the agentic system without requiring the full implementation. These stubs
simulate the interfaces of the real agent classes but with simplified behavior.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Set, Callable, Union
from enum import Enum
import uuid

from triangulum_lx.agents.message import AgentMessage, MessageType
from triangulum_lx.agents.enhanced_message_bus import EnhancedMessageBus
from triangulum_lx.monitoring.agentic_system_monitor import AgenticSystemMonitor, AgentActivityState

logger = logging.getLogger(__name__)


class BaseAgentStub:
    """Base agent stub with minimal functionality."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_type: str = "generic",
        message_bus: Optional[EnhancedMessageBus] = None,
        progress_reporting_level: str = "standard",
        system_monitor: Optional[AgenticSystemMonitor] = None
    ):
        """Initialize the agent stub."""
        self.agent_id = agent_id or f"{agent_type}_{uuid.uuid4().hex[:8]}"
        self.agent_type = agent_type
        self.message_bus = message_bus
        self.progress_reporting_level = progress_reporting_level
        self.system_monitor = system_monitor
        self.idle = True
        
        logger.debug(f"Initialized {self.agent_type} agent stub with ID {self.agent_id}")
        
    def is_idle(self) -> bool:
        """Return whether the agent is idle."""
        return self.idle
    
    def send_message(self, message: AgentMessage) -> str:
        """Send a message through the message bus."""
        if self.message_bus:
            return self.message_bus.publish(message)
        return ""
    
    def update_progress(
        self, 
        activity: str, 
        percent_complete: float,
        estimated_completion: Optional[float] = None
    ) -> None:
        """Update progress information."""
        if self.system_monitor:
            self.system_monitor.update_progress(
                agent_name=self.agent_id,
                activity=activity,
                percent_complete=percent_complete,
                estimated_completion=estimated_completion
            )
            
    def set_idle(self, is_idle: bool = True) -> None:
        """Set the agent's idle state."""
        self.idle = is_idle
        if self.system_monitor:
            state = AgentActivityState.IDLE if is_idle else AgentActivityState.BUSY
            self.system_monitor.set_agent_state(self.agent_id, state)


class BugDetectorAgent(BaseAgentStub):
    """Stub implementation of the Bug Detector Agent."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        message_bus: Optional[EnhancedMessageBus] = None,
        system_monitor: Optional[AgenticSystemMonitor] = None,
        progress_reporting_level: str = "standard"
    ):
        """Initialize the Bug Detector Agent stub."""
        super().__init__(
            agent_id=agent_id,
            agent_type="bug_detector",
            message_bus=message_bus,
            progress_reporting_level=progress_reporting_level,
            system_monitor=system_monitor
        )
    
    def detect_bugs_in_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Simulate detecting bugs in a file."""
        self.update_progress("Analyzing file", 50.0)
        time.sleep(0.5)  # Simulate work
        self.update_progress("Completing analysis", 100.0)
        
        # Return a simulated bug
        return [{
            "file": file_path,
            "line": 10,
            "description": "Simulated bug for testing",
            "severity": "medium"
        }]


class RelationshipAnalystAgent(BaseAgentStub):
    """Stub implementation of the Relationship Analyst Agent."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        message_bus: Optional[EnhancedMessageBus] = None,
        system_monitor: Optional[AgenticSystemMonitor] = None,
        progress_reporting_level: str = "standard"
    ):
        """Initialize the Relationship Analyst Agent stub."""
        super().__init__(
            agent_id=agent_id,
            agent_type="relationship_analyst",
            message_bus=message_bus,
            progress_reporting_level=progress_reporting_level,
            system_monitor=system_monitor
        )
    
    def analyze_relationships(self, path: str) -> Dict[str, Any]:
        """Simulate analyzing relationships."""
        self.update_progress("Starting relationship analysis", 10.0)
        time.sleep(0.5)  # Simulate work
        self.update_progress("Analyzing dependencies", 50.0)
        time.sleep(0.5)  # Simulate more work
        self.update_progress("Completing analysis", 100.0)
        
        # Return simulated relationship data
        return {
            "files_analyzed": 5,
            "relationships_found": 10,
            "central_files": ["main.py", "utils.py"]
        }


class VerificationAgent(BaseAgentStub):
    """Stub implementation of the Verification Agent."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        message_bus: Optional[EnhancedMessageBus] = None,
        system_monitor: Optional[AgenticSystemMonitor] = None,
        progress_reporting_level: str = "standard"
    ):
        """Initialize the Verification Agent stub."""
        super().__init__(
            agent_id=agent_id,
            agent_type="verification",
            message_bus=message_bus,
            progress_reporting_level=progress_reporting_level,
            system_monitor=system_monitor
        )
    
    def verify_fix(self, file_path: str) -> Dict[str, Any]:
        """Simulate verifying a fix."""
        self.update_progress("Starting verification", 10.0)
        time.sleep(0.5)  # Simulate work
        self.update_progress("Running tests", 50.0)
        time.sleep(0.5)  # Simulate more work
        self.update_progress("Completing verification", 100.0)
        
        # Return simulated verification result
        return {
            "verified": True,
            "confidence": 0.9,
            "tests_passed": 5,
            "tests_total": 5
        }


class PriorityAnalyzerAgent(BaseAgentStub):
    """Stub implementation of the Priority Analyzer Agent."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        message_bus: Optional[EnhancedMessageBus] = None,
        system_monitor: Optional[AgenticSystemMonitor] = None,
        progress_reporting_level: str = "standard"
    ):
        """Initialize the Priority Analyzer Agent stub."""
        super().__init__(
            agent_id=agent_id,
            agent_type="priority_analyzer",
            message_bus=message_bus,
            progress_reporting_level=progress_reporting_level,
            system_monitor=system_monitor
        )
    
    def analyze_priorities(self, bugs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simulate analyzing bug priorities."""
        self.update_progress("Analyzing bug priorities", 50.0)
        time.sleep(0.5)  # Simulate work
        self.update_progress("Completing priority analysis", 100.0)
        
        # Return the bugs with added priority
        for bug in bugs:
            bug["priority"] = "high" if bug.get("severity") == "critical" else "medium"
        
        return bugs


class OrchestratorAgent(BaseAgentStub):
    """Stub implementation of the Orchestrator Agent."""
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        message_bus: Optional[EnhancedMessageBus] = None,
        agents: Optional[Dict[str, BaseAgentStub]] = None,
        system_monitor: Optional[AgenticSystemMonitor] = None,
        progress_reporting_level: str = "standard",
        parallel_executor: Optional[Any] = None
    ):
        """Initialize the Orchestrator Agent stub."""
        super().__init__(
            agent_id=agent_id,
            agent_type="orchestrator",
            message_bus=message_bus,
            progress_reporting_level=progress_reporting_level,
            system_monitor=system_monitor
        )
        self.agents = agents or {}
        self.parallel_executor = parallel_executor
    
    def coordinate_analysis(self, path: str) -> Dict[str, Any]:
        """Simulate coordinating an analysis workflow."""
        self.update_progress("Starting analysis workflow", 10.0)
        time.sleep(0.5)  # Simulate work
        
        # Simulate using bug detector
        if "bug_detector" in self.agents:
            self.agents["bug_detector"].set_idle(False)
            self.update_progress("Running bug detection", 30.0)
            bugs = self.agents["bug_detector"].detect_bugs_in_file(path)
            self.agents["bug_detector"].set_idle(True)
        else:
            bugs = []
        
        # Simulate using relationship analyst
        if "relationship_analyst" in self.agents:
            self.agents["relationship_analyst"].set_idle(False)
            self.update_progress("Running relationship analysis", 60.0)
            relationships = self.agents["relationship_analyst"].analyze_relationships(path)
            self.agents["relationship_analyst"].set_idle(True)
        else:
            relationships = {}
        
        # Simulate using priority analyzer
        if "priority_analyzer" in self.agents and bugs:
            self.agents["priority_analyzer"].set_idle(False)
            self.update_progress("Analyzing priorities", 80.0)
            bugs = self.agents["priority_analyzer"].analyze_priorities(bugs)
            self.agents["priority_analyzer"].set_idle(True)
        
        self.update_progress("Completing workflow", 100.0)
        
        # Return simulated results
        return {
            "bugs": bugs,
            "relationships": relationships,
            "workflow_id": f"test-workflow-{uuid.uuid4().hex[:8]}"
        }
