import numpy as np

class TriangulumOptimizer:
    """
    Optimizes Triangulum system parameters based on performance history.
    """
    def __init__(self):
        self.parameter_bounds = {
            'timer_multiplier': (0.5, 2.0),
            'entropy_threshold': (1.0, 10.0),
            'agent_capacity': (6, 15),
        }
        self.exploration_rate = 0.1

    def suggest_parameters(self, performance_history: list, current_params: dict) -> dict:
        """
        Suggests optimal parameters based on performance history.
        """
        if len(performance_history) < 5:
            return self._explore_parameters(current_params)
            
        sorted_history = sorted(
            performance_history,
            key=lambda x: self._calculate_reward(x['metrics']),
            reverse=True
        )
        
        top_params = sorted_history[0]['parameters']
        
        if np.random.random() < self.exploration_rate:
            return self._explore_parameters(current_params)
        else:
            return self._exploit_parameters(top_params)

    def _calculate_reward(self, metrics: dict) -> float:
        """
        Calculates a reward score from a metrics dictionary.
        """
        reward = 0
        if 'success_rate' in metrics:
            reward += 50 * metrics['success_rate']
        if 'time_to_resolution' in metrics:
            time_factor = 1 - (metrics['time_to_resolution'] / 60)
            reward += 30 * time_factor
        if 'resource_efficiency' in metrics:
            reward += 20 * metrics['resource_efficiency']
        return reward

    def _explore_parameters(self, current_params: dict) -> dict:
        """
        Generates new parameters with random exploration.
        """
        new_params = {}
        for param, bounds in self.parameter_bounds.items():
            if bounds:
                new_params[param] = np.random.uniform(bounds[0], bounds[1])
        return new_params
        
    def _exploit_parameters(self, base_params: dict) -> dict:
        """
        Exploits with small variations around base parameters.
        """
        new_params = {}
        for param, value in base_params.items():
            bounds = self.parameter_bounds.get(param)
            if bounds:
                adjustment = (bounds[1] - bounds[0]) * 0.1
                new_value = value + np.random.uniform(-adjustment, adjustment)
                new_params[param] = max(bounds[0], min(bounds[1], new_value))
            else:
                new_params[param] = value
        return new_params
