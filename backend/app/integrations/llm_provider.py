"""LLM Provider abstraction for provider-independent model execution."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class ModelAvailabilityStatus(str, Enum):
    AVAILABLE = "available"
    MODEL_NOT_FOUND = "model_not_found"
    PROVIDER_UNAVAILABLE = "provider_unavailable"


class ToolCall(BaseModel):
    """Represents a structured tool invocation requested by the model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class LLMMessage(BaseModel):
    """Represents a single conversational turn in the LLM chat history."""

    role: str  # "system", "user", "assistant", "tool"
    content: Optional[str] = ""
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

    def to_provider_dict(self) -> Dict[str, Any]:
        """Converts message to standard dictionary representation."""
        data: Dict[str, Any] = {"role": self.role, "content": self.content or ""}
        if self.tool_calls:
            data["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": tc.arguments},
                }
                for tc in self.tool_calls
            ]
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.name:
            data["name"] = self.name
        return data


class LLMResponse(BaseModel):
    """Encapsulates the model's generation result, including any requested tool calls."""

    content: Optional[str] = ""
    model: str
    provider: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    usage: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class BaseLLMProvider(ABC):
    """Abstract interface defining the contract for any LLM inference provider."""

    provider_name: str

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider daemon / service is reachable."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """List locally available models from the provider."""
        pass

    @abstractmethod
    async def check_model_status(self, model: Optional[str] = None) -> ModelAvailabilityStatus:
        """Determines whether the provider is up and whether the specific model is installed."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Generate a raw text completion for the provided prompt."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Execute a multi-turn chat completion with optional structured tool definitions."""
        pass
