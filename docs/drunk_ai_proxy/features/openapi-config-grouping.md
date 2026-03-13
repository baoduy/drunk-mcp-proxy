# OpenAPI Sub-Config Grouping Plan

## Goal

Restructure MCP config so OpenAPI-related fields live under `open_api`, with OpenAPI spec payload loaded into `open_api.spec_data`, while preserving clear spec-type branching:

- `spec_type: mcp` → use `mcp_servers` (validated for MCP usage)
- `spec_type: openapi` → use `open_api` block (validated after loading `open_api.spec_file`)

## Requested target shape

```yaml
mcp:
  - enabled: true
    path: /deepsea
    spec_type: openapi
    open_api:
      spec_file: openapi/deepsea.openapi.json
      base_url: https://deepsea-fxrate.tsv2.dev
      filters:
        methods: [GET, POST, PUT]
        tags: [CurrencyPairs]
```

`spec_data` is moved under `open_api` and populated from `open_api.spec_file`.

## Current-state findings (codebase)

- `McpConfig` currently stores OpenAPI and MCP fields together (`spec_file`, `base_url`, `filters`, `mcp_servers`, top-level `spec_data`) in `src/drunk_ai_proxy/drunk_ai_proxy/utils/config_yaml.py`.
- `McpConfig.load_spec_data()` currently loads file-based specs into top-level `spec_data` for both spec types; for MCP it also performs JSON Schema validation.
- `OpenApiMcpProvider` currently reads `config.base_url`, `config.filters`, and `config.spec_data`.
- `McpProxyProvider` currently reads `config.spec_data` to build MCP proxy and warns when missing.
- `StaticProxiesProvider` already separates processing by `spec_type`; this branch point should remain canonical.

## Design decisions

1. Introduce explicit `OpenApiConfig` nested model.
2. Keep `McpConfig` as top-level orchestrator but delegate OpenAPI storage/validation/loading into `open_api`.
3. Keep `spec_type` as the single routing switch.
4. Preserve current MCP resource-only behavior (skills/prompts/agents without `mcp_servers`) while enforcing `mcp_servers` correctness whenever MCP proxy data is expected.
5. Use phased compatibility for one release to avoid breaking existing configs abruptly.

## Proposed model changes

### New model

Add in `src/drunk_ai_proxy/drunk_ai_proxy/utils/config_yaml.py`:

- Rename `class McpFilters` to `class OpenApiFilters`.
- `class OpenApiConfig(ConfigBaseModel)`
  - `spec_file: str | None`
  - `base_url: str | None`
   - `filters: OpenApiFilters | None`
  - `spec_data: dict[str, Any] | None = Field(default=None, exclude=True)`

### McpConfig updates

- Add `open_api: OpenApiConfig | None = Field(default=None, alias="openApi")`
- Replace any remaining `McpConfig.filters` typing/references with `OpenApiFilters` via `open_api.filters`.
- Deprecate top-level OpenAPI fields in `McpConfig`:
  - `spec_file`
  - `base_url`
  - `filters`
  - `spec_data`
- Add compatibility normalizer (`@model_validator(mode="before")`):
  - If `spec_type == openapi` and legacy top-level fields are present, synthesize `open_api` from them.
  - If both legacy and `open_api` are present, prefer `open_api` and log a warning.

## Validation and loading flow

### For `spec_type == openapi`

Validation sequence in `after_model_validator`:

1. Ensure `open_api` exists.
2. Load `open_api.spec_file` from `CONFIG_DIR` into `open_api.spec_data`.
3. Resolve env vars in loaded payload.
4. Validate minimal OpenAPI document requirements post-load:
   - root is object
   - `openapi` present
   - `info` present
   - at least one of `paths`, `components`, or `webhooks` present
5. Validate runtime client requirements:
   - `open_api.base_url` required unless future auth mode explicitly supports omission.

### For `spec_type == mcp`

Validation sequence in `after_model_validator`:

1. Validate resource directory lists (`skills/prompts/agents`) as today.
2. Build MCP proxy input from `mcp_servers` when provided:
   - `self.spec_data = {"mcpServers": ...}` (top-level retained temporarily for compatibility)
3. Validate MCP payload through `McpConfig` Pydantic model and explicit field validators.
4. Keep prompt/skill/agent-only configs valid without requiring `mcp_servers`.

## Provider/runtime refactor plan

### OpenAPI provider changes

File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/openapi_provider.py`

- Replace reads of:
  - `config.base_url` → `config.open_api.base_url`
  - `config.filters` → `config.open_api.filters`
  - `config.spec_data` → `config.open_api.spec_data`
- Add defensive errors when `open_api` or `open_api.spec_data` is missing.

### MCP provider changes

File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/proxy_provider.py`

- Keep MCP path behavior using top-level `config.spec_data` during compatibility phase.
- In cleanup phase, optionally shift to `config.mcp_spec_data` helper (or equivalent) to avoid OpenAPI ambiguity.

### Static provider

File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/static_provider.py`

- No structural change required; continue spec-type partitioning.
- Add tests confirming that OpenAPI entries are processed only through `open_api` data path.

## Testing plan

### Unit tests to add/update

1. `tests/test_config_yaml.py`
   - Rename imports/usages from `McpFilters` to `OpenApiFilters`.
   - OpenAPI config parses from nested `open_api`.
   - `open_api.spec_file` loads into `open_api.spec_data`.
   - Post-load OpenAPI validation failures (missing `openapi`, missing `info`, missing `paths/components/webhooks`).
   - MCP branch validates `mcp_servers` structure and rejects invalid server specs.
   - Compatibility: legacy top-level OpenAPI fields auto-mapped to `open_api` (during transition).

2. `tests/test_openapi_mcp_provider.py`
   - `create_client()` uses `open_api.base_url`.
   - `create_proxy()` uses `open_api.spec_data` and `open_api.filters`.
   - Missing `open_api`/`spec_data` raises deterministic errors.

3. `tests/test_mcp_proxy_provider.py`
   - MCP `spec_type` continues using MCP-derived `spec_data`.
   - Prompt-only MCP config still skips MCP proxy creation without crashing.

4. `tests/test_config_yaml_integration.py`
   - End-to-end load of updated `data/config.yaml` structure with nested `open_api`.

### Regression command

Run:

```bash
/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest tests/test_config_yaml.py tests/test_config_yaml_integration.py tests/test_openapi_mcp_provider.py tests/test_mcp_proxy_provider.py -q
```

Then run broader targeted suite already used in repo notes.

## Migration strategy

### Phase 1 (non-breaking)

- Accept both old and new OpenAPI shapes.
- Emit warning for legacy top-level OpenAPI fields.
- Internally normalize to `open_api`.

### Phase 2 (breaking cleanup)

- Remove legacy top-level OpenAPI fields from `McpConfig`.
- Remove compatibility normalizer and related tests.
- Update docs/examples to nested-only schema.

## Documentation updates

Update after implementation:

- `data/config.yaml` sample OpenAPI entry.
- `README.md` OpenAPI section examples.
- `docs/drunk_ai_proxy/features/openapi/*` references still showing top-level `spec_file/base_url/filters`.
- `CHANGE_LOGS.md` under `[Unreleased]` with `### Changed`.

## Risks and mitigations

1. **Risk:** Breaking existing configs that still use top-level OpenAPI fields.
   - **Mitigation:** One-release compatibility shim with warning.

2. **Risk:** Confusion between MCP and OpenAPI `spec_data` ownership.
   - **Mitigation:** Explicit nested ownership (`open_api.spec_data`) and branch-specific loaders.

3. **Risk:** Provider assumptions about non-null fields.
   - **Mitigation:** Add explicit precondition checks with sanitized error handling.

4. **Risk:** Prompt/skill/agent MCP configs accidentally forced to include `mcp_servers`.
   - **Mitigation:** Preserve existing resource-only validity; only validate `mcp_servers` when MCP proxy payload is needed.

## Rollout notes

- Deploy Phase 1 with deprecation warnings first.
- Announce migration deadline for top-level OpenAPI keys.
- After config updates are complete, execute Phase 2 cleanup.

## Sources consulted

- https://docs.pydantic.dev/latest/concepts/validators/
- https://docs.pydantic.dev/latest/concepts/fields/
- https://swagger.io/specification/
