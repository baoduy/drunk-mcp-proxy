# Anthropic Provider - Messages API Wrapper

## Overview

The `AnthropicProvider` module provides format conversion utilities for proxying Anthropic Messages API requests through OpenAI-compatible backends. This enables Anthropic Claude models to be accessed through OpenAI-compatible LLM providers.

## Architecture

```
Client (Anthropic Format) → AnthropicProvider → OpenAI Format → Backend
                              ↓
Client (Anthropic Format) ← AnthropicProvider ← OpenAI Format ← Backend
```

The provider acts as a bidirectional converter:
- **Request direction**: Anthropic Messages API → OpenAI Chat Completions API
- **Response direction**: OpenAI Chat Completions API → Anthropic Messages API
- **Streaming**: OpenAI SSE events → Anthropic SSE events

## Features

### Request Conversion

The `anthropic_to_openai_request()` method converts Anthropic Messages API requests to OpenAI format:

#### System Prompts
- **String system prompts** → OpenAI system message
- **Array of text blocks** → Concatenated system message

```python
# Anthropic format
{
    "system": "You are a helpful assistant.",
    "messages": [{"role": "user", "content": "Hello"}]
}

# Converted to OpenAI format
{
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
}
```

#### Multimodal Content

**Images (Base64)**:
```python
# Anthropic format
{
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/png",
        "data": "iVBORw0KGgo..."
    }
}

# Converted to OpenAI format
{
    "type": "image_url",
    "image_url": {"url": "data:image/png;base64,iVBORw0KGgo..."}
}
```

**Images (URL)**:
```python
# Anthropic format
{
    "type": "image",
    "source": {"type": "url", "url": "https://example.com/image.png"}
}

# Converted to OpenAI format
{
    "type": "image_url",
    "image_url": {"url": "https://example.com/image.png"}
}
```

#### Tool Use

**Tool Calls**:
```python
# Anthropic format
{
    "type": "tool_use",
    "id": "toolu_123",
    "name": "get_weather",
    "input": {"location": "San Francisco"}
}

# Converted to OpenAI format
{
    "id": "toolu_123",
    "type": "function",
    "function": {
        "name": "get_weather",
        "arguments": "{\"location\": \"San Francisco\"}"
    }
}
```

**Tool Results**:
```python
# Anthropic format (in user message)
{
    "type": "tool_result",
    "tool_use_id": "toolu_123",
    "content": "Sunny, 72°F"
}

# Converted to OpenAI format (separate message)
{
    "role": "tool",
    "tool_call_id": "toolu_123",
    "content": "Sunny, 72°F"
}
```

#### Tool Definitions

**Tools**:
```python
# Anthropic format
{
    "tools": [{
        "name": "get_weather",
        "description": "Get current weather",
        "input_schema": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"]
        }
    }]
}

# Converted to OpenAI format
{
    "tools": [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"]
            }
        }
    }]
}
```

**Tool Choice**:
- `{"type": "auto"}` → `"auto"`
- `{"type": "any"}` → `"required"`
- `{"type": "tool", "name": "get_weather"}` → `{"type": "function", "function": {"name": "get_weather"}}`

#### Parameters

| Anthropic Parameter | OpenAI Parameter | Notes |
|---------------------|------------------|-------|
| `max_tokens` | `max_tokens` | Direct mapping |
| `temperature` | `temperature` | Direct mapping |
| `top_p` | `top_p` | Direct mapping |
| `stream` | `stream` | Direct mapping |
| `stop_sequences` | `stop` | Array of stop strings |
| `top_k` | `top_k` | Passed through (may not be supported by all backends) |
| `metadata.user_id` | `user` | User tracking |

### Response Conversion

The `openai_to_anthropic_response()` method converts OpenAI responses to Anthropic format:

#### Finish Reason Mapping

| OpenAI `finish_reason` | Anthropic `stop_reason` |
|------------------------|-------------------------|
| `stop` | `end_turn` |
| `length` | `max_tokens` |
| `tool_calls` | `tool_use` |
| `content_filter` | `end_turn` |
| Other | `end_turn` |

#### Usage Tokens

```python
# OpenAI format
{
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 25
    }
}

# Converted to Anthropic format
{
    "usage": {
        "input_tokens": 10,
        "output_tokens": 25
    }
}
```

### Streaming Conversion

The `format_anthropic_streaming_response()` method converts OpenAI SSE streams to Anthropic SSE format:

#### Event Sequence

```
event: message_start
data: {"type": "message_start", "message": {...}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {...}}

event: ping
data: {"type": "ping"}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": " world"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": null}, "usage": {"output_tokens": 10}}

event: message_stop
data: {"type": "message_stop"}
```

## Usage

### Basic Usage

```python
from proxies.anthropic_provider import AnthropicProvider

# Convert request
anthropic_body = {
    "model": "claude-3-5-sonnet-20241022",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
}

openai_body = AnthropicProvider.anthropic_to_openai_request(
    anthropic_body,
    "gpt-4o"  # Backend model name
)

# Convert response
openai_response = {
    "id": "chatcmpl-123",
    "choices": [{
        "message": {"role": "assistant", "content": "Hi there!"},
        "finish_reason": "stop"
    }],
    "usage": {"prompt_tokens": 5, "completion_tokens": 10}
}

anthropic_response = AnthropicProvider.openai_to_anthropic_response(
    openai_response,
    "openai_gpt-4o"  # Original model ID
)
```

### Streaming Usage

```python
# Convert streaming response
async def openai_stream():
    yield {"id": "chatcmpl-123", "choices": [{"delta": {"content": "Hello"}}]}
    yield {"id": "chatcmpl-123", "choices": [{"delta": {"content": " world"}}]}
    yield {"id": "chatcmpl-123", "choices": [{"delta": {}, "finish_reason": "stop"}]}

streaming_response = await AnthropicProvider.format_anthropic_streaming_response(
    openai_stream(),
    "openai_gpt-4o"
)

# Returns FastAPI StreamingResponse with Anthropic SSE events
```

### Integration with LlmProxiesProvider

The `AnthropicProvider` is automatically integrated into `LlmProxiesProvider`:

```python
# In llm_proxies_provider.py
async def _anthropic_messages_endpoint(self, request: Request):
    body = await request.json()
    
    # Parse model ID
    provider_name, model_name = self.parse_model_id(body["model"])
    
    # Convert to OpenAI format
    openai_body = AnthropicProvider.anthropic_to_openai_request(body, model_name)
    
    # Call backend
    client = self.open_ai_factory.get_client(provider_name)
    response = await client.chat.completions.create(**openai_body)
    
    # Convert back to Anthropic format
    if body.get("stream"):
        return await AnthropicProvider.format_anthropic_streaming_response(response, body["model"])
    else:
        anthropic_response = AnthropicProvider.openai_to_anthropic_response(response, body["model"])
        return JSONResponse(content=anthropic_response)
```

## API Reference

### `anthropic_to_openai_request(body: dict[str, Any], model_name: str) -> dict[str, Any]`

Converts Anthropic Messages API request to OpenAI Chat Completions format.

**Parameters:**
- `body`: Raw Anthropic request body (dict)
- `model_name`: Provider-stripped model name (e.g., "gpt-4o")

**Returns:**
- Dict suitable for AsyncOpenAI client

**Example:**
```python
request = {
    "model": "claude-3-5-sonnet-20241022",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 100
}
result = AnthropicProvider.anthropic_to_openai_request(request, "gpt-4o")
```

### `openai_to_anthropic_response(response: Any, model_id: str) -> dict[str, Any]`

Converts OpenAI Chat Completions response to Anthropic Messages API format.

**Parameters:**
- `response`: OpenAI response object or dict
- `model_id`: Original model ID from Anthropic request (e.g., "openai_gpt-4o")

**Returns:**
- Dict conforming to Anthropic Messages API response schema

**Example:**
```python
openai_response = {
    "id": "chatcmpl-123",
    "choices": [{"message": {"content": "Hello!"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 10}
}
result = AnthropicProvider.openai_to_anthropic_response(openai_response, "openai_gpt-4o")
```

### `format_anthropic_streaming_response(stream: Any, model_id: str) -> StreamingResponse`

Wraps OpenAI SSE stream as Anthropic SSE events.

**Parameters:**
- `stream`: Async iterable of OpenAI completion chunks
- `model_id`: Original model ID from Anthropic request

**Returns:**
- FastAPI StreamingResponse with `text/event-stream` media type

**Example:**
```python
async def openai_chunks():
    yield {"id": "chatcmpl-123", "choices": [{"delta": {"content": "Hi"}}]}

response = await AnthropicProvider.format_anthropic_streaming_response(
    openai_chunks(),
    "openai_gpt-4o"
)
```

## Testing

The module includes comprehensive unit tests in `tests/test_anthropic_provider.py`:

```bash
# Run all tests
pytest tests/test_anthropic_provider.py -v

# Run specific test class
pytest tests/test_anthropic_provider.py::TestAnthropicToOpenAIRequest -v

# Run with coverage
pytest tests/test_anthropic_provider.py --cov=src/proxies/anthropic_provider
```

**Test Coverage:**
- ✅ 25 tests covering all conversion scenarios
- ✅ Request conversion (text, images, tools, parameters)
- ✅ Response conversion (text, tool calls, finish reasons)
- ✅ Streaming SSE event generation
- ✅ Edge cases (invalid JSON, empty content, etc.)

## Limitations

1. **Content Concatenation**: When converting system prompts or tool results with multiple text blocks, text is joined with spaces (may add extra spaces if blocks already have trailing/leading spaces).

2. **Tool Result Format**: Anthropic's `tool_result` blocks within user messages are converted to separate OpenAI `tool` role messages, which changes the message structure.

3. **Top-K Parameter**: The `top_k` parameter is passed through but may not be supported by all OpenAI-compatible backends.

4. **Model Name**: The original Anthropic model name is lost during conversion; the response uses the proxy model ID format (`provider_modelname`).

## Related Documentation

- [LLM Proxies Provider](./llm-proxies-provider.md)
- [API Usage Guide](../guides/api-usage.md)
- [Tool Use Guide](../guides/tool-use.md)
- [Anthropic Messages API Reference](https://docs.anthropic.com/en/api/messages)
