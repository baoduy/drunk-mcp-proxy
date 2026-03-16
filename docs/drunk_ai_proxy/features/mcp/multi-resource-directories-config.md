# MCP Multi-Folder Resource Configuration Plan

## Status

- Phase: Planned
- Priority: High
- Scope: Enforce multiple `skills`, `prompts`, and `agents` directories per MCP entry using the new schema only.

## Objective

Enable this YAML shape for MCP resources:

```yaml
- path: /resources
  spec_type: mcp
  skills:
    dirs:
      - skills/dknet
      - skills/dotnet
  prompts:
    - prompts/custom
    - prompts/dotnet
  agents:
    - agents/core
    - agents/dotnet
    - agents/tools
```

and remove support for legacy single-folder keys:

- `skill_dir`
- `prompt_dir`
- `agents_dir`

## Current State (Codebase Findings)

- `McpConfig` currently models only single-folder fields (`skill_dir`, `prompt_dir`, `agents_dir`) and validates MCP entries against those fields.
- Runtime provider creation uses only single-folder values:
  - skills in `base_provider.py`
  - prompts in `proxy_provider.py`
  - agents in `base_provider.py`
- Prompt-only detection and proxy build readiness use `prompt_dir` checks.
- Existing custom providers already support multiple roots (`CustomSkillsDirectoryProvider`, `CustomAgentsDirectoryProvider`), but MCP wiring currently passes only one root.
- Tests are heavily tied to single-folder keys across config and MCP provider test suites.

## Design Decisions

1. **New schema is mandatory**
   - Reject legacy keys (`skill_dir`, `prompt_dir`, `agents_dir`) during config validation.
   - Treat this as a deliberate breaking change.

2. **Canonical internal representation**
   - Use only list-based resource fields in `McpConfig`.
   - Runtime logic should consume list-based accessors only.

3. **Conflict handling for mixed configs**
   - If legacy keys and new keys are mixed in one MCP entry, fail validation with a clear error.
   - Rationale: avoid ambiguous behavior and force one canonical structure.

4. **Validation behavior**
   - For `spec_type: mcp`, consider MCP config valid when any of these exist:
     - `spec_file`
     - `mcp_servers`
     - non-empty prompt directories list
     - non-empty agents directories list
   - non-empty skills directories list

5. **Logging and security conventions**
   - Keep existing project logging approach: log exception types only.

## Proposed Schema Changes

### `utils/config_yaml.py`

Add new fields to `McpConfig`:

- `skills: SkillsConfig`
  - `dirs: list[str]`
- `prompts: list[str]`
- `agents: list[str]`

Remove legacy fields from `McpConfig`:

- `skill_dir`
- `prompt_dir`
- `agents_dir`

Add accessors in `McpConfig`:

- `get_skill_dirs() -> list[str]`
- `get_prompt_dirs() -> list[str]`
- `get_agent_dirs() -> list[str]`

Add model-level post-validation to:

- validate required list structure and non-empty paths
- validate string list cleanliness (non-empty paths)
- keep failure messages explicit and actionable

## Runtime Changes

### `proxies/mcp/base_provider.py`

- Refactor `_create_skill_proxy()` to use `config.get_skill_dirs()` and pass all resolved paths as `roots=[...]` to `CustomSkillsDirectoryProvider`.
- Refactor `_create_agent_proxy()` to aggregate valid directories and pass `roots=[...]` to `CustomAgentsDirectoryProvider`.
- Keep behavior resilient: skip missing/empty directories with warnings; proceed with remaining roots.

### `proxies/mcp/proxy_provider.py`

- Refactor `_create_prompt_proxy()` to iterate all effective prompt dirs.
- Register prompts from multiple directories into the same MCP instance.
- Prevent collisions by preserving current duplicate-name handling at prompt loader/provider layer.

### `proxies/mcp/mcp_proxy_builder.py`

- Replace single `prompt_dir` readiness check with list-based check over configured prompt directories.

### `proxies/prompt/prompt_provider.py` and `proxies/prompt/prompt_loader.py`

- Introduce multi-root prompt loading path:
  - either expand loader to accept multiple roots
  - or instantiate one loader/provider per root and merge templates before registration
- Standardize prompt-name collision strategy across directories (first wins + warning, or deterministic precedence).

## Documentation Changes

- Update `data/config.yaml` examples to show both:
   - required multi-folder shape
- Add migration section in docs explaining strict old-to-new mapping and validation failures for legacy keys.
- Update `CHANGE_LOGS.md` under `[Unreleased]` once implementation lands.

## Test Plan

## Unit Tests

1. `tests/test_config_yaml.py`
   - parse new fields (`skills.dirs`, `prompts`, `agents`)
   - reject legacy keys (`skill_dir`, `prompt_dir`, `agents_dir`)
   - reject mixed old+new payloads

2. `tests/test_config_yaml_integration.py`
   - MCP validation acceptance for new schema
   - validation errors for empty lists/invalid paths

3. `tests/test_mcp_proxy_provider.py`
   - `_create_skill_proxy` with multiple roots
   - `_create_prompt_proxy` with multiple prompt dirs
   - `_create_agent_proxy` with multiple roots
   - partial-missing-dir behavior (some roots invalid)

4. Prompt tests
   - add/update tests for multi-dir loading and deterministic duplicate handling

## Regression Tests

- Remove or rewrite legacy single-folder tests to assert validation errors.
- Run targeted suites first, then broader MCP/LLM tests:
  - `python -m pytest tests/test_config_yaml.py tests/test_config_yaml_integration.py -q`
  - `python -m pytest tests/test_mcp_proxy_provider.py tests/test_mcp_proxy_provider_extended.py -q`
  - `python -m pytest tests/test_openapi_mcp_provider.py tests/test_llm_proxies_provider.py -q`

## Rollout Plan

### Phase 1: Schema Enforcement

- Introduce/lock in new fields and remove legacy fields.
- Add explicit validation errors for legacy keys.

### Phase 2: Runtime Adoption

- Update skill/prompt/agent wiring to consume list APIs.
- Ensure prompt-only and builder checks use effective prompt list.

### Phase 3: Docs + Migration Guide

- Publish examples and migration notes.
- Mark old keys as removed and provide migration mapping.

### Phase 4: Stabilization

- Run full test suite and fix regressions.
- Collect user feedback on collision behavior and ergonomics.

## Risks and Mitigations

1. **Prompt name collisions across directories**
   - Mitigation: deterministic precedence + explicit warning logs.

2. **Behavior drift for existing configs**
   - Mitigation: provide explicit migration guide and fail-fast validation messages.

3. **Ambiguous precedence when old and new keys coexist**
   - Mitigation: disallow coexistence and fail validation.

4. **Runtime startup fragility from invalid paths**
   - Mitigation: skip invalid roots with warnings; continue loading valid ones.

## Acceptance Criteria

- New multi-folder MCP config loads successfully.
- Legacy config fails validation with clear actionable errors.
- Mixed old+new config fails validation with clear actionable errors.
- Skills/prompts/agents can be loaded from multiple directories in one MCP entry.
- Existing test suites pass with added multi-folder coverage.

## Sources Consulted

- Pydantic validators: https://docs.pydantic.dev/latest/concepts/validators/
- Pydantic aliasing and compatibility patterns: https://docs.pydantic.dev/latest/concepts/alias/
- Feature rollout and safe migration principles: https://martinfowler.com/articles/feature-toggles.html
