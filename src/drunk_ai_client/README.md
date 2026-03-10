# Drunk MCP Client (STDIO)

A local stdio MCP server that proxies requests to a remote Drunk AI Proxy MCP endpoint.

## Run with uvx (local)

From the repo root:

```bash
uvx --from ./src/drunk_ai_client drunk_ai_client
```

## Run with uvx (published)

After publishing to a registry:

```bash
uvx drunk_ai_client
```

## Configuration

The client reads configuration from CLI arguments and environment variables.

## Environment variables

- `API_URL`: Remote MCP endpoint URL (required)
- `API_KEY`: Bearer token for auth (optional)
- `SKILL_DIR`: Local directory for synced skills (optional)
- `AGENTS_DIR`: Local directory for synced agents (optional)
- `ALLOWS_OVERWRITE`: Whether to overwrite local files during sync (`true|1|yes`)
-
## Notes

- `uvx` runs the console script `drunk_ai_client` provided by this package.
- The stdio bridge logs to stderr by default (FastMCP behavior).
