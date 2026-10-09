"""Ollama local LLM provider implementation with tool-calling support and robust error handling."""

import json
import re
from typing import Any, Dict, List, Optional
import uuid
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


class OllamaTimeoutError(OllamaProviderError):
    """Raised when an Ollama HTTP request times out."""
    pass


class OllamaModelNotFoundError(OllamaProviderError):
    """Raised when the specified model is not downloaded in Ollama."""
    pass


class OllamaResponseError(OllamaProviderError):
    """Raised when Ollama returns an HTTP error or unexpected payload structure."""
    pass


def _strip_thinking_tags(text: str) -> str:
    """Strips any internal <think>...</think> chain-of-thought blocks if present."""
    if not text:
        return ""
    if "<think>" in text and "</think>" in text:
        return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text


class OllamaProvider(BaseLLMProvider):
    """Local LLM provider interfacing with Ollama over HTTP.

    Supports chat completions, tool definitions, tool-call responses,
    and granular availability status checking. Never exposes internal chain-of-thought
    thinking fields to the rest of the application.
    """

    provider_name: str = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.default_model = default_model or settings.OLLAMA_MODEL
        self.timeout = float(timeout if timeout is not None else settings.OLLAMA_TIMEOUT_SECONDS)
        self.transport = transport

    def _get_client(self, timeout: Optional[float] = None) -> httpx.AsyncClient:
        """Returns an AsyncClient instance configured with provider settings and optional transport."""
        return httpx.AsyncClient(
            timeout=timeout if timeout is not None else self.timeout,
            transport=self.transport,
        )

    async def is_available(self) -> bool:
        """Pings Ollama /api/tags to see if the local daemon is running."""
        try:
            async with self._get_client(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> List[str]:
        """Queries Ollama for currently pulled local models."""
        try:
            async with self._get_client(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception as e:
            logger.debug(f"Failed to query Ollama models: {e}")
        return []

    async def check_model_status(self, model: Optional[str] = None) -> ModelAvailabilityStatus:
        """Determines whether Ollama is reachable and whether the target model is present."""
        installed_models = await self.list_models()
        if not installed_models:
            # If list_models returned empty, check if daemon is even up
            if not await self.is_available():
                return ModelAvailabilityStatus.PROVIDER_UNAVAILABLE
            return ModelAvailabilityStatus.MODEL_NOT_FOUND

        target_model = model or self.default_model
        
        target_base = target_model.split(":")[0]
        for m in installed_models:
            m_base = m.split(":")[0]
            if m == target_model or m == f"{target_model}:latest" or f"{m}:latest" == target_model:
                return ModelAvailabilityStatus.AVAILABLE
            if m_base == target_base:
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

        logger.info("Ollama generate request started for model '%s'", target_model)

        try:
            async with self._get_client() as client:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                if res.status_code == 404:
                    logger.warning("Model '%s' not found in Ollama", target_model)
                    raise OllamaModelNotFoundError(f"Model '{target_model}' not found in Ollama.")
                if res.status_code != 200:
                    logger.warning("Ollama generate returned status %d", res.status_code)
                    raise OllamaResponseError(f"Ollama returned HTTP {res.status_code}: {res.text}")

                data = res.json()
                raw_content = data.get("response", "")
                clean_content = _strip_thinking_tags(raw_content)

                return LLMResponse(
                    content=clean_content,
                    model=target_model,
                    provider=self.provider_name,
                    usage={"eval_count": data.get("eval_count", 0)},
                )
        except httpx.ConnectError as e:
            logger.warning("Cannot connect to Ollama at %s: %s", self.base_url, e)
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}: {e}") from e
        except httpx.TimeoutException as e:
            logger.warning("Ollama generate timed out after %.1fs for model '%s'", self.timeout, target_model)
            raise OllamaTimeoutError(f"Ollama request timed out after {self.timeout}s.") from e
        except OllamaProviderError:
            raise
        except Exception as e:
            logger.warning("Ollama generate request failed: %s", e)
            raise OllamaResponseError(f"Ollama generation failed: {e}") from e

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

        # Serialize messages for Ollama API format
        formatted_messages: List[Dict[str, Any]] = []
        for m in messages:
            msg_dict: Dict[str, Any] = {"role": m.role, "content": m.content or ""}
            if m.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            if m.name:
                msg_dict["name"] = m.name
            formatted_messages.append(msg_dict)

        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": formatted_messages,
            "stream": False,
            "options": {"temperature": temperature},
        }

        if tools:
            payload["tools"] = tools

        logger.info(
            "Ollama chat turn started for model '%s' (messages=%d, tools=%d)",
            target_model,
            len(messages),
            len(tools) if tools else 0,
        )

        try:
            async with self._get_client() as client:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                if res.status_code == 404:
                    logger.warning("Model '%s' not found on Ollama server", target_model)
                    raise OllamaModelNotFoundError(f"Model '{target_model}' not found in Ollama.")
                if res.status_code != 200:
                    logger.warning("Ollama chat returned status %d", res.status_code)
                    raise OllamaResponseError(f"Ollama returned HTTP error {res.status_code}: {res.text}")

                try:
                    data = res.json()
                except Exception as e:
                    raise OllamaResponseError(f"Malformed JSON response from Ollama: {e}") from e

                if not isinstance(data, dict):
                    raise OllamaResponseError(f"Unexpected response type from Ollama: {type(data)}")

                msg = data.get("message")
                if not isinstance(msg, dict):
                    raise OllamaResponseError(f"Missing or malformed 'message' object in Ollama response: {data}")

                # Clean and sanitize content — strip any thinking tags if present
                raw_content = msg.get("content", "") or ""
                clean_content = _strip_thinking_tags(raw_content)

                # Parse structured tool calls
                raw_tool_calls = msg.get("tool_calls", [])
                parsed_tool_calls: List[ToolCall] = []

                if isinstance(raw_tool_calls, list):
                    for rtc in raw_tool_calls:
                        if not isinstance(rtc, dict):
                            continue
                        fn = rtc.get("function", {})
                        if not isinstance(fn, dict):
                            continue
                        fn_name = fn.get("name", "")
                        if not fn_name:
                            continue

                        fn_args = fn.get("arguments", {})
                        if isinstance(fn_args, str):
                            try:
                                fn_args = json.loads(fn_args)
                            except Exception:
                                fn_args = {}
                        elif not isinstance(fn_args, dict):
                            fn_args = {}

                        tc_id = rtc.get("id") or str(uuid.uuid4())
                        parsed_tool_calls.append(
                            ToolCall(
                                id=tc_id,
                                name=fn_name,
                                arguments=fn_args,
                            )
                        )

                eval_count = data.get("eval_count", 0)
                if parsed_tool_calls:
                    logger.info(
                        "Ollama response received: %d tool call(s) detected: %s (eval_count=%s)",
                        len(parsed_tool_calls),
                        [tc.name for tc in parsed_tool_calls],
                        eval_count,
                    )
                else:
                    logger.info(
                        "Ollama response received: text completion generated (eval_count=%s)",
                        eval_count,
                    )

                # Discard thinking field completely at the provider boundary!
                return LLMResponse(
                    content=clean_content,
                    model=target_model,
                    provider=self.provider_name,
                    tool_calls=parsed_tool_calls,
                    usage={"eval_count": eval_count},
                )

        except httpx.ConnectError as e:
            logger.warning("Connection to Ollama failed at %s: %s", self.base_url, e)
            raise OllamaConnectionError(f"Cannot connect to Ollama daemon at {self.base_url}. Ensure Ollama is running.") from e
        except httpx.TimeoutException as e:
            logger.warning("Ollama chat timed out after %.1fs for model '%s'", self.timeout, target_model)
            raise OllamaTimeoutError(f"Ollama request timed out after {self.timeout}s.") from e
        except OllamaProviderError:
            raise
        except Exception as e:
            logger.error("Unexpected error during Ollama chat: %s", e, exc_info=True)
            raise OllamaResponseError(f"Ollama chat failed: {e}") from e
