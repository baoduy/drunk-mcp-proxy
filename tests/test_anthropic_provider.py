"""Unit tests for AnthropicProvider - Anthropic Messages API format converter.

This test suite covers:
- Request conversion: Anthropic Messages API → OpenAI format
- Response conversion: OpenAI → Anthropic Messages API format
- Streaming response formatting
- Edge cases and error handling
"""

from __future__ import annotations

import json
import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from proxies.anthropic_provider import AnthropicProvider
from tools.serialization import to_dict


class TestAnthropicToOpenAIRequest:
    """Tests for anthropic_to_openai_request conversion."""

    def test_basic_text_message(self) -> None:
        """Test conversion of basic text message."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert result["model"] == "gpt-4o"
        assert result["messages"] == [{"role": "user", "content": "Hello"}]
        assert result["max_tokens"] == 100

    def test_system_prompt_string(self) -> None:
        """Test conversion with string system prompt."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "system": "You are a helpful assistant.",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert len(result["messages"]) == 2
        assert result["messages"][0] == {
            "role": "system",
            "content": "You are a helpful assistant.",
        }
        assert result["messages"][1]["role"] == "user"

    def test_system_prompt_blocks(self) -> None:
        """Test conversion with system prompt as text blocks."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "system": [
                {"type": "text", "text": "You are helpful."},
                {"type": "text", "text": " Be concise."},
            ],
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert result["messages"][0] == {
            "role": "system",
            "content": "You are helpful.  Be concise.",
        }

    def test_image_base64(self) -> None:
        """Test conversion with base64 image."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": "iVBORw0KGgo=",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        content = result["messages"][0]["content"]
        assert len(content) == 2
        assert content[0] == {"type": "text", "text": "What's in this image?"}
        assert content[1]["type"] == "image_url"
        assert content[1]["image_url"]["url"] == "data:image/png;base64,iVBORw0KGgo="

    def test_image_url(self) -> None:
        """Test conversion with image URL."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "url",
                                "url": "https://example.com/image.png",
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        content = result["messages"][0]["content"]
        assert content[0]["type"] == "image_url"
        assert content[0]["image_url"]["url"] == "https://example.com/image.png"

    def test_tool_use(self) -> None:
        """Test conversion with tool_use block."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Let me check the weather."},
                        {
                            "type": "tool_use",
                            "id": "toolu_123",
                            "name": "get_weather",
                            "input": {"location": "San Francisco"},
                        },
                    ],
                }
            ],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        message = result["messages"][0]
        assert message["role"] == "assistant"
        assert message["content"][0] == {
            "type": "text",
            "text": "Let me check the weather.",
        }
        assert len(message["tool_calls"]) == 1
        assert message["tool_calls"][0] == {
            "id": "toolu_123",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"location": "San Francisco"}',
            },
        }

    def test_tool_result(self) -> None:
        """Test conversion with tool_result block."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_123",
                            "content": "Sunny, 72°F",
                        },
                    ],
                }
            ],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        # tool_result should create a separate tool message
        assert len(result["messages"]) == 1
        assert result["messages"][0] == {
            "role": "tool",
            "tool_call_id": "toolu_123",
            "content": "Sunny, 72°F",
        }

    def test_tool_result_with_text_blocks(self) -> None:
        """Test conversion with tool_result containing text blocks."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": "toolu_123",
                            "content": [
                                {"type": "text", "text": "Result: "},
                                {"type": "text", "text": "Success"},
                            ],
                        },
                    ],
                }
            ],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert result["messages"][0]["content"] == "Result:  Success"

    def test_tools_definition(self) -> None:
        """Test conversion with tools definition."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "What's the weather?"}],
            "tools": [
                {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "input_schema": {
                        "type": "object",
                        "properties": {"location": {"type": "string"}},
                        "required": ["location"],
                    },
                }
            ],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert "tools" in result
        assert len(result["tools"]) == 1
        assert result["tools"][0] == {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get current weather",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}},
                    "required": ["location"],
                },
            },
        }

    def test_tool_choice_auto(self) -> None:
        """Test conversion with tool_choice: auto."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": [{"name": "tool1", "description": "Tool"}],
            "tool_choice": {"type": "auto"},
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert result["tool_choice"] == "auto"

    def test_tool_choice_any(self) -> None:
        """Test conversion with tool_choice: any (required)."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": [{"name": "tool1", "description": "Tool"}],
            "tool_choice": {"type": "any"},
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert result["tool_choice"] == "required"

    def test_tool_choice_tool(self) -> None:
        """Test conversion with tool_choice: specific tool."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": [{"name": "get_weather", "description": "Tool"}],
            "tool_choice": {"type": "tool", "name": "get_weather"},
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert result["tool_choice"] == {
            "type": "function",
            "function": {"name": "get_weather"},
        }

    def test_other_parameters(self) -> None:
        """Test conversion of other parameters."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 0.9,
            "stream": True,
            "stop_sequences": ["\n\n", "END"],
            "top_k": 50,
            "metadata": {"user_id": "user123"},
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        assert result["temperature"] == 0.7
        assert result["top_p"] == 0.9
        assert result["stream"] is True
        assert result["stop"] == ["\n\n", "END"]
        assert result["top_k"] == 50
        assert result["user"] == "user123"

    def test_complex_multimodal_message(self) -> None:
        """Test conversion with complex content including text and image."""
        body = {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Single text block"},
                    ],
                }
            ],
            "max_tokens": 100,
        }
        
        result = AnthropicProvider.anthropic_to_openai_request(body, "gpt-4o")
        
        # Single text block should be simplified to string
        assert result["messages"][0]["content"] == "Single text block"


class TestOpenAIToAnthropicResponse:
    """Tests for openai_to_anthropic_response conversion."""

    def test_basic_text_response(self) -> None:
        """Test conversion of basic text response."""
        response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        
        result = AnthropicProvider.openai_to_anthropic_response(
            response, "openai_gpt-4o"
        )
        
        assert result["id"] == "chatcmpl-123"
        assert result["type"] == "message"
        assert result["role"] == "assistant"
        assert result["model"] == "openai_gpt-4o"
        assert result["content"] == [{"type": "text", "text": "Hello!"}]
        assert result["stop_reason"] == "end_turn"
        assert result["stop_sequence"] is None
        assert result["usage"]["input_tokens"] == 10
        assert result["usage"]["output_tokens"] == 5

    def test_tool_calls_response(self) -> None:
        """Test conversion with tool calls."""
        response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Let me check that.",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "NYC"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
        }
        
        result = AnthropicProvider.openai_to_anthropic_response(
            response, "openai_gpt-4o"
        )
        
        assert len(result["content"]) == 2
        assert result["content"][0] == {"type": "text", "text": "Let me check that."}
        assert result["content"][1] == {
            "type": "tool_use",
            "id": "call_123",
            "name": "get_weather",
            "input": {"location": "NYC"},
        }
        assert result["stop_reason"] == "tool_use"

    def test_finish_reason_mapping(self) -> None:
        """Test finish_reason to stop_reason mapping."""
        test_cases = [
            ("stop", "end_turn"),
            ("length", "max_tokens"),
            ("tool_calls", "tool_use"),
            ("content_filter", "end_turn"),
            ("unknown", "end_turn"),
        ]
        
        for finish_reason, expected_stop_reason in test_cases:
            response = {
                "id": "chatcmpl-123",
                "choices": [
                    {
                        "message": {"content": "Test"},
                        "finish_reason": finish_reason,
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5},
            }
            
            result = AnthropicProvider.openai_to_anthropic_response(
                response, "openai_gpt-4o"
            )
            
            assert result["stop_reason"] == expected_stop_reason, (
                f"Failed for finish_reason='{finish_reason}'"
            )

    def test_multiple_tool_calls(self) -> None:
        """Test conversion with multiple tool calls."""
        response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "tool1",
                                    "arguments": '{"arg1": "val1"}',
                                },
                            },
                            {
                                "id": "call_2",
                                "type": "function",
                                "function": {
                                    "name": "tool2",
                                    "arguments": '{"arg2": "val2"}',
                                },
                            },
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 20},
        }
        
        result = AnthropicProvider.openai_to_anthropic_response(
            response, "openai_gpt-4o"
        )
        
        # Should have 2 tool_use blocks (no text since content is None)
        assert len(result["content"]) == 2
        assert result["content"][0]["type"] == "tool_use"
        assert result["content"][0]["name"] == "tool1"
        assert result["content"][1]["type"] == "tool_use"
        assert result["content"][1]["name"] == "tool2"

    def test_invalid_tool_call_json(self) -> None:
        """Test handling of invalid JSON in tool call arguments."""
        response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "tool1",
                                    "arguments": "invalid json {",
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5},
        }
        
        result = AnthropicProvider.openai_to_anthropic_response(
            response, "openai_gpt-4o"
        )
        
        # Should handle gracefully with empty input
        assert result["content"][0]["input"] == {}


class TestFormatAnthropicStreamingResponse:
    """Tests for format_anthropic_streaming_response SSE formatting."""

    @pytest.mark.asyncio
    async def test_streaming_response_events(self) -> None:
        """Test streaming response generates correct SSE event sequence."""
        
        # Mock OpenAI stream chunks
        async def mock_stream():
            # First chunk with ID
            yield {
                "id": "chatcmpl-123",
                "choices": [{"delta": {"content": "Hello"}, "finish_reason": None}],
            }
            # Second chunk with more content
            yield {
                "id": "chatcmpl-123",
                "choices": [{"delta": {"content": " world"}, "finish_reason": None}],
            }
            # Final chunk with finish reason
            yield {
                "id": "chatcmpl-123",
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10},
            }
        
        response = await AnthropicProvider.format_anthropic_streaming_response(
            mock_stream(), "openai_gpt-4o"
        )
        
        # Collect all events
        events = []
        async for chunk in response.body_iterator:
            # chunk is already a string from StreamingResponse
            events.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))
        
        # Verify event sequence
        assert "event: message_start" in events[0]
        assert "event: content_block_start" in events[1]
        assert "event: ping" in events[2]
        assert "event: content_block_delta" in events[3]
        assert '"text": "Hello"' in events[3]
        assert "event: content_block_delta" in events[4]
        assert '"text": " world"' in events[4]
        assert "event: content_block_stop" in events[5]
        assert "event: message_delta" in events[6]
        assert '"stop_reason": "end_turn"' in events[6]
        assert '"output_tokens": 10' in events[6]
        assert "event: message_stop" in events[7]

    @pytest.mark.asyncio
    async def test_streaming_with_tool_calls(self) -> None:
        """Test streaming doesn't break with tool calls finish reason."""
        
        async def mock_stream():
            yield {
                "id": "chatcmpl-123",
                "choices": [{"delta": {"content": "Checking..."}, "finish_reason": None}],
            }
            yield {
                "id": "chatcmpl-123",
                "choices": [{"delta": {}, "finish_reason": "tool_calls"}],
                "usage": {"completion_tokens": 5},
            }
        
        response = await AnthropicProvider.format_anthropic_streaming_response(
            mock_stream(), "openai_gpt-4o"
        )
        
        events = []
        async for chunk in response.body_iterator:
            # chunk is already a string from StreamingResponse
            events.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))
        
        # Should have message_delta with stop_reason: tool_use
        message_delta_event = [e for e in events if "message_delta" in e][0]
        assert '"stop_reason": "tool_use"' in message_delta_event


class TestToDict:
    """Tests for to_dict helper function."""

    def test_to_dict_with_dict(self) -> None:
        """Test to_dict with plain dict."""
        obj = {"key": "value"}
        result = to_dict(obj)
        assert result == {"key": "value"}

    def test_to_dict_with_pydantic_model(self) -> None:
        """Test to_dict with Pydantic model."""
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            value: int
        
        obj = TestModel(name="test", value=42)
        result = to_dict(obj)
        
        assert result == {"name": "test", "value": 42}

    def test_to_dict_with_object_dict(self) -> None:
        """Test to_dict with object having __dict__."""
        
        class TestObj:
            def __init__(self):
                self.foo = "bar"
                self.num = 123
        
        obj = TestObj()
        result = to_dict(obj)
        
        assert result == {"foo": "bar", "num": 123}

    def test_to_dict_with_string(self) -> None:
        """Test to_dict with string (returns empty dict for non-dict-like objects)."""
        obj = "test string"
        result = to_dict(obj)
        # String is not dict-like, should return empty dict
        assert result == {}
