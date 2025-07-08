"""
Response Caching for Deterministic LLM Interactions.

This module provides a caching mechanism to ensure that for a given
configuration, the Triangulum system's interactions with LLMs are
perfectly reproducible, thus preserving its deterministic guarantees.
"""

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from ..providers.base import LLMResponse

# Path to the SQLite database for caching
CACHE_DB_PATH = Path("triangulum_data/llm_response_cache.db")

class ResponseCache:
    """
    A persistent cache for LLM responses to enforce determinism.

    The cache keys are generated from a hash of the agent's role,
    the model identifier, and the prompt content.
    """

    def __init__(self, db_path: Union[str, Path] = CACHE_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True, parents=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initializes the SQLite database and table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS response_cache (
                request_hash TEXT PRIMARY KEY,
                response_data TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()

    def _create_hash(
        self, agent_name: str, model_id: str, prompt: Union[str, List[Dict[str, str]]]
    ) -> str:
        """Creates a unique SHA-256 hash for a given request."""
        # Serialize the prompt to a consistent JSON string
        if isinstance(prompt, list):
            prompt_str = json.dumps(prompt, sort_keys=True)
        else:
            prompt_str = prompt

        hash_content = f"{agent_name}:{model_id}:{prompt_str}"
        return hashlib.sha256(hash_content.encode("utf-8")).hexdigest()

    def get(
        self, agent_name: str, model_id: str, prompt: Union[str, List[Dict[str, str]]]
    ) -> Optional[LLMResponse]:
        """
        Retrieve a cached LLMResponse.

        Args:
            agent_name: The name of the agent making the request.
            model_id: The identifier of the model being used.
            prompt: The prompt being sent.

        Returns:
            A cached LLMResponse if found, otherwise None.
        """
        request_hash = self._create_hash(agent_name, model_id, prompt)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response_data FROM response_cache WHERE request_hash = ?",
                (request_hash,),
            )
            row = cursor.fetchone()

        if row:
            response_data = json.loads(row[0])
            return LLMResponse(**response_data)
        
        return None

    def put(
        self,
        agent_name: str,
        model_id: str,
        prompt: Union[str, List[Dict[str, str]]],
        response: LLMResponse,
    ) -> None:
        """
        Store an LLMResponse in the cache.

        Args:
            agent_name: The name of the agent.
            model_id: The identifier of the model.
            prompt: The prompt that was sent.
            response: The LLMResponse object to cache.
        """
        request_hash = self._create_hash(agent_name, model_id, prompt)
        
        # Create a serializable version of the response
        response_dict = {
            "content": response.content,
            "model": response.model,
            "cost": response.cost,
            "latency": response.latency,
            "tokens_used": response.tokens_used,
            # raw_response is not included to save space and avoid complexity
        }
        response_data = json.dumps(response_dict)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO response_cache (request_hash, response_data) VALUES (?, ?)",
                (request_hash, response_data),
            )
            conn.commit()

# Global instance of the cache
_global_cache = None

def get_response_cache() -> ResponseCache:
    """Returns a singleton instance of the ResponseCache."""
    global _global_cache
    if _global_cache is None:
        _global_cache = ResponseCache()
    return _global_cache
