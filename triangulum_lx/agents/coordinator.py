"""
Coordinator module for managing agent interactions in the Triangulum system.
"""

class Coordinator:
    """
    The Coordinator manages interactions between different specialized agents
    in the Triangulum system. It acts as a central hub that can dispatch tasks
    to appropriate agents and manage the flow of information between them.
    """

    def __init__(self, engine, agents):
        """
        Initialize the Coordinator with a reference to the core engine and a set of agents.

        Args:
            engine: The core Triangulum engine
            agents: A dictionary mapping agent IDs to agent instances
        """
        self.engine = engine
        self.agents = agents
        self.current_state = "IDLE"

    def dispatch_task(self, agent_id, task):
        """
        Dispatch a task to a specific agent.

        Args:
            agent_id: The ID of the agent to dispatch the task to
            task: The task to dispatch

        Raises:
            KeyError: If the specified agent doesn't exist
        """
        if agent_id not in self.agents:
            raise KeyError(f"Unknown agent: {agent_id}")
        
        self.agents[agent_id].execute_task(task)

    def register_agent(self, agent_id, agent):
        """
        Register a new agent with the coordinator.

        Args:
            agent_id: The ID to register the agent under
            agent: The agent instance to register
        """
        self.agents[agent_id] = agent

    def broadcast_message(self, message, exclude=None):
        """
        Broadcast a message to all agents except those in the exclude list.

        Args:
            message: The message to broadcast
            exclude: A list of agent IDs to exclude from the broadcast
        """
        exclude = exclude or []
        for agent_id, agent in self.agents.items():
            if agent_id not in exclude:
                agent.receive_message(message)
