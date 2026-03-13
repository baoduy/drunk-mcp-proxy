# Feature Plan: Remove Legacy MCP JSON Schema Validation

## Goal
Remove legacy MCP JSON Schema validation (`schemas/mcp.schema.json` + `jsonschema`) because configuration validation is already enforced by Pydantic models and field validators.

This plan covers runtime code cleanup, schema folder removal, Docker/build cleanup, environment variable cleanup, test migration, and documentation updates.

## Current State (Code-Verified)

### Runtime validation path (legacy)
- `drunk_ai_proxy/utils/config_yaml.py`
  - Imports `jsonschema`.
  - Imports `SCHEMA_DIR` from env.
  - Defines `_validate_mcp_schema()` that loads `mcp.schema.json` from `SCHEMA_DIR` and validates `self.spec_data`.
  - Calls `_validate_mcp_schema()` in `load_spec_data()` for `spec_type == mcp` when `spec_data` is present.

### Environment variable surface
- `drunk_ai_proxy/utils/env.py`
  - Defines `SCHEMA_DIR = get_env_string("FASTMCP_SCHEMA_DIR", "schemas")`.

### Build/runtime container surface
- `Dockerfile`
  - Copies `schemas/` into image.
  - Exposes `FASTMCP_SCHEMA_DIR` in runtime `ENV`.

### Dependency surface
- `src/drunk_ai_proxy/pyproject.toml`
  - Runtime dependency includes `jsonschema>=4.0.0`.

### Config/docs/tests surface
- `.env.sample` includes `FASTMCP_SCHEMA_DIR` and schema-dir comments.
- `tests/test_env.py` has SCHEMA_DIR/FASTMCP_SCHEMA_DIR assertions.
- Multiple docs still reference `FASTMCP_SCHEMA_DIR` and `schemas/`.
- `schemas/mcp.schema.json` appears to be the only schema artifact under `schemas/`.

## Desired End State
- No runtime dependency on `jsonschema` or `schemas/mcp.schema.json`.
- MCP config validation relies on Pydantic model validation and existing explicit validators in `McpConfig`.
- `FASTMCP_SCHEMA_DIR` fully removed from code and docs.
- Docker image no longer copies `schemas/` nor exports schema env var.
- `schemas/` folder removed from repository (if empty after removal).

## Scope

### In scope
1. Remove `_validate_mcp_schema()` and all related imports/usages.
2. Remove `SCHEMA_DIR` and `FASTMCP_SCHEMA_DIR` usage.
3. Remove `jsonschema` from package dependencies.
4. Remove `schemas/mcp.schema.json` and `schemas/` folder.
5. Update Dockerfile and env templates.
6. Update tests and documentation.
7. Add changelog entry under `[Unreleased]`.

### Out of scope
- Reworking overall config model structure beyond schema-removal needs.
- New schema-generation pipeline.
- Broader config compatibility refactors unrelated to schema validation.

## Implementation Plan (Phased)

### Phase 1 — Runtime code cleanup (single PR)
1. `drunk_ai_proxy/utils/config_yaml.py`
   - Remove `import jsonschema`.
   - Remove `SCHEMA_DIR` import.
   - Delete `_validate_mcp_schema()` method.
   - Remove call to `_validate_mcp_schema()` in `load_spec_data()`.
   - Keep existing `McpConfig` validation behavior:
     - `_validate_fields()`
     - directory validations
     - OpenAPI validation path (`_validate_openapi_spec`) unchanged.

2. `drunk_ai_proxy/utils/env.py`
   - Remove `SCHEMA_DIR` constant.
   - Remove schema-related comments.

Acceptance criteria:
- No references remain to `SCHEMA_DIR`, `FASTMCP_SCHEMA_DIR`, `jsonschema.validate`, or `mcp.schema.json` in runtime code.

### Phase 2 — Build and dependency cleanup
1. `src/drunk_ai_proxy/pyproject.toml`
   - Remove `jsonschema>=4.0.0` dependency.

2. `Dockerfile`
   - Remove `COPY ... schemas/ ./schemas/` line.
   - Remove `FASTMCP_SCHEMA_DIR=...` from `ENV` block.

3. Repo cleanup
   - Delete `schemas/mcp.schema.json`.
   - Remove `schemas/` directory if empty.

Acceptance criteria:
- Package installs and runtime image build without schema assets.
- No dependency lock/build errors due to removed `jsonschema`.

### Phase 3 — Tests and documentation migration
1. Tests
   - `tests/test_env.py`
     - Remove `test_schema_dir_default` and any assertions on `SCHEMA_DIR`.
   - Add/adjust tests in `tests/test_config_yaml.py` / integration tests to ensure MCP configs still validate correctly via Pydantic rules (positive + negative cases already partially exist).

2. Templates/docs
   - `.env.sample`: remove `FASTMCP_SCHEMA_DIR` and related comments.
   - Update references in:
     - `docs/drunk_ai_proxy/configuration/environment-variables.md`
     - `docs/drunk_ai_proxy/deployment/docker.md`
     - `docs/drunk_ai_proxy/architecture/drunk-ai-proxy-module-reference.md`
     - `docs/drunk_ai_proxy/development/drunk-ai-proxy-operator-runbook.md`
     - `docs/drunk_ai_proxy/features/openapi-config-grouping.md` (replace planned schema-validation step with Pydantic validation wording)
     - `CHANGE_LOGS.md` under `[Unreleased]` (`Changed`/`Removed`/`Fixed` sections as appropriate).

Acceptance criteria:
- No docs/examples advertise `FASTMCP_SCHEMA_DIR`.
- Changelog clearly marks this as removed behavior.

### Phase 4 — Verification and release safety
Run validation in this order:
1. Targeted tests first:
   - `python -m pytest tests/test_env.py tests/test_config_yaml.py tests/test_config_yaml_integration.py -q`
2. Then broader regression subset used in repository workflows:
   - `/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest tests/test_api_auth_provider.py tests/test_auth_pass_through.py tests/test_azure_oauth.py tests/test_mcp_proxy_provider.py tests/test_openapi_mcp_provider.py tests/test_llm_proxies_provider.py -q`
3. Static checks:
   - `pyright`
   - `flake8 src tests`

Release-note guidance:
- Mark `FASTMCP_SCHEMA_DIR` and schema-file validation as removed.
- Note that MCP config validation is now solely model/validator-based.

## Risks and Mitigations

1. **Risk: Hidden consumers rely on `FASTMCP_SCHEMA_DIR`.**
   - Mitigation: Explicit changelog + docs updates; verify no code references remain via global grep.

2. **Risk: Validation strictness changes subtly without JSON Schema layer.**
   - Mitigation: Add/keep tests for MCP config edge cases; compare failure messages/paths in critical tests.

3. **Risk: Docker users mounting `schemas/` expect it to exist.**
   - Mitigation: Update Docker docs and examples in same PR; include migration note: schema mount no longer required.

4. **Risk: Dependency transitive assumptions in CI/build.**
   - Mitigation: Run full install/build path after `jsonschema` removal.

## Rollout Strategy

### Recommended rollout
- Perform as one focused cleanup PR if repository is pre-1.0 and change cadence is fast.
- If stricter compatibility is needed, use two-step rollout:
  1. deprecate env var/docs first,
  2. remove in next release.

### Communication
- Add explicit `Removed` changelog bullets:
  - `FASTMCP_SCHEMA_DIR` env variable.
  - `schemas/mcp.schema.json` runtime validation.
- Add migration note in docs: “No schema directory is required anymore.”

## Definition of Done
- [ ] No `jsonschema` import/use in runtime code.
- [ ] No `SCHEMA_DIR` / `FASTMCP_SCHEMA_DIR` in code, Dockerfile, `.env.sample`, or docs.
- [ ] `schemas/` artifacts removed.
- [ ] Tests updated and passing.
- [ ] Changelog updated under `[Unreleased]`.

## Sources consulted
- https://docs.pydantic.dev/latest/concepts/models/
- https://semver.org/
- https://keepachangelog.com/en/1.1.0/

## Notes from best practices applied
- Prefer single authoritative validation layer to avoid drift/duplication (Pydantic model validation).
- Treat env-var removal as API surface change; communicate via changelog and docs.
- Keep removal cohesive (code + build + docs + tests in one change set) to avoid partial breakages.

## Status

✅ Implementation completed on 13 March 2026.

✅ Remove `_validate_mcp_schema()` and all related imports/usages.
✅ Remove `SCHEMA_DIR` and `FASTMCP_SCHEMA_DIR` usage.
✅ Remove `jsonschema` from package dependencies.
✅ Remove `schemas/mcp.schema.json` and `schemas/` folder.
✅ Update Dockerfile and env templates.
✅ Update tests and documentation.
✅ Add changelog entry under `[Unreleased]`.
✅ Run targeted config/env verification tests.
✅ Run broader provider regression subset.
✅ Run static checks (`pyright`, `flake8`).
