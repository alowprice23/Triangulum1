"""
Router module for routing tasks to appropriate agents in the Triangulum system.
"""

class Router:
    """
    The Router is responsible for analyzing task descriptions and determining
    which specialized agent is best suited to handle the task. It uses simple
    keyword matching and heuristics to make routing decisions.
    """

    def __init__(self, engine):
        """
        Initialize the Router with a reference to the core engine.

        Args:
            engine: The core Triangulum engine
        """
        self.engine = engine
        
        # Define keyword mappings for different agent types
        self._keyword_mappings = {
            'CODE_ANALYZER': ['analyze', 'analysis', 'review', 'evaluate', 'assess', 'inspect', 'examine'],
            'BUG_FIXER': ['fix', 'repair', 'resolve', 'correct', 'debug', 'bug', 'error', 'issue'],
            'REFACTORER': ['refactor', 'restructure', 'reorganize', 'rewrite', 'clean', 'improve', 'maintainability'],
        }

    def route(self, task):
        """
        Analyze the task description and determine which agent should handle it.

        Args:
            task: The task description to analyze

        Returns:
            The ID of the agent that should handle the task
        """
        task_lower = task.lower()
        
        # Check each agent type for keyword matches
        for agent_id, keywords in self._keyword_mappings.items():
            for keyword in keywords:
                if keyword.lower() in task_lower:
                    return agent_id
        
        # If no matches, return the default agent
        return "GENERAL_AGENT"

    def add_keyword_mapping(self, agent_id, keywords):
        """
        Add or update the keyword mappings for an agent.

        Args:
            agent_id: The ID of the agent
            keywords: A list of keywords that should route to this agent
        """
        self._keyword_mappings[agent_id] = keywords

    def get_all_agent_types(self):
        """
        Get a list of all agent types known to the router.

        Returns:
            A list of agent IDs
        """
        return list(self._keyword_mappings.keys()) + ["GENERAL_AGENT"]
