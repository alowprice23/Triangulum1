"""
Model Capability Discovery for Triangulum LX.

This module provides automated discovery and tracking of LLM model capabilities,
allowing the system to dynamically adapt its behavior based on what each model
can actually do (streaming, tool use, context length, etc.).
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .base import LLMProvider, Tool
from .factory import get_provider_map

class CapabilityType(Enum):
    """Types of capabilities that can be discovered."""
    STREAMING = "streaming"
    TOOL_USE = "tool_use"
    VISION = "vision"
    CODE_EXECUTION = "code_execution"
    FUNCTION_CALLING = "function_calling"
    SYSTEM_MESSAGES = "system_messages"
    CONTEXT_LENGTH = "context_length"
    RESPONSE_FORMAT = "response_format"

@dataclass
class ModelCapability:
    """Represents a specific capability of a model."""
    capability_type: CapabilityType
    supported: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # How confident we are in this assessment
    last_tested: Optional[float] = None

@dataclass
class ModelProfile:
    """Complete capability profile for a model."""
    provider_name: str
    model_name: str
    capabilities: Dict[CapabilityType, ModelCapability] = field(default_factory=dict)
    max_context_length: Optional[int] = None
    cost_per_token: Optional[float] = None
    average_latency_ms: Optional[float] = None
    reasoning_power: Optional[float] = None
    last_updated: Optional[float] = None

class CapabilityTester:
    """Tests various capabilities of LLM models."""
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
    
    async def test_streaming(self) -> ModelCapability:
        """Test if the model supports streaming responses."""
        try:
            response = self.provider.generate(
                "Say 'test' in one word.",
                stream=True,
                max_tokens=10
            )
            
            # Check if we get an iterator
            if hasattr(response, '__iter__') and not isinstance(response, str):
                return ModelCapability(
                    capability_type=CapabilityType.STREAMING,
                    supported=True,
                    metadata={"test_passed": True},
                    last_tested=time.time()
                )
            else:
                return ModelCapability(
                    capability_type=CapabilityType.STREAMING,
                    supported=False,
                    metadata={"test_passed": False, "reason": "No iterator returned"},
                    last_tested=time.time()
                )
        except Exception as e:
            return ModelCapability(
                capability_type=CapabilityType.STREAMING,
                supported=False,
                metadata={"test_passed": False, "error": str(e)},
                confidence=0.8,
                last_tested=time.time()
            )
    
    async def test_tool_use(self) -> ModelCapability:
        """Test if the model supports tool/function calling."""
        try:
            test_tool = Tool(
                name="get_weather",
                description="Get the current weather in a location",
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "The city name"}
                    },
                    "required": ["location"]
                }
            )
            
            response = self.provider.generate_with_tools(
                "What's the weather like in San Francisco?",
                tools=[test_tool]
            )
            
            # Check if we get tool calls back
            if isinstance(response, list) and len(response) > 0:
                return ModelCapability(
                    capability_type=CapabilityType.TOOL_USE,
                    supported=True,
                    metadata={"test_passed": True, "tools_called": len(response)},
                    last_tested=time.time()
                )
            else:
                return ModelCapability(
                    capability_type=CapabilityType.TOOL_USE,
                    supported=False,
                    metadata={"test_passed": False, "reason": "No tool calls returned"},
                    confidence=0.9,
                    last_tested=time.time()
                )
        except Exception as e:
            return ModelCapability(
                capability_type=CapabilityType.TOOL_USE,
                supported=False,
                metadata={"test_passed": False, "error": str(e)},
                confidence=0.7,
                last_tested=time.time()
            )
    
    async def test_context_length(self) -> ModelCapability:
        """Estimate the maximum context length by testing progressively longer inputs."""
        base_prompt = "Repeat this number: "
        max_tested = 0
        
        # Test common context lengths
        test_lengths = [1000, 2000, 4000, 8000, 16000, 32000, 64000, 128000]
        
        for length in test_lengths:
            try:
                # Create a prompt of approximately the target length
                test_text = "A" * (length - len(base_prompt) - 100)  # Leave some buffer
                full_prompt = base_prompt + test_text
                
                response = self.provider.generate(
                    full_prompt,
                    max_tokens=10
                )
                
                max_tested = length
            except Exception:
                # If this length fails, the previous one was likely the max
                break
        
        return ModelCapability(
            capability_type=CapabilityType.CONTEXT_LENGTH,
            supported=True,
            metadata={
                "estimated_max_tokens": max_tested,
                "test_method": "progressive_testing"
            },
            confidence=0.8 if max_tested > 0 else 0.3,
            last_tested=time.time()
        )
    
    async def test_system_messages(self) -> ModelCapability:
        """Test if the model properly follows system messages."""
        try:
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Always end your responses with the word MARKER."},
                {"role": "user", "content": "Say hello."}
            ]
            
            response = self.provider.generate(messages, max_tokens=50)
            
            if "MARKER" in response.content:
                return ModelCapability(
                    capability_type=CapabilityType.SYSTEM_MESSAGES,
                    supported=True,
                    metadata={"test_passed": True, "marker_found": True},
                    last_tested=time.time()
                )
            else:
                return ModelCapability(
                    capability_type=CapabilityType.SYSTEM_MESSAGES,
                    supported=False,
                    metadata={"test_passed": False, "marker_found": False},
                    confidence=0.8,
                    last_tested=time.time()
                )
        except Exception as e:
            return ModelCapability(
                capability_type=CapabilityType.SYSTEM_MESSAGES,
                supported=False,
                metadata={"test_passed": False, "error": str(e)},
                confidence=0.5,
                last_tested=time.time()
            )

class CapabilityRegistry:
    """Registry for storing and retrieving model capability profiles."""
    
    def __init__(self):
        self.profiles: Dict[str, ModelProfile] = {}
    
    def get_profile(self, provider_name: str, model_name: str) -> Optional[ModelProfile]:
        """Get the capability profile for a specific model."""
        key = f"{provider_name}:{model_name}"
        return self.profiles.get(key)
    
    def save_profile(self, profile: ModelProfile) -> None:
        """Save a capability profile."""
        key = f"{profile.provider_name}:{profile.model_name}"
        profile.last_updated = time.time()
        self.profiles[key] = profile
    
    def has_capability(self, provider_name: str, model_name: str, 
                      capability: CapabilityType) -> bool:
        """Check if a model has a specific capability."""
        profile = self.get_profile(provider_name, model_name)
        if not profile:
            return False
        
        cap = profile.capabilities.get(capability)
        return cap.supported if cap else False
    
    def get_models_with_capability(self, capability: CapabilityType) -> List[str]:
        """Get all models that support a specific capability."""
        models = []
        for key, profile in self.profiles.items():
            if self.has_capability(profile.provider_name, profile.model_name, capability):
                models.append(key)
        return models
    
    def export_to_json(self) -> str:
        """Export all profiles to JSON format."""
        export_data = {}
        for key, profile in self.profiles.items():
            export_data[key] = {
                "provider_name": profile.provider_name,
                "model_name": profile.model_name,
                "capabilities": {
                    cap_type.value: {
                        "supported": cap.supported,
                        "metadata": cap.metadata,
                        "confidence": cap.confidence,
                        "last_tested": cap.last_tested
                    }
                    for cap_type, cap in profile.capabilities.items()
                },
                "max_context_length": profile.max_context_length,
                "cost_per_token": profile.cost_per_token,
                "average_latency_ms": profile.average_latency_ms,
                "reasoning_power": profile.reasoning_power,
                "last_updated": profile.last_updated
            }
        return json.dumps(export_data, indent=2)

class CapabilityDiscoveryService:
    """Service for automatically discovering model capabilities."""
    
    def __init__(self):
        self.registry = CapabilityRegistry()
    
    async def discover_all_capabilities(self, provider_name: str, model_name: str) -> ModelProfile:
        """Discover all capabilities for a specific model."""
        try:
            provider = get_provider_map().get(provider_name)
            if not provider:
                raise ValueError(f"Unknown provider: {provider_name}")
            
            provider_instance = provider(model=model_name)
            tester = CapabilityTester(provider_instance)
            
            profile = ModelProfile(
                provider_name=provider_name,
                model_name=model_name
            )
            
            # Run all capability tests
            tasks = [
                tester.test_streaming(),
                tester.test_tool_use(),
                tester.test_context_length(),
                tester.test_system_messages()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, ModelCapability):
                    profile.capabilities[result.capability_type] = result
                # Ignore exceptions for now
            
            self.registry.save_profile(profile)
            return profile
            
        except Exception as e:
            # Create a minimal profile with error information
            profile = ModelProfile(
                provider_name=provider_name,
                model_name=model_name
            )
            profile.capabilities[CapabilityType.STREAMING] = ModelCapability(
                capability_type=CapabilityType.STREAMING,
                supported=False,
                metadata={"discovery_error": str(e)},
                confidence=0.0
            )
            return profile
    
    async def discover_all_models(self) -> Dict[str, ModelProfile]:
        """Discover capabilities for all available models."""
        from ..agents.llm_config import LLM_CONFIG
        
        profiles = {}
        providers_config = LLM_CONFIG.get("providers", {})
        
        for provider_name, provider_info in providers_config.items():
            models = provider_info.get("models", {})
            for model_name in models.keys():
                try:
                    profile = await self.discover_all_capabilities(provider_name, model_name)
                    key = f"{provider_name}:{model_name}"
                    profiles[key] = profile
                except Exception as e:
                    print(f"Failed to discover capabilities for {provider_name}:{model_name}: {e}")
        
        return profiles

# Global capability registry instance
_capability_registry = CapabilityRegistry()

def get_capability_registry() -> CapabilityRegistry:
    """Get the global capability registry."""
    return _capability_registry
