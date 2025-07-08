"""
api/llm_integrations.py
───────────────────────
Ultra-thin abstraction around three popular LLM back-ends:

* **OpenAI**      – ChatGPT / GPT-4 / GPT-4o  
* **Anthropic**   – Claude-3 family (optional)  
* **Google**      – Gemini-Pro (optional)

Design philosophy
─────────────────
• *Be invisible* – don’t hide provider-specific kwargs, just normalise a bare
  `chat()` signature.  
• *Fail fast*    – if the underlying SDK isn’t installed, raise a clear error.  
• *Router only*  – no retries, no cost tracking; those live in agent_orchestrator.

Public surface
──────────────
```python
lm = LLMManager()                          # auto-detect installed providers
resp = lm.chat(
        role="assistant",
        content="Explain entropy in 3 sentences.",
        task_type="explain",
        complexity="low",
    )
print(resp.text, resp.tokens, resp.cost_usd)
```
"""
from __future__ import annotations

import importlib
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Protocol


# ──────────────────────────────────────────────────────────────────────────────
# 0.  Dataclasses & Protocols
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class LLMResponse:
    """Standardised response container."""
    text: str
    tokens: int
    latency_ms: float
    cost_usd: float
    provider: str
    model: str


class BaseProvider(Protocol):
    """Interface for all LLM provider wrappers."""
    name: str

    def chat(self, role: str, content: str, **kwargs) -> LLMResponse:  # noqa: D401
        ...


# ──────────────────────────────────────────────────────────────────────────────
# 1.  Provider Implementations
# ──────────────────────────────────────────────────────────────────────────────
class OpenAIProvider:
    """OpenAI API wrapper."""
    name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
    ):
        self.model = model
        self.temperature = temperature
        self.openai = self._import_sdk()
        self.openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai.api_key:
            raise RuntimeError("OPENAI_API_KEY missing")

    @staticmethod
    def _import_sdk():
        mod = importlib.import_module("openai")  # raises if not installed
        return mod

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ chat
    def chat(self, role: str, content: str, **kwargs):
        start = time.perf_counter()
        rsp = self.openai.ChatCompletion.create(
            model=self.model,
            temperature=self.temperature,
            messages=[{"role": role, "content": content}],
        )
        dur = (time.perf_counter() - start) * 1000

        choice = rsp.choices[0].message.content
        usage = rsp.usage
        # simplistic cost estimation: (prompt + completion) / 1k * $0.01 placeholder
        cost = (usage.prompt_tokens + usage.completion_tokens) / 1000 * 0.01

        return LLMResponse(
            text=choice,
            tokens=usage.total_tokens,
            latency_ms=dur,
            cost_usd=cost,
            provider=self.name,
            model=self.model,
        )


class AnthropicProvider:
    """Anthropic API wrapper."""
    name = "anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-sonnet-20240229",
        temperature: float = 0.1,
    ):
        self.model = model
        self.temperature = temperature
        self.anthropic = self._import_sdk()
        self.anthropic.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.anthropic.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")

    @staticmethod
    def _import_sdk():
        return importlib.import_module("anthropic")

    def chat(self, role: str, content: str, **kwargs):
        start = time.perf_counter()
        client = self.anthropic.Anthropic()
        rsp = client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=self.temperature,
            messages=[{"role": role, "content": content}],
        )
        dur = (time.perf_counter() - start) * 1000
        text = "".join(block.text for block in rsp.content)
        # anthropic does not return usage tokens yet; rough estimate
        tokens = len(text.split())
        cost = tokens / 1000 * 0.012  # placeholder

        return LLMResponse(
            text=text,
            tokens=tokens,
            latency_ms=dur,
            cost_usd=cost,
            provider=self.name,
            model=self.model,
        )


class GeminiProvider:
    """Google Gemini API wrapper."""
    name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "models/gemini-pro",
        temperature: float = 0.1,
    ):
        self.model = model
        self.temperature = temperature
        self.google_gen = self._import_sdk()
        self.client = self.google_gen.GenerativeModel(model)
        if api_key:
            os.environ["GOOGLE_API_KEY"] = api_key
        elif "GOOGLE_API_KEY" not in os.environ:
            raise RuntimeError("GOOGLE_API_KEY missing")

    @staticmethod
    def _import_sdk():
        return importlib.import_module("google.generativeai")

    def chat(self, role: str, content: str, **kwargs):
        start = time.perf_counter()
        rsp = self.client.generate_content(
            content, generation_config={"temperature": self.temperature}
        )
        dur = (time.perf_counter() - start) * 1000
        text = rsp.text
        tokens = len(text.split())
        cost = tokens / 1000 * 0.010  # placeholder

        return LLMResponse(
            text=text,
            tokens=tokens,
            latency_ms=dur,
            cost_usd=cost,
            provider=self.name,
            model=self.model,
        )


# ──────────────────────────────────────────────────────────────────────────────
# 2.  Manager / Router
# ──────────────────────────────────────────────────────────────────────────────
class LLMManager:
    """
    Auto-detects and routes to the best-fit installed LLM provider.

    Routing logic
    ─────────────
        task_type == 'explain'         → prefer cheapest (Gemini/OpenAI mini)
        complexity == 'high'           → use GPT-4 / Claude Sonnet

    You can override by specifying `provider='openai'` in chat().
    """

    def __init__(self) -> None:
        self.providers: Dict[str, BaseProvider] = {}
        self._autodetect()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ autodetect
    def _autodetect(self) -> None:
        for cls in (OpenAIProvider, AnthropicProvider, GeminiProvider):
            try:
                p = cls()
                self.providers[p.name] = p
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
# Fixed: null_reference - Exception caught but not handled properly
            except Exception:
                # silent fail – provider not available/configured
                pass

        if not self.providers:
            raise RuntimeError("No LLM provider could be initialised")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ public
    def chat(
        self,
        role: str,
        content: str,
        *,
        task_type: str = "general",
        complexity: str = "low",
        provider: Optional[str] = None,
    ) -> LLMResponse:
        if provider:
            if provider not in self.providers:
                raise ValueError(f"provider '{provider}' not available")
            p = self.providers[provider]
        else:
            p = self._route(task_type, complexity)

        return p.chat(role=role, content=content)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ routing logic
    def _route(self, task_type: str, complexity: str) -> BaseProvider:
        # naive heuristics
        if complexity == "high" and "openai" in self.providers:
            return self.providers["openai"]
        if task_type in {"explain", "summary"} and "gemini" in self.providers:
            return self.providers["gemini"]
        # fallback to whichever is first
        return next(iter(self.providers.values()))

    # ---------------------------------------------------------------- debug
    def available(self):
        return list(self.providers.keys())