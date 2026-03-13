# WebSocket Responses API

This document describes the real-time LLM WebSocket endpoint exposed by `drunk_ai_proxy`.

## Endpoint

- WebSocket route: `/llm/v1/responses`
- Mounted by: `LlmProxiesProvider` when a WebSocket-capable provider is configured

## Request flow

1. Client opens a WebSocket connection to `/llm/v1/responses`.
2. Client sends OpenAI-compatible events (for example, `response.create`).
3. Proxy resolves provider/model from the incoming payload.
4. Proxy forwards events to the backend provider WebSocket endpoint.
5. Backend events are streamed back to the client.

## Model selection

Use provider-prefixed model IDs:

- Format: `{provider}_{model}`
- Example: `openai_gpt-4o-mini`

The proxy uses the prefix to select the backend provider and rewrites model routing as needed.

## Authentication

- WebSocket requests inherit the same auth behavior as the LLM proxy surface.
- When auth is enabled, include a valid bearer token.

## Notes

- The proxy is transport-focused: it forwards websocket events and upstream responses.
- Backend WebSocket URL construction and pooling are implemented in `websocket_transport.py`.
- Request/response fallback handling and terminal event detection are implemented in `websocket_provider.py`.

## Related files

- `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/proxies_provider.py`
- `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/websocket_provider.py`
- `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/websocket_transport.py`