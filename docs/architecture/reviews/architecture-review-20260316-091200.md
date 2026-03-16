# Architecture Review — `src/drunk_ai_proxy/drunk_ai_proxy`

**Status:** PLANNED → [Refactor Plan](../../refactoring/refactor-plan-20260313-153911.md)

## Scope + Assumptions
- Scope reviewed: all Python modules under `src/drunk_ai_proxy/drunk_ai_proxy` (67 files; inventory produced via codebase scan).
- Priority lens applied per repo constraints: OOP/class-per-module first, then method-level SRP, library-native usage, DRY, SOLID, and best-practice conformance.
- `__init__.py` re-export modules and `__main__.py` entrypoints are treated as packaging exceptions unless they contain business logic.
- FastAPI and FastMCP guidance was cross-checked against current docs (`/fastapi/fastapi`, `/jlowin/fastmcp`, `/prefecthq/fastmcp`).

## Architecture Scorecard (0–5)
- OOP / class-per-module: **2.5/5**
- Library-native usage: **3.5/5**
- DRY / reuse: **3.0/5**
- SOLID compliance: **3.0/5**
- Layering / dependency direction: **2.5/5**
- Security architecture: **3.5/5**
- Naming / cohesion: **3.5/5**
- Testability / DI boundaries: **3.0/5**

## OOP/Class Findings (P0)

### P0-1: Procedural compatibility layer reintroduced at module level
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/middleware_provider.py`
- Evidence:
  - Primary class exists: `MiddlewareProvider` at line 36.
  - Module-level builders (outside class): `_parse_csv` line 131, `_create_cors_middleware` line 136, `get_middlewares` line 184.
- Violation type: procedural logic outside class, duplicated orchestration path.
- Recommended primary class: `MiddlewareProvider` (already present).
- Move/Change:
  - Keep one construction path: class `build()`.
  - Replace module-level compatibility functions with thin pass-through to a `MiddlewareProvider` instance, or remove shims after callsite migration.

### P0-2: Security module is function-first with class alias wrapper
- File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/security.py`
- Evidence:
  - Top-level business/security functions: `sanitize_error_response` line 31, `validate_url` line 148, others.
  - Wrapper class added late: `SecurityUtils` line 515, plus function alias rebinding from line 533.
- Violation type: mixed responsibility and dual API surface (function API + class API).
- Recommended primary class: `SecurityService` (single canonical class API).
- Move/Change:
  - Move helper implementations into class methods (static/class methods as appropriate).
  - Keep a minimal compatibility import surface in `utils/__init__.py`, not in-module alias rebinding.

### P0-3: Utility modules without primary class for business-facing logic
- Files:
  - `src/drunk_ai_proxy/drunk_ai_proxy/utils/env_resolver.py` (`resolve_env_var` line 20, `resolve_env_vars` line 129)
  - `src/drunk_ai_proxy/drunk_ai_proxy/utils/config_yaml_uri.py` (function-only URI generation)
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/resource_path_utils.py` (`get_root_namespace` line 8)
- Violation type: missing primary class in modules used by runtime orchestration.
- Recommended primary classes:
  - `EnvResolver`
  - `ConfigYamlUriBuilder`
  - `ResourcePathNamespaceResolver`
- Move/Change:
  - Encapsulate parsing rules and normalization logic in class methods.
  - Keep module-level functions only as short compatibility adapters during migration.

### P0-4: Runtime module-level environment initialization
- File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/env.py`
- Evidence:
  - Runtime calls at import time (e.g., `CONFIG_DIR` line 72, `SERVER_NAME` line 85, `AUTH_ENABLED` line 116).
- Violation type: module-level executable initialization and mutable runtime state capture.
- Recommended primary class: `EnvConfig` (or `EnvSettingsProvider`).
- Move/Change:
  - Centralize env reads in class construction or lazy getters.
  - Provide one frozen snapshot for startup, pass via DI where needed.

### P0-5: Layering breach (proxies depending on app layer)
- Files:
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/resource/on_demand_remote_resource_service.py` line 27
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/prompt/remote_prompt_provider.py` line 16
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/remote_skill_provider.py` line 20
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/remote_agent_provider.py` line 18
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/base_provider.py` lines 294, 360, 400
- Violation type: dependency direction violation (`proxies -> app`).
- Recommended primary class impact:
  - Keep proxy classes, but inject `TokenStore`/cache protocol from composition root (`app/server`).
- Move/Change:
  - Introduce constructor-injected `TokenStore`/`CacheAccessor` protocols at `utils/protocols.py` level and remove direct `app.cache_provider` imports from proxy layer.

## Method SRP Findings (P0.5)

### M1: `MCPProxyServer.async_run`
- Path: `src/drunk_ai_proxy/drunk_ai_proxy/app/server.py:169`
- Mixed concerns: startup logging, config load, provider construction, audit eventing, server startup, exception mapping.
- Proposed private helpers:
  - `_load_runtime_config()`
  - `_build_mcp_services(config_provider)`
  - `_build_llm_mounts(config_provider)`
  - `_emit_startup_audit()`
  - `_run_server()`
- Extraction sequence: config load -> service build -> audit/log -> server run.

### M2: `MCPProxyServer._async_start_server`
- Path: `src/drunk_ai_proxy/drunk_ai_proxy/app/server.py:72`
- Mixed concerns: app assembly, mounting, uvicorn construction, telemetry, process serving.
- Proposed private helpers:
  - `_build_starlette_app()`
  - `_create_uvicorn_server(app)`
  - `_audit_server_start(host, port)`
- Optional static helper: `_resolve_bind_address()`.

### M3: `LlmProxiesProvider._anthropic_messages_endpoint`
- Path: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/proxies_provider.py:499`
- Mixed concerns: HTTP body parsing, schema validation, protocol conversion, OpenAI dispatch, streaming/non-stream response conversion.
- Proposed private helpers:
  - `_validate_anthropic_messages_payload(body)`
  - `_build_anthropic_openai_payload(body, model_name)`
  - `_dispatch_anthropic(provider_name, payload)`
  - `_format_anthropic_response(response, stream, model_id)`
- Optional static helper: payload field assertions.

### M4: `McpBaseProvider._add_remote_{skill,agent,prompt}_proxy`
- Path: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/base_provider.py:273,339,380`
- Mixed concerns: config conflict warnings, cache/http client creation, provider factory wiring, registration semantics.
- Proposed private helpers:
  - `_build_remote_provider_runtime()`
  - `_warn_local_remote_overlap(resource_type)`
  - `_attach_remote_resource_providers(resource_type, entries, register_fn)`
- Extraction sequence: overlap warning -> runtime creation -> attachment.

## Library-Native Findings

### L1: No-op `mount` implementation on concrete provider
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/websocket_provider.py:116-126`
- Hand-rolled pattern: class inherits base provider requiring `mount`, but concrete method is a no-op `pass`.
- Library-native replacement:
  - Use explicit endpoint registration through FastAPI router only, and remove `mount` contract from classes that do not mount.
  - Align provider contracts with FastAPI routing primitives (`APIRouter`) and FastMCP provider abstractions where mounting is real.
- Effort: **M**

### L2: OpenAPI docs assembled manually on Starlette root
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/swagger_provider.py`
- Hand-rolled pattern: custom schema assembly for mounted LLM/MCP endpoints.
- Library-native replacement:
  - Prefer FastAPI-native OpenAPI for FastAPI sub-app endpoints and expose mounted app docs where feasible.
  - Keep custom synthesis only for cross-app merged docs if truly required.
- Effort: **M/L** (depends on requirement for single merged spec).

### L3: Auth/middleware setup mostly library-native and good
- Positive evidence:
  - Router-level dependency injection via FastAPI `Depends` in `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/router.py`.
  - FastMCP auth providers constructed explicitly in `src/drunk_ai_proxy/drunk_ai_proxy/app/auth_type_registry.py`.
- Action: retain; no immediate refactor needed.

## DRY/Reuse Findings

### D1: Dual middleware builders duplicate behavior
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/middleware_provider.py`
- Duplication: class methods and module-level `_create_*` functions both build same middleware list.
- Proposed abstraction: keep one builder in `MiddlewareProvider`; compatibility wrapper calls only `MiddlewareProvider(cache).build()`.
- Expected gain: fewer drift bugs and easier middleware policy changes.

### D2: Repeated remote resource bootstrap in MCP base provider
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/base_provider.py:273-417`
- Duplication: each resource type repeats cache/client creation + overlap warning + attach call.
- Proposed abstraction: `RemoteProviderBootstrapContext` + single `_mount_remote_resources(resource_type, ...)`.
- Expected gain: lower regression risk across agent/skill/prompt paths.

### D3: Security API duplicated via alias rebinding
- File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/security.py:533+`
- Duplication: functions and class static aliases expose same behavior in two forms.
- Proposed abstraction: one canonical class API + stable imports from package init.
- Expected gain: clearer ownership and easier static analysis.

## SOLID Findings

### S1 (SRP): `MCPProxyServer` orchestrates too many concerns
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/server.py`
- Evidence: `_async_start_server` + `async_run` mix bootstrap, composition, serving, and telemetry.
- Minimal fix: introduce `ServerBootstrapper` collaborator and delegate composition steps.

### S2 (DIP): Proxy layer depends on concrete app cache implementation
- Files: proxy imports listed in P0-5.
- Evidence: direct imports of `CacheProvider`/`TTLAsyncKeyValue` from `app`.
- Minimal fix: depend on `TokenStore`/cache protocols from `utils/protocols.py`, inject at composition root.

### S3 (OCP): AuthTypeRegistry still requires edits for every new provider
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/auth_type_registry.py`
- Evidence: central `_REGISTRY` build in `_ensure_registry` (line 120+) and explicit factory methods.
- Minimal fix: allow provider registration hooks/extensions to reduce central modification pressure.

### S4 (ISP): `LlmBaseProvider` mount contract forces no-op implementation
- Files: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/base_provider.py`, `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/websocket_provider.py`
- Evidence: `mount` required, `LlmWebSocketProvider.mount` is `pass`.
- Minimal fix: split interface/ABC into mountable vs endpoint-only capabilities.

## Best Practices Findings

### B1: `Any` usage remains broad in business paths
- Examples:
  - `src/drunk_ai_proxy/drunk_ai_proxy/app/server.py:27,66`
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/prompt/prompt_provider.py:94`
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/anthropic_provider.py` (multiple)
- Recommendation: reduce `Any` at boundaries first (request/response models, typed payload aliases).

### B2: Missing module docstring in key provider module
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/proxies_provider.py`
- Evidence: file starts directly with `from __future__ import annotations` at line 1.
- Recommendation: add concise module docstring per project convention.

### B3: Sensitive input fragment logged on auth failure
- File: `src/drunk_ai_proxy/drunk_ai_proxy/auth/api_auth_provider.py:53`
- Evidence: `logger.info("Token verification failed: %s", token[-4:])` logs attacker-supplied token suffix.
- Recommendation: avoid logging token-derived fragments; log request metadata or hashed fingerprint only.

## Prioritized Recommendations

1. **Eliminate P0 module-level procedural paths in middleware/security/env utility modules**
   - Rationale: hard project rule; highest architecture drift source.
   - Impact: High, Effort: **M**, Risk: **Low/Med**.

2. **Fix layering violations by injecting cache/token interfaces into proxy layer**
   - Rationale: reduces coupling and addresses known architecture guardrail breaches.
   - Impact: High, Effort: **M**, Risk: **Med**.

3. **Split high-complexity orchestrators (`MCPProxyServer`, Anthropic endpoint path)**
   - Rationale: improves SRP, testability, and rollback safety.
   - Impact: High, Effort: **M**, Risk: **Med**.

4. **Collapse duplicate middleware/security APIs into single canonical construction path**
   - Rationale: DRY + reduced behavior divergence risk.
   - Impact: Med, Effort: **S/M**, Risk: **Low**.

5. **Refine LLM provider contracts (mountable vs endpoint-only)**
   - Rationale: remove interface mismatch and no-op methods.
   - Impact: Med, Effort: **M**, Risk: **Med**.

6. **Tighten best-practice conformance (`Any`, module docstrings, token logging)**
   - Rationale: maintainability + security hygiene.
   - Impact: Med, Effort: **S**, Risk: **Low**.

## Migration Strategy

### Phase 1 (Quick wins, 1–2 PRs)
- Convert `app/middleware_provider.py` and `utils/security.py` to single class-led public API (keep temporary adapters).
- Remove token suffix logging from `auth/api_auth_provider.py`.
- Add missing module docstrings for high-traffic modules.

### Phase 2 (Structural refactor, 2–4 PRs)
- Introduce proxy-facing cache protocols and inject from `app/server.py` composition root.
- Remove `proxies -> app.cache_provider` imports.
- Split `MCPProxyServer.async_run` / `_async_start_server` into focused collaborators.

### Phase 3 (Contract hardening, 1–2 PRs)
- Split `LlmBaseProvider` interface into mountable/non-mountable capabilities.
- Normalize remote resource bootstrap path in `McpBaseProvider`.

### Compatibility Notes
- Maintain compatibility adapters for one release cycle for module-level helper imports.
- Keep public import paths stable in package `__init__.py` while internals migrate.

### Rollback Path
- PR-by-PR rollback possible by preserving adapter functions and feature flags for DI path changes.
- Defer interface split if downstream tests indicate broad usage of old ABC contract.

## Validation Plan
- Targeted tests:
  - `python -m pytest tests/test_starlette_app.py tests/test_middleware.py tests/test_server.py -q`
  - `python -m pytest tests/test_llm_proxies_provider.py tests/test_llm_websocket_provider.py -q`
  - `python -m pytest tests/test_mcp_proxy_provider.py tests/test_mcp_proxy_provider_extended.py -q`
- Static checks:
  - `pyright`
  - `flake8 src tests`
- Architecture guardrails:
  - Re-run import-linter checks after proxy cache DI refactor to confirm `proxies -> app` violations are reduced/removed.

## Open Questions
- Is a single merged OpenAPI document across mounted Starlette/FastAPI apps a hard requirement, or can docs be split per mounted app?
- Do you want immediate hard removal of compatibility module-level helpers, or one release-cycle deprecation shims?