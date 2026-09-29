"""Deterministic unit tests for OllamaProvider using mocked HTTP transports (Phase 2C).

All tests execute completely offline without requiring a live Ollama daemon, GPU,
or external network access.
"""

import json
from typing import Any, Dict
import httpx
import pytest

from app.integrations.llm_provider import (
    LLMMessage,
    ToolCall,
    ModelAvailabilityStatus,
)
from app.integrations.ollama_provider import (
    OllamaProvider,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelNotFoundError,
    OllamaResponseError,
)


@pytest.mark.asyncio
async def test_basic_assistant_response_parsing():
    """1. Test standard text assistant completion parsing."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I assist you today?",
                },
                "eval_count": 12,
            },
        )

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        default_model="qwen3:4b",
        transport=httpx.MockTransport(handler),
    )

    messages = [LLMMessage(role="user", content="Hello")]
    resp = await provider.chat(messages)

    assert resp.content == "Hello! How can I assist you today?"
    assert resp.model == "qwen3:4b"
    assert resp.provider == "ollama"
    assert not resp.has_tool_calls
    assert resp.usage.get("eval_count") == 12


@pytest.mark.asyncio
async def test_structured_tool_call_parsing():
    """2. Test structured tool call extraction from response."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_12345",
                            "function": {
                                "name": "request_demo_action",
                                "arguments": {"action_name": "backup", "target": "database"},
                            },
                        }
                    ],
                },
            },
        )

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        default_model="qwen3:4b",
        transport=httpx.MockTransport(handler),
    )

    resp = await provider.chat([LLMMessage(role="user", content="Backup the database")])

    assert resp.has_tool_calls
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].id == "call_12345"
    assert resp.tool_calls[0].name == "request_demo_action"
    assert resp.tool_calls[0].arguments == {"action_name": "backup", "target": "database"}


@pytest.mark.asyncio
async def test_empty_tool_arguments():
    """3. Test tool call with empty arguments dictionary."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_empty_args",
                            "function": {
                                "name": "get_system_info",
                                "arguments": {},
                            },
                        }
                    ],
                },
            },
        )

    provider = OllamaProvider(transport=httpx.MockTransport(handler))
    resp = await provider.chat([LLMMessage(role="user", content="Get sys info")])

    assert resp.has_tool_calls
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "get_system_info"
    assert resp.tool_calls[0].arguments == {}


@pytest.mark.asyncio
async def test_multiple_tool_calls():
    """4. Test multiple tool calls returned in a single turn."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {"name": "get_system_info", "arguments": {}},
                        },
                        {
                            "id": "call_2",
                            "function": {"name": "request_demo_action", "arguments": {"action_name": "ping"}},
                        },
                    ],
                },
            },
        )

    provider = OllamaProvider(transport=httpx.MockTransport(handler))
    resp = await provider.chat([LLMMessage(role="user", content="Inspect system and ping")])

    assert resp.has_tool_calls
    assert len(resp.tool_calls) == 2
    assert resp.tool_calls[0].name == "get_system_info"
    assert resp.tool_calls[1].name == "request_demo_action"
    assert resp.tool_calls[1].arguments == {"action_name": "ping"}


@pytest.mark.asyncio
async def test_tool_result_messages():
    """5. Test formatting of conversation containing tool results."""
    captured_payload: Dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {"role": "assistant", "content": "Tool finished successfully."},
            },
        )

    provider = OllamaProvider(transport=httpx.MockTransport(handler))

    messages = [
        LLMMessage(role="user", content="Get info"),
        LLMMessage(
            role="assistant",
            content="",
            tool_calls=[ToolCall(id="call_999", name="get_system_info", arguments={})],
        ),
        LLMMessage(
            role="tool",
            name="get_system_info",
            tool_call_id="call_999",
            content=json.dumps({"os": "Windows 11"}),
        ),
    ]

    resp = await provider.chat(messages)

    assert resp.content == "Tool finished successfully."
    assert len(captured_payload["messages"]) == 3
    tool_msg = captured_payload["messages"][2]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "call_999"
    assert tool_msg["name"] == "get_system_info"


@pytest.mark.asyncio
async def test_thinking_field_is_not_exposed():
    """6. Ensure chain-of-thought in 'thinking' field and '<think>' tags is stripped and never exposed."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "qwen3:4b",
                "message": {
                    "role": "assistant",
                    "content": "<think>\nInternal reasoning steps here.\n</think>\nHere is the real answer.",
                    "thinking": "Secret internal chain-of-thought thoughts that should never leak.",
                },
            },
        )

    provider = OllamaProvider(transport=httpx.MockTransport(handler))
    resp = await provider.chat([LLMMessage(role="user", content="Explain something")])

    # Content must only contain the user-facing text
    assert resp.content == "Here is the real answer."
    # Thinking must not be present anywhere in the LLMResponse model
    assert not hasattr(resp, "thinking")
    assert "Secret internal" not in resp.content
    assert "<think>" not in resp.content


@pytest.mark.asyncio
async def test_malformed_response_handling():
    """7. Handle missing message object or invalid JSON payload."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Returns 200 but payload lacks 'message' dict
        return httpx.Response(200, json={"unexpected": "payload"})

    provider = OllamaProvider(transport=httpx.MockTransport(handler))

    with pytest.raises(OllamaResponseError) as exc_info:
        await provider.chat([LLMMessage(role="user", content="Hello")])

    assert "Missing or malformed 'message'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_http_error_handling():
    """8. Handle 404 (model not found) and 500 (internal server error) responses."""
    def not_found_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="model 'missing:latest' not found")

    provider = OllamaProvider(
        default_model="missing:latest",
        transport=httpx.MockTransport(not_found_handler),
    )

    with pytest.raises(OllamaModelNotFoundError):
        await provider.chat([LLMMessage(role="user", content="Hello")])

    def server_error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Ollama failure")

    provider_500 = OllamaProvider(transport=httpx.MockTransport(server_error_handler))
    with pytest.raises(OllamaResponseError) as exc_info:
        await provider_500.chat([LLMMessage(role="user", content="Hello")])

    assert "HTTP error 500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_connection_failure_handling():
    """9. Handle connection refused / daemon offline gracefully."""
    def conn_error_handler(request: httpx.Request):
        raise httpx.ConnectError("Connection refused by target machine")

    provider = OllamaProvider(transport=httpx.MockTransport(conn_error_handler))

    with pytest.raises(OllamaConnectionError) as exc_info:
        await provider.chat([LLMMessage(role="user", content="Hello")])

    assert "Cannot connect to Ollama" in str(exc_info.value)


@pytest.mark.asyncio
async def test_timeout_handling():
    """10. Handle inference timeout gracefully."""
    def timeout_handler(request: httpx.Request):
        raise httpx.ReadTimeout("Request timed out waiting for local GPU")

    provider = OllamaProvider(timeout=5.0, transport=httpx.MockTransport(timeout_handler))

    with pytest.raises(OllamaTimeoutError) as exc_info:
        await provider.chat([LLMMessage(role="user", content="Compute something heavy")])

    assert "timed out" in str(exc_info.value)


@pytest.mark.asyncio
async def test_model_configuration():
    """11. Verify custom model selection and model availability checking."""
    def tags_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "models": [
                    {"name": "qwen3:4b"},
                    {"name": "deepseek-r1:8b"},
                ]
            },
        )

    provider = OllamaProvider(
        default_model="qwen3:4b",
        transport=httpx.MockTransport(tags_handler),
    )

    status_installed = await provider.check_model_status("qwen3:4b")
    assert status_installed == ModelAvailabilityStatus.AVAILABLE

    status_another = await provider.check_model_status("deepseek-r1:8b")
    assert status_another == ModelAvailabilityStatus.AVAILABLE

    status_missing = await provider.check_model_status("llama3.1:70b")
    assert status_missing == ModelAvailabilityStatus.MODEL_NOT_FOUND


@pytest.mark.asyncio
async def test_base_url_configuration():
    """12. Verify custom base URL configuration is stripped and respected."""
    captured_url = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_url
        captured_url = str(request.url)
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "pong"}},
        )

    custom_url = "http://192.168.1.100:11434/"
    provider = OllamaProvider(
        base_url=custom_url,
        transport=httpx.MockTransport(handler),
    )

    assert provider.base_url == "http://192.168.1.100:11434"
    await provider.chat([LLMMessage(role="user", content="ping")])
    assert captured_url == "http://192.168.1.100:11434/api/chat"
