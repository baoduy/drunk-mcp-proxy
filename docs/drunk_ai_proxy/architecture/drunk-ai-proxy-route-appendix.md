# `drunk_ai_proxy` Route Appendix

This appendix lists runtime routes exposed by `src/drunk_ai_proxy/drunk_ai_proxy`.

## Server-level routes

Mounted by `StarletteApp.build()`:

- `GET /health` - service health payload.
- `GET /` - health-style root response.

## MCP mount routes

Mounted per `McpProxyConfig.path`:

- Root MCP (`path: /`) -> `/mcp`
- Namespaced MCP (`path: /x`) -> `/x/mcp`

Behavior source:
- `app/starlette_app.py:add_mcp_service`

## LLM route prefix

Mounted via `MCPProxyServer` with env-driven prefix:

- Prefix: `FASTMCP_LLM_ROUTE_PREFIX` (default `/api/v1`)

Mounted app: `LlmProxiesProvider._get_fastapi_app()`

## LLM HTTP endpoints

Under `<prefix>`:

- `POST /chat/completions`
- `POST /messages` (Anthropic-compatible interface)
- `POST /embeddings`
- `POST /audio/transcriptions`
- `POST /audio/translations`
- `POST /images/generations`
- `GET /models`
- `GET /providers`

## LLM WebSocket endpoint

Under `<prefix>`:

- `WS /responses`

## Optional docs routes

When `FASTMCP_SWAGGER_ENABLED=true`, Swagger/OpenAPI docs are mounted by `SwaggerProvider.mount(...)`.

## Middleware route effects

Global middleware stack (`get_middlewares()` + Starlette fallback add):

- CORS headers
- Request size limit (413 on oversize)
- Security headers
- Optional auth header enforcement (401 on missing/empty auth for protected paths)
- Optional fixed-window IP rate limiting (429 + `Retry-After`)

## Common route-level errors

- Invalid model format (expected `provider_model`) -> 400 on LLM endpoints.
- Missing Authorization header on protected paths -> 401.
- Rate limit exceeded -> 429.
- Unhandled server exceptions are sanitized by global exception handler.
