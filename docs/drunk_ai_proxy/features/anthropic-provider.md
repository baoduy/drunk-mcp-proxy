# Anthropic Provider — Messages API Converter

**Status**: Implemented  
**Version**: 0.2.0  

## Overview

The `AnthropicProvider` is a bidirectional format converter that enables Anthropic Messages API clients to communicate with OpenAI-compatible LLM backends. It translates requests and responses between the two API formats, including streaming SSE events.

## Architecture

```
Client (Anthropic Format) → AnthropicProvider → OpenAI Format → Backend LLM
                              ↓
Client (Anthropic Format) ← AnthropicProvider ← OpenAI Format ← Backend LLM
```

**Source**: `proxies/llm/anthropic_provider.py` (354 lines)

The provider contains three static methods — no instantiation required:

| Method | Direction | Description |
|--------|-----------|-------------|
| `anthropic_to_openai_request()` | Request → | Convert Anthropic request body to OpenAI format |
| `openai_to_anthropic_response()` | ← Response | Convert OpenAI response to Anthropic format |
| `format_anthropic_streaming_response()` | ← Stream | Convert OpenAI SSE stream to Anthropic SSE events |

## Integration

The `AnthropicProvider` is automatically used by `LlmProxiesProvider` when requests arrive at the `/v1/messages` Anthropic-compatible endpoint:

```python
# In llm_proxies_provider.py
async def _anthropic_messages_endpoint(self, request: Request):
    body = await request.json()
    provider_name, model_name = self.parse_model_id(body["model"])
    
    # Convert Anthropic → OpenAI
    openai_body = AnthropicProvider.anthropic_to_openai_request(body, model_name)
    
    # Call OpenAI-compatible backend
    response = await client.chat.completions.create(**openai_body)
    
    # Convert OpenAI → Anthropic
    if body.get("stream"):
        return await AnthropicProvider.format_anthropic_streaming_response(response, body["model"])
    else:
        return JSONResponse(AnthropicProvider.openai_to_anthropic_response(response, body["model"]))
```

## Request Conversion

### System Prompts

**String system prompt:**
```json
// Anthropic
{"system": "You are a helpful assistant.", "messages": [...]}

// → OpenAI
{"messages": [{"role": "system", "content": "You are a helpful assistant."}, ...]}
```

**Array of text blocks:**
```json
// Anthropic
{"system": [{"type": "text", "text": "First."}, {"type": "text", "text": "Second."}]}

// → OpenAI
{"messages": [{"role": "system", "content": "First. Second."}]}
```

### Multimodal Content

**Images (Base64):**
```json
// Anthropic
{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "iVBOR..."}}

// → OpenAI
{"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBOR..."}}
```

**Images (URL):**
```json
// Anthropic
{"type": "image", "source": {"type": "url", "url": "https://example.com/img.png"}}

// → OpenAI
{"type": "image_url", "image_url": {"url": "https://example.com/img.png"}}
```

### Tool Use

**Tool calls (assistant → function):**
```json
// Anthropic
{"type": "tool_use", "id": "toolu_123", "name": "get_weather", "input": {"location": "SF"}}

// → OpenAI
{"id": "toolu_123", "type": "function", "function": {"name": "get_weather", "arguments": "{\"location\": \"SF\"}"}}
```

**Tool results (user → tool role):**
```json
// Anthropic (in user message content)
{"type": "tool_result", "tool_use_id": "toolu_123", "content": "Sunny, 72°F"}

// → OpenAI (separate message)
{"role": "tool", "tool_call_id": "toolu_123", "content": "Sunny, 72°F"}
```

### Tool Definitions

```json
// Anthropic
{"tools": [{"name": "get_weather", "description": "...", "input_schema": {"type": "object", ...}}]}

// → OpenAI
{"tools": [{"type": "function", "function": {"name": "get_weather", "description": "...", "parameters": {"type": "object", ...}}}]}
```

### Tool Choice Mapping

| Anthropic | OpenAI |
|-----------|--------|
| `{"type": "auto"}` | `"auto"` |
| `{"type": "any"}` | `"required"` |
| `{"type": "tool", "name": "fn"}` | `{"type": "function", "function": {"name": "fn"}}` |

### Parameter Mapping

| Anthropic | OpenAI | Notes |
|-----------|--------|-------|
| `max_tokens` | `max_tokens` | Direct |
| `temperature` | `temperature` | Direct |
| `top_p` | `top_p` | Direct |
| `stream` | `stream` | Direct |
| `stop_sequences` | `stop` | Array of stop strings |
| `top_k` | `top_k` | Pass-through (not supported by all backends) |
| `metadata.user_id` | `user` | User tracking |

## Response Conversion

### Finish Reason Mapping

| OpenAI `finish_reason` | Anthropic `stop_reason` |
|------------------------|-------------------------|
| `stop` | `end_turn` |
| `length` | `max_tokens` |
| `tool_calls` | `tool_use` |
| `content_filter` | `end_turn` |
| Other | `end_turn` |

### Usage Token Mapping

```json
// OpenAI
{"usage": {"prompt_tokens": 10, "completion_tokens": 25}}

// → Anthropic
{"usage": {"input_tokens": 10, "output_tokens": 25}}
```

## Streaming Conversion

The `format_anthropic_streaming_response()` method converts OpenAI SSE chunks into Anthropic's event sequence:

```
event: message_start
data: {"type": "message_start", "message": {...}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {...}}

event: ping
data: {"type": "ping"}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 10}}

event: message_stop
data: {"type": "message_stop"}
```

Returns a FastAPI `StreamingResponse` with `text/event-stream` content type.

## Limitations

1. **Content concatenation**: When converting system prompts or tool results with multiple text blocks, text is joined with spaces
2. **Tool result structure**: Anthropic's `tool_result` blocks within user messages become separate OpenAI `tool` role messages
3. **Top-K parameter**: Passed through but may not be supported by all OpenAI-compatible backends
4. **Model name**: The original Anthropic model name is replaced with the proxy model ID format (`provider_modelname`)

## Testing

```bash
# Run all Anthropic provider tests
python -m pytest tests/test_anthropic_provider.py -v

# Run specific test class
python -m pytest tests/test_anthropic_provider.py::TestAnthropicToOpenAIRequest -v
```

### Test Coverage (25 tests)
- Request conversion: text, images (base64/URL), tools, parameters
- Response conversion: text, tool calls, finish reasons, usage tokens
- Streaming SSE event generation
- Edge cases: invalid JSON, empty content, missing fields

## Related

- [MCP Prompt Provider](./mcp-prompt-provider.md) — Prompt template system
- [Agents Directory](./agents-directory-implementation.md) — Agent definitions
- [Anthropic Messages API Reference](https://docs.anthropic.com/en/api/messages)
- [OpenAI Chat Completions Reference](https://platform.openai.com/docs/api-reference/chat)
