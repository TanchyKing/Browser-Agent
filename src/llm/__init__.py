"""LLM adapter interfaces for browser-agent decisions."""

from .adapters import (
    BaseLLMAdapter,
    LLMRequest,
    LLMResponse,
    MockLLMAdapter,
    ObservationDrivenMockLLMAdapter,
    OllamaAdapter,
    StaticJSONAdapter,
)
from .structured_output import (
    StructuredAction,
    observation_candidates,
    observation_grounded_schema,
    validate_structured_action,
)

__all__ = [
    "BaseLLMAdapter",
    "LLMRequest",
    "LLMResponse",
    "MockLLMAdapter",
    "ObservationDrivenMockLLMAdapter",
    "OllamaAdapter",
    "StaticJSONAdapter",
    "StructuredAction",
    "observation_candidates",
    "observation_grounded_schema",
    "validate_structured_action",
]
