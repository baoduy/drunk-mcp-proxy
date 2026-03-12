# OpenAPI Provider Consolidation Plan

## Goal

Simplify OpenAPI proxy wiring by removing `OpenApiMcpProvider` and consolidating OpenAPI composition into `McpProxyProvider` via a new method:

- `__add_open_api_proxy(self, mcp: FastMCP) -> None`

This keeps one canonical MCP provider class while preserving current OpenAPI behavior (filters, auth-aware client creation, and skill/prompt/agent composition).

## Current-State Findings

### Existing split

- `McpProxyProvider` handles `spec_type: mcp` and mounts MCP upstream via `fastmcp.server.create_proxy`.
- `OpenApiMcpProvider` handles `spec_type: openapi` by:
  - creating `httpx.AsyncClient(base_url=..., auth=...)`
  - calling `FastMCP.from_openapi(...)`
  - applying route filters through `route_map_fn`
  - attaching auth and skills/agents.

### Selection path

- `StaticProxiesProvider._get_openapi_services()` imports `OpenApiMcpProvider` and calls `OpenApiMcpProvider.create_mcp_proxies_configs(...)`.
- Package exports expose `OpenApiMcpProvider` through:
  - `proxies/mcp/__init__.py`
  - `proxies/__init__.py`

### Test coupling

- `tests/test_openapi_mcp_provider.py` is tightly coupled to class `OpenApiMcpProvider` and old import paths.
- `tests/test_proxies_init.py` asserts `OpenApiMcpProvider` is lazily exported.

## Design Decisions

1. Consolidate OpenAPI creation logic into `McpProxyProvider` (single provider class per domain).
2. Keep OpenAPI config selection in `StaticProxiesProvider`, but route to `McpProxyProvider.create_openapi_proxies_configs(...)`.
3. Preserve FastMCP-native behavior by continuing to use `FastMCP.from_openapi(...)` for OpenAPI conversion.
4. Keep skill/prompt/agent enrichment in the same provider after OpenAPI components are attached.
5. Remove `openapi_provider.py` entirely after migrating imports/tests/exports.

## Implementation Plan

### Phase 1: Extend `McpProxyProvider` for OpenAPI

1. Add OpenAPI helpers to `McpProxyProvider`:
   - `__get_openapi_filters()`
   - `__openapi_route_mapper(route: HTTPRoute, mcp_type: MCPType) -> MCPType | None`
   - `__create_openapi_client() -> httpx.AsyncClient`
   - `__add_open_api_proxy(mcp: FastMCP) -> None`
2. In `create_proxy()`, branch by `self.config.spec_type`:
   - `mcp` → existing `_create_proxy(...)`
   - `openapi` → new `__add_open_api_proxy(...)`
3. Ensure auth assignment remains consistent (`mcp.auth = self._get_app_auth_provider()`).
4. Keep skill/prompt/agent add-ons enabled for both spec types.

### Phase 2: Replace OpenAPI config builder entrypoint

1. Add `@staticmethod create_openapi_proxies_configs(configs: list[McpConfig]) -> list[McpProxyConfig]` in `McpProxyProvider`.
2. Implement via `McpProxyBuilder.build_openapi_proxy_configs(...)` using provider factory `lambda config: McpProxyProvider(config=config)`.
3. Update `StaticProxiesProvider._get_openapi_services()` to call `McpProxyProvider.create_openapi_proxies_configs(...)`.

### Phase 3: Remove legacy provider module

1. Delete `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/openapi_provider.py`.
2. Remove related exports/imports from:
   - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/__init__.py`
   - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/__init__.py`
3. Update any package metadata references if required (egg-info source list regeneration is build-generated; do not hand-edit unless repository expects it).

### Phase 4: Update tests

1. Replace `tests/test_openapi_mcp_provider.py` with tests targeting `McpProxyProvider` OpenAPI path:
   - route filter behavior (methods/tags)
   - OpenAPI client creation and auth wiring
   - OpenAPI proxy creation with `FastMCP.from_openapi`
   - caching behavior (`self.mcp` reuse)
   - validation errors (`base_url` missing, `spec_data` missing)
2. Update `tests/test_proxies_init.py` to remove `OpenApiMcpProvider` export assertions and keep MCP export assertions valid.
3. Add/adjust `StaticProxiesProvider` tests (or extend existing server wiring tests) to verify OpenAPI configs now flow through `McpProxyProvider`.

### Phase 5: Documentation and changelog

1. Update any docs mentioning `OpenApiMcpProvider` as public API surface.
2. Add `[Unreleased]` entry in `CHANGE_LOGS.md` under `### Changed` describing provider consolidation.

## Behavioral Parity Checklist

- OpenAPI `route_map_fn` filtering still excludes by configured methods/tags.
- `FastMCP.from_openapi` still receives:
  - `name=f"{SERVER_NAME}{self.config.path}"`
  - `openapi_spec=self.config.get_openapi_spec_data()`
  - `client=<async client>`
  - `route_map_fn=<custom mapper>`
  - `tags=self.config.tags`
- OpenAPI proxies still get auth, skills, prompts, and agents.
- Caching behavior (`self.mcp`) remains unchanged.

## Risks and Mitigations

1. Name-mangling risk with double-underscore method
   - Risk: unit tests that patch `__add_open_api_proxy` directly can be brittle.
   - Mitigation: patch through public `create_proxy()` effects; if direct patching is needed, patch mangled name (`_McpProxyProvider__add_open_api_proxy`).

2. Async client lifecycle leaks
   - Risk: creating many unmanaged `httpx.AsyncClient` instances can leak resources.
   - Mitigation: keep one client per provider instance and ensure FastMCP ownership model is documented; add follow-up to verify graceful close behavior during app shutdown.

3. API compatibility for external imports
   - Risk: external code importing `OpenApiMcpProvider` breaks.
   - Mitigation: include changelog note and, if needed, temporary alias shim in a separate deprecation PR.

4. Test refactor drift
   - Risk: tests still patch deleted module paths.
   - Mitigation: batch-update patch targets to `drunk_ai_proxy.proxies.mcp.proxy_provider.*` and run targeted regression.

## Test Plan

Run focused tests first:

```bash
/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest tests/test_openapi_mcp_provider.py tests/test_mcp_proxy_provider.py tests/test_mcp_proxy_provider_extended.py tests/test_proxies_init.py -q
```

Then run established regression subset:

```bash
/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest tests/test_api_auth_provider.py tests/test_auth_pass_through.py tests/test_azure_oauth.py tests/test_openapi_mcp_provider.py tests/test_mcp_proxy_provider.py tests/test_mcp_proxy_provider_extended.py tests/test_llm_proxies_provider.py tests/test_llm_websocket_provider.py tests/test_llm_websocket_transport.py -q
```

## Rollout Notes

1. Merge consolidation with tests + changelog in one PR to avoid transient import breakage.
2. Call out `OpenApiMcpProvider` removal in release notes.
3. If downstream users depend on direct class import, publish migration guidance: use `McpProxyProvider` + `spec_type: openapi` configs.

## Sources Consulted

- https://gofastmcp.com/servers/providers/proxy
- https://gofastmcp.com/servers/composition
- https://www.python-httpx.org/async/
- https://www.python-httpx.org/advanced/clients/
