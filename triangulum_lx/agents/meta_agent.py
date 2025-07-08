import logging
import uuid
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Union

from triangulum_lx.agents.message import AgentMessage, MessageType, ConfidenceLevel
from triangulum_lx.agents.message_bus import MessageBus

logger = logging.getLogger(__name__)

class MetaAgentState(Enum):
    IDLE = auto()
    DECOMPOSING = auto()
    DISPATCHING = auto()
    WAITING = auto()
    SYNTHESIZING = auto()
    RESPONDING = auto()

class MetaAgent:
    """
    Meta Agent - Orchestrates specialized agents for task execution.
    
    The MetaAgent is responsible for breaking down complex tasks into smaller sub-tasks,
    routing them to specialized agents, and synthesizing the results into a coherent response.
    With the new message protocol, it communicates with other agents through the message bus.
    """
    
    def __init__(self, engine, tooling, router, message_bus: Optional[MessageBus] = None):
        """
        Initialize the MetaAgent.
        
        Args:
            engine: Reference to the core engine
            tooling: Available tools for the agent
            router: Agent router for task routing
            message_bus: Message bus for agent communication (optional)
        """
        self.engine = engine
        self.tooling = tooling
        self.router = router
        self.message_bus = message_bus
        self.agent_id = f"meta_agent_{str(uuid.uuid4())[:8]}"
        
        self.state = MetaAgentState.IDLE
        self.current_task = None
        self.current_conversation_id = None
        self.sub_tasks = []
        self.task_results = {}
        
        # Register with message bus if provided
        if self.message_bus:
            self.message_bus.subscribe(
                agent_id=self.agent_id,
                callback=self._handle_message,
                message_types=None  # Subscribe to all message types
            )
            logger.debug(f"MetaAgent {self.agent_id} registered with message bus")

    def execute_task(self, task):
        """
        The main entry point for the MetaAgent, invoked by the core engine.
        
        Args:
            task: Task to execute
        """
        if self.state != MetaAgentState.IDLE:
            raise Exception("MetaAgent is not idle, cannot accept new task.")
        
        logger.info(f"MetaAgent received task: {task}")
        self.current_task = task
        self.current_conversation_id = str(uuid.uuid4())
        self.state = MetaAgentState.DECOMPOSING
        
        # If message bus is available, create a task message
        if self.message_bus:
            task_message = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                content={"task": task},
                sender="engine",
                receiver=self.agent_id,
                conversation_id=self.current_conversation_id
            )
            # Handle the message directly rather than publishing it
            self._handle_message(task_message)
        else:
            # Legacy behavior if no message bus
            self._decompose_task()

    def _handle_message(self, message: AgentMessage):
        """
        Handle incoming messages from the message bus.
        
        Args:
            message: Message to handle
        """
        logger.debug(f"MetaAgent received message: {message.message_type} from {message.sender}")
        
        if message.message_type == MessageType.TASK_REQUEST:
            if self.state != MetaAgentState.IDLE and message.conversation_id != self.current_conversation_id:
                # Can't accept a new task right now
                self._send_error_message(
                    message,
                    "MetaAgent is busy, cannot accept new task.",
                    receiver=message.sender
                )
                return
            
            # Start a new task
            self.current_task = message.content.get("task")
            self.current_conversation_id = message.conversation_id
            self.state = MetaAgentState.DECOMPOSING
            self._decompose_task()
            
        elif message.message_type == MessageType.TASK_RESULT:
            # Handle results from sub-tasks
            task_id = message.content.get("task_id")
            result = message.content.get("result")
            if task_id is not None and result is not None:
                self.report_result(task_id, result)
                
        elif message.message_type == MessageType.ERROR:
            # Handle error messages
            logger.error(f"Error from {message.sender}: {message.content.get('error')}")
            # Could implement recovery logic here
    
    def _send_message(self, message_type: MessageType, content: Dict[str, Any], 
                     receiver: Optional[str] = None, 
                     confidence: Optional[float] = None):
        """
        Send a message via the message bus.
        
        Args:
            message_type: Type of message to send
            content: Message content
            receiver: Message recipient (optional)
            confidence: Confidence level (optional)
        """
        if not self.message_bus:
            logger.warning("No message bus available, message not sent")
            return
        
        message = AgentMessage(
            message_type=message_type,
            content=content,
            sender=self.agent_id,
            receiver=receiver,
            conversation_id=self.current_conversation_id,
            confidence=confidence
        )
        
        self.message_bus.publish(message)
    
    def _send_error_message(self, original_message: AgentMessage, error_text: str, receiver: Optional[str] = None):
        """
        Send an error message in response to another message.
        
        Args:
            original_message: Message that triggered the error
            error_text: Error description
            receiver: Message recipient (optional)
        """
        if not self.message_bus:
            logger.warning(f"No message bus available, error not sent: {error_text}")
            return
            
        error_message = original_message.create_response(
            message_type=MessageType.ERROR,
            content={"error": error_text, "original_message_type": original_message.message_type},
            confidence=None,
            metadata={"severity": "high"}
        )
        
        if receiver:
            error_message.receiver = receiver
            
        self.message_bus.publish(error_message)
        
    def _decompose_task(self):
        """
        Decomposes the current task into a set of sub-tasks.
        This is a placeholder for a more sophisticated decomposition logic.
        """
        logger.info("Decomposing task...")
        # In a real implementation, this would use an LLM or a rule-based system
        # to break down the task. For now, we'll create a simple sub-task.
        self.sub_tasks = [f"Sub-task for: {self.current_task}"]
        self.state = MetaAgentState.DISPATCHING
        
        # Send status message if message bus is available
        if self.message_bus:
            self._send_message(
                message_type=MessageType.STATUS,
                content={
                    "status": "task_decomposed",
                    "sub_tasks_count": len(self.sub_tasks)
                },
                receiver="engine"
            )
        
        self._dispatch_tasks()

    def _dispatch_tasks(self):
        """
        Dispatches the sub-tasks to the appropriate specialized agents.
        """
        logger.info("Dispatching sub-tasks...")
        for i, sub_task in enumerate(self.sub_tasks):
            # Use the router to find the best agent for the task
            agent_role = self.router.route(sub_task)
            logger.info(f"Routing sub-task '{sub_task}' to {agent_role}")
            
            if self.message_bus:
                # Send the task via message bus
                self._send_message(
                    message_type=MessageType.TASK_REQUEST,
                    content={
                        "task": sub_task,
                        "task_id": i,
                        "agent_role": agent_role
                    },
                    receiver=agent_role
                )
            else:
                # Legacy behavior - directly execute the sub-task
                self._execute_sub_task(i, sub_task, agent_role)

        self.state = MetaAgentState.WAITING

    def _execute_sub_task(self, task_id, sub_task, agent_role):
        """
        A placeholder for the actual execution of a sub-task by a specialized agent.
        
        Args:
            task_id: ID of the sub-task
            sub_task: Sub-task description
            agent_role: Role of the agent to execute the task
        """
        logger.info(f"Executing sub-task {task_id} with {agent_role}: {sub_task}")
        # Simulate a result
        result = f"Result for sub-task {task_id}"
        self.report_result(task_id, result)

    def report_result(self, task_id, result):
        """
        Called by specialized agents to report the result of a sub-task.
        
        Args:
            task_id: ID of the sub-task
            result: Result of the sub-task
        """
        logger.info(f"Received result for sub-task {task_id}: {result}")
        self.task_results[task_id] = result

        # Check if all tasks are complete
        if len(self.task_results) == len(self.sub_tasks):
            self.state = MetaAgentState.SYNTHESIZING
            self._synthesize_results()

    def _synthesize_results(self):
        """
        Synthesizes the results from all sub-tasks into a final response.
        """
        logger.info("Synthesizing results...")
        final_response = "\n".join(self.task_results.values())
        self.state = MetaAgentState.RESPONDING
        
        # Send the synthesized results via message bus if available
        if self.message_bus:
            self._send_message(
                message_type=MessageType.TASK_RESULT,
                content={
                    "task": self.current_task,
                    "result": final_response,
                    "sub_results": self.task_results
                },
                receiver="engine",
                confidence=ConfidenceLevel.HIGH.value
            )
        
        self._respond_to_engine(final_response)

    def _respond_to_engine(self, response):
        """
        Sends the final response back to the core engine.
        
        Args:
            response: Final response to send
        """
        logger.info(f"Responding to engine with: {response}")
        # In a real system, this would be a callback to the engine
        # self.engine.on_task_complete(self.current_task, response)
        self._reset()

    def _reset(self):
        """
        Resets the MetaAgent to its initial state.
        """
        self.state = MetaAgentState.IDLE
        self.current_task = None
        self.current_conversation_id = None
        self.sub_tasks = []
        self.task_results = {}
        logger.info("MetaAgent has been reset and is now idle.")
