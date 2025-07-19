import logging
from .router import Router
from .roles import OBSERVER_PROMPT, ANALYST_PROMPT, VERIFIER_PROMPT
from .response_cache import get_response_cache
from .llm_config import get_agent_config, get_provider_config
from ..providers.factory import get_provider

logger = logging.getLogger(__name__)

class MetaAgent:
    def __init__(self, engine):
        self.engine = engine
        self.router = Router(engine)
        self.cache = get_response_cache()

    def get_agent_provider(self, agent_name):
        agent_config = get_agent_config(agent_name)
        provider_name = agent_config.get('provider')
        provider_config = get_provider_config(provider_name)
        return get_provider(provider_name, **provider_config)

    async def run_observer(self, goal_json):
        prompt = OBSERVER_PROMPT.format(goal_json=goal_json)
        provider = self.get_agent_provider('Observer')
        response = await provider.generate(prompt)
        return response.content

    async def run_analyst(self, observer_summary, diff):
        prompt = ANALYST_PROMPT.format(observer_summary=observer_summary, diff=diff)
        provider = self.get_agent_provider('Analyst')
        response = await provider.generate(prompt)
        return response.content

    async def run_verifier(self, patch_diff, apply_ok):
        prompt = VERIFIER_PROMPT.format(patch_diff=patch_diff, apply_ok=apply_ok)
        provider = self.get_agent_provider('Verifier')
        response = await provider.generate(prompt)
        return response.content

    def run_repair(self, task):
        from ..tooling.repair import PatcherAgent
        patcher = PatcherAgent()
        return patcher.execute_repair(task)
