"""Ollama local LLM provider implementation with tool-calling support."""

import json
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.integrations.llm_provider import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    ToolCall,
    ModelAvailabilityStatus,
)


class OllamaProviderError(Exception):
    """Base exception for Ollama provider errors."""
    pass


class OllamaConnectionError(OllamaProviderError):
    """Raised when the local Ollama server cannot be reached."""
    pass


class OllamaModelNotFoundError(OllamaProviderError):
    """Raised when the specified model is not downloaded in Ollama."""
    pass


class OllamaProvider(BaseLLMProvider):
    """Local LLM provider interfacing with Ollama over HTTP.

    Supports chat completions, tool definitions, tool-call responses,
    and granular availability status checking.
    """

    provider_name: str = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 45.0,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = default_model or settings.OLLAMA_MODEL
        self.timeout = timeout

    async def is_available(self) -> bool:
        """Pings Ollama /api/tags to see if the local daemon is running."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Queries Ollama for currently pulled local models."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.debug(f"Failed to query Ollama models: {e}")
        return []

    async def check_model_status(self, model: Optional[str] = None) -> ModelAvailabilityStatus:
        """Determines whether Ollama is reachable and whether the target model is present."""
        if not await self.is_available():
            return ModelAvailabilityStatus.PROVIDER_UNAVAILABLE

        target_model = model or self.default_model
        installed_models = await self.list_models()

        # Check exact match or base tag match (e.g. "llama3.2" matches "llama3.2:latest")
        for m in installed_models:
            if m == target_model or m.split(":")[0] == target_model.split(":")[0]:
                return ModelAvailabilityStatus.AVAILABLE

        return ModelAvailabilityStatus.MODEL_NOT_FOUND

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Call Ollama /api/generate endpoint."""
        target_model = model or self.default_model
        payload: Dict[str, Any] = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                if res.status_code == 404:
                    raise OllamaModelNotFoundError(f"Model '{target_model}' not found in Ollama.")
                res.raise_for_status()
                data = res.json()
                return LLMResponse(
                    content=data.get("response", ""),
                    model=target_model,
                    provider=self.provider_name,
                    usage={"eval_count": data.get("eval_count", 0)},
                )
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}") from e
        except OllamaProviderError:
            raise
        except Exception as e:
            logger.warning(f"Ollama generate request failed: {e}")
            raise OllamaProviderError(f"Ollama generation failed: {e}") from e

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Call Ollama /api/chat endpoint with optional tool definitions."""
        target_model = model or self.default_model

        # Serialize messages for Ollama API
        formatted_messages: List[Dict[str, Any]] = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role, "content": m.content or ""}
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        }
                    }
                    for tc in m.tool_calls
                ]
            formatted_messages.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                if res.status_code == 404:
                    raise OllamaModelNotFoundError(f"Model '{target_model}' not found in Ollama.")
                res.raise_for_status()
                data = res.json()

                msg = data.get("message", {})
                raw_tool_calls = msg.get("tool_calls", [])
                parsed_tool_calls: List[ToolCall] = []

                for rtc in raw_tool_calls:
                    fn = rtc.get("function", {})
                    fn_name = fn.get("name", "")
                    fn_args = fn.get("arguments", {})
                    if isinstance(fn_args, str):
                        try:
                            fn_args = json.loads(fn_args)
                        except Exception:
                            fn_args = {}
                    parsed_tool_calls.append(
                        ToolCall(name=fn_name, arguments=fn_args if isinstance(fn_args, dict) else {})
                    )

                return LLMResponse(
                    content=msg.get("content", ""),
                    model=target_model,
                    provider=self.provider_name,
                    tool_calls=parsed_tool_calls,
                    usage={"eval_count": data.get("eval_count", 0)},
                )
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}") from e
        except OllamaProviderError:
            raise
        except Exception as e:
            logger.warning(f"Ollama chat request failed: {e}")
            raise OllamaProviderError(f"Ollama chat failed: {e}") from e
