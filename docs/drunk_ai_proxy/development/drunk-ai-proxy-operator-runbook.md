# `drunk_ai_proxy` Operator Runbook

## Scope

Operational checks and incident triage for the service implemented in `src/drunk_ai_proxy`.

## Start and verify

```bash
python -m pytest -q
python -m src.main
curl -s http://localhost:9123/health
```

Expected health response shape:
- `{"status": "healthy", "service": "<name>"}`

## Key runtime inputs

- Config file: `data/config.yaml`
- Module env defaults: `src/drunk_ai_proxy/drunk_ai_proxy/utils/env.py`

Critical env vars:
- `FASTMCP_CONFIG_DIR`
- `FASTMCP_HOST`, `FASTMCP_PORT`, `FASTMCP_LOG_LEVEL`
- `FASTMCP_LLM_ROUTE_PREFIX`
- `FASTMCP_AUTH_ENABLED`
- `FASTMCP_RATE_LIMIT_ENABLED`, `FASTMCP_RATE_LIMIT_REQUESTS`, `FASTMCP_RATE_LIMIT_WINDOW_SECONDS`
- `FASTMCP_OAUTH_STORAGE_TYPE`, `FASTMCP_OAUTH_STORAGE_ENCRYPTION_KEY`
- `REMOTE_RESOURCE_*`

## Startup triage

### Failure: config not found

Symptom:
- startup exception with missing config file.

Checks:
1. verify `FASTMCP_CONFIG_DIR` points to existing directory.
2. verify `<CONFIG_DIR>/config.yaml` exists and is readable.

### Failure: OpenAPI validation/config errors

Symptom:
- startup validation error for OpenAPI entry.

Checks:
1. ensure `spec_type: openapi` entries include `open_api.base_url`.
2. ensure `open_api.spec_file` exists under `CONFIG_DIR`.

### Failure: middleware/rate-limit config

Symptom:
- startup failure when rate limit enabled.

Checks:
1. ensure `FASTMCP_RATE_LIMIT_REQUESTS > 0`.
2. ensure `FASTMCP_RATE_LIMIT_WINDOW_SECONDS > 0`.

## Runtime triage

### 401 responses

- If `FASTMCP_AUTH_ENABLED=true`, verify clients send `Authorization` header.
- Confirm route is not in anonymous path allowlist.

### 429 responses

- Confirm IP-based rate limiting settings.
- Increase limit/window or disable rate limiting for investigation.

### LLM 400 invalid model

- Ensure `model` is in `provider_model` format.
- Ensure provider prefix matches configured `llm[].provider`.

### Remote resource sync issues

- Sync only accepts `https://` URLs.
- Destination must remain under `FASTMCP_CONFIG_DIR`.
- File extension must be allowlisted by `REMOTE_RESOURCE_ALLOWED_EXTENSIONS`.
- File size must be below `REMOTE_RESOURCE_MAX_SIZE_MB`.

## Safe change checklist

1. Validate config syntax and required fields.
2. Run focused tests:

```bash
python -m pytest tests/test_mcp_proxy_provider.py tests/test_llm_proxies_provider.py tests/test_lifespan.py -q
```

3. Validate health endpoint and one MCP + one LLM route.
4. Monitor logs for sanitized errors only (no sensitive payloads).

## Rollback hints

- Revert recent config changes in `data/config.yaml`.
- Disable optional toggles (`AUTH`, `RATE_LIMIT`, `REMOTE_RESOURCE`) to isolate failures.
- Re-run with `FASTMCP_LOG_LEVEL=DEBUG` for diagnostics.
