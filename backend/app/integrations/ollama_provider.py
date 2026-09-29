"""Ollama local LLM provider implementation."""

from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger
from app.integrations.llm_provider import BaseLLMProvider, LLMMessage, LLMResponse


class OllamaProvider(BaseLLMProvider):
    """Local LLM provider interfacing with Ollama over HTTP.

    Runs entirely locally with zero external API fees.
    Gracefully handles states where the Ollama daemon is offline or models are not yet pulled.
    """

    provider_name: str = "ollama"

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: float = 30.0,
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
                res.raise_for_status()
                data = res.json()
                return LLMResponse(
                    content=data.get("response", ""),
                    model=target_model,
                    provider=self.provider_name,
                    usage={"eval_count": data.get("eval_count", 0)},
                )
        except Exception as e:
            logger.warning(f"Ollama generate request failed: {e}")
            raise RuntimeError(f"Ollama generation failed: {e}") from e

    async def chat(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        """Call Ollama /api/chat endpoint."""
        target_model = model or self.default_model
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": temperature},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                res.raise_for_status()
                data = res.json()
                msg = data.get("message", {})
                return LLMResponse(
                    content=msg.get("content", ""),
                    model=target_model,
                    provider=self.provider_name,
                    usage={"eval_count": data.get("eval_count", 0)},
                )
        except Exception as e:
            logger.warning(f"Ollama chat request failed: {e}")
            raise RuntimeError(f"Ollama chat failed: {e}") from e
