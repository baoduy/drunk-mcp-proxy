# Feature Plan: Per-MCP `codemode_enabled` Toggle (Local-Only)

## Goal
Allow Code Mode to be enabled/disabled per MCP config entry by adding a required `codemode_enabled` field under each `mcp` item in `data/config.yaml`, and remove `FASTMCP_CODEMODE_ENABLED` entirely.

## Current State (Code-Verified)

1. **Global-only toggle exists (to be removed)**
   - `drunk_ai_proxy/utils/env.py` defines `CODEMODE_ENABLED = get_env_bool("FASTMCP_CODEMODE_ENABLED", True)`.

2. **Code Mode decision is global and static**
   - `drunk_ai_proxy/proxies/mcp/mcp_proxy_builder.py`:
     - imports global `CODEMODE_ENABLED`.
     - `_get_code_mode_transforms()` returns transforms only based on global env flag.
     - `create_fastmcp_server()` always uses `get_transforms()` with no per-config parameter.

3. **MCP config model has no per-entry codemode field (yet)**
   - `drunk_ai_proxy/utils/config_yaml.py` (`McpConfig`) includes route flags (`enabled`, `path`, `spec_type`, resources/auth/openapi/mcp_servers/tags/spec_data), but no `codemode_enabled` field.

4. **MCP proxy construction path**
   - `McpProxyBuilder.build_mcp_proxy_configs()` creates one root `FastMCP` (`path="/"`) and then builds providers for each `McpConfig`.
   - `McpProxyProvider.create_proxy()` uses `McpProxyBuilder.create_fastmcp_server(...)` for non-root and openapi cases, and can reuse root for `path="/"`.

## Desired Behavior

### Configuration semantics
- New required field on each MCP item:
  - `codemode_enabled: true|false`
- No global fallback remains.

### Runtime semantics
- Code Mode transforms are applied per `FastMCP` instance according to that instance’s effective flag.
- Root server (`path="/"`) and non-root routes can differ in Code Mode behavior.
- Breaking-change note: existing configs must add `codemode_enabled` for every MCP entry.

## Design Decisions

1. **Use explicit per-route field in `McpConfig`**
   - Add `codemode_enabled: bool = Field(default=True, ...)`.
   - Local config is the only source for Code Mode state.

2. **Remove global env var completely**
   - Delete `FASTMCP_CODEMODE_ENABLED` and `CODEMODE_ENABLED` from env surface.
   - Remove all related docs/tests for that env variable.

3. **Move decision logic closer to server creation input**
   - Refactor `McpProxyBuilder` APIs to accept a resolved boolean for each server creation call.
   - Avoid hidden global reads deep in transform selection.

4. **Preserve existing root-path optimization**
   - Keep shared root behavior, but ensure root is created with root config’s effective Code Mode state.

## Implementation Plan

### Phase 1 — Extend MCP schema model
1. Update `drunk_ai_proxy/utils/config_yaml.py`:
   - Add field to `McpConfig`:
   - `codemode_enabled: bool = Field(default=True, description="Enable/disable FastMCP Code Mode for this MCP route.")`
2. Keep default `True` for safe migration while transitioning configs.
3. Optional hardening (follow-up): remove default and require explicit field once all configs are updated.

Acceptance criteria:
- `McpConfig.model_validate({...})` accepts `codemode_enabled`.
- Existing config files continue to validate during migration because of default.

### Phase 2 — Refactor builder to support per-instance toggles
1. Update `drunk_ai_proxy/proxies/mcp/mcp_proxy_builder.py`:
   - Refactor `_get_code_mode_transforms()` to accept `codemode_enabled: bool` (or equivalent resolved value).
   - Refactor `get_transforms(...)` to pass through resolved flag.
   - Refactor `create_fastmcp_server(server_name, server_version, codemode_enabled)`.
2. Remove any helper/function that reads global `CODEMODE_ENABLED`.

Acceptance criteria:
- Builder can create `FastMCP` with Code Mode on/off independent of process-global default.

### Phase 3 — Remove global env toggle surface
1. Update `drunk_ai_proxy/utils/env.py`:
   - Delete `CODEMODE_ENABLED` constant.
   - Delete `FASTMCP_CODEMODE_ENABLED` parsing/comments.
2. Update `.env` / `.env.sample` and config docs:
   - Remove `FASTMCP_CODEMODE_ENABLED` references.
   - Add per-MCP `codemode_enabled` examples in YAML docs.
3. Update changelog with explicit breaking/behavior note.

Acceptance criteria:
- No code/docs/tests reference `FASTMCP_CODEMODE_ENABLED`.
- Runtime behavior is driven only by `McpConfig.codemode_enabled`.

### Phase 4 — Wire per-config resolution through MCP proxy creation
1. In `build_mcp_proxy_configs(...)`:
   - Determine root config (path `/`) if present.
   - Create root server with root config `codemode_enabled`.
   - Pass root server to providers as before.
2. In `McpProxyProvider.create_proxy()`:
   - For non-root or openapi-created servers, call builder with this config’s `codemode_enabled`.
   - For root path using provided `root_mcp`, continue reuse without recreating.

Acceptance criteria:
- Different MCP paths can have different Code Mode states.
- Root path behavior remains stable.

### Phase 5 — Config and docs surface updates
1. Update `data/config.yaml` examples:
   - Add `codemode_enabled` to every MCP entry and document required usage.
2. Update user-facing docs where env var/features are listed (minimum: changelog + relevant configuration docs).
3. Add changelog entry under `[Unreleased]` in `CHANGE_LOGS.md`.

Acceptance criteria:
- Docs clearly explain local-only behavior and no global toggle.

### Phase 6 — Tests

#### Unit tests to add/update
1. `tests/test_config_yaml.py`
   - `McpConfig` accepts `codemode_enabled=True/False`.
   - Missing `codemode_enabled` yields `True` during migration phase (or validation error in strict follow-up phase).

2. `tests/test_mcp_proxy_provider.py` and/or `tests/test_mcp_proxy_provider_extended.py`
   - Verify `McpProxyBuilder.create_fastmcp_server` is called with expected codemode flag for:
     - root route
     - non-root route
     - openapi route
   - Verify behavior when `codemode_enabled` omitted uses model default only (no env interaction).

3. Add/extend tests around `mcp_proxy_builder` (new direct unit tests preferred)
   - `create_fastmcp_server(..., codemode_enabled=False)` does not attach transforms.
   - `create_fastmcp_server(..., codemode_enabled=True)` attaches Code Mode transforms.

4. Update env tests:
   - Remove `FASTMCP_CODEMODE_ENABLED`/`CODEMODE_ENABLED` assertions from `tests/test_env.py`.

#### Regression command set
- Targeted:
  - `python -m pytest tests/test_config_yaml.py tests/test_mcp_proxy_provider.py tests/test_mcp_proxy_provider_extended.py -q`
- Broader subset already used in repo:
  - `/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest tests/test_api_auth_provider.py tests/test_auth_pass_through.py tests/test_azure_oauth.py tests/test_mcp_proxy_provider.py tests/test_openapi_mcp_provider.py tests/test_llm_proxies_provider.py -q`

## Risks and Mitigations

1. **Risk: Unexpected root behavior changes**
   - Mitigation: explicit root-path tests (`path="/"` reuse + codemode state assertions).

2. **Risk: API signature churn in builder affects many tests**
   - Mitigation: update call sites in one cohesive refactor and adjust mocks in affected tests in same PR.

3. **Risk: Breaking-change confusion for operators currently using env toggle**
   - Mitigation: explicit migration notes with before/after examples and changelog callout.

4. **Risk: OpenAPI route unintentionally receives wrong toggle state**
   - Mitigation: dedicated openapi-path test verifying codemode argument wiring.

## Rollout Notes

- This is a behavior change because global env control is removed.
- Recommended rollout:
   1. add `codemode_enabled` to all MCP entries in `data/config.yaml`,
   2. deploy code that reads local config only,
   3. remove `FASTMCP_CODEMODE_ENABLED` from runtime env and deployment manifests.
- Observability: log effective codemode per route at server creation (boolean only; no sensitive data).

## Definition of Done
- [ ] `McpConfig` supports local `codemode_enabled` for each MCP entry.
- [ ] Builder/server creation accepts per-instance codemode setting.
- [ ] Root and non-root MCP paths respect per-route override.
- [ ] `FASTMCP_CODEMODE_ENABLED` removed from env, code, tests, and docs.
- [ ] Unit/integration tests updated and passing.
- [ ] Changelog and config documentation updated.

## Sources Consulted
- FastMCP transforms model and server-vs-provider transform layering: https://gofastmcp.com/servers/transforms
- Feature toggle design and layered configuration/override guidance: https://martinfowler.com/articles/feature-toggles.html
- Pydantic v2 field defaults/aliases/validation behavior: https://docs.pydantic.dev/latest/concepts/fields/

## Status
✅ Implementation completed on 13 March 2026.
✅ Add McpConfig codemode_enabled
✅ Refactor mcp_proxy_builder API
✅ Remove global env toggle
✅ Wire provider callsites
✅ Update config/docs/changelog
✅ Update and add tests
✅ Run targeted regressions
✅ Append plan status section
