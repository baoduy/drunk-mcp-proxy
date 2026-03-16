# Architecture Review — `src/drunk_ai_proxy/drunk_ai_proxy` (Re-review)

## Scope + Assumptions
- Scope: all Python modules under `src/drunk_ai_proxy/drunk_ai_proxy`, with a focused re-check of `app/app_config_provider.py`.
- Priority order enforced: OOP/class-per-module (mandatory) → method-level SRP → library-native usage → DRY → SOLID → best practices.
- `__main__.py`/`main.py` entrypoints are treated as packaging exceptions only when they stay thin.
- Library-native recommendations are grounded in current docs from Context7: `/fastapi/fastapi` and `/prefecthq/fastmcp`.

## Architecture Scorecard (0–5)
- OOP/class-per-module: **2.8/5**
- Library-native usage: **3.6/5**
- DRY/reuse: **3.1/5**
- SOLID compliance: **3.2/5**
- Layering/dependency direction: **2.7/5**
- Security architecture: **3.7/5**
- Naming/cohesion: **3.8/5**
- Testability/DI boundaries: **3.1/5**

## OOP/Class Findings (P0 — first)

### P0-1: `app/middleware_provider.py` still has procedural module-level orchestration
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/middleware_provider.py`
- Violation type: procedural logic outside primary class.
- Evidence:
	- Primary class exists: `MiddlewareProvider` at line 37.
	- Module-level business helpers remain: `_create_rate_limit_middleware` line 151, `get_middlewares` line 172.
- Recommended primary class: `MiddlewareProvider` (keep as single orchestration owner).
- What to move:
	- Move compatibility wrappers to a separate legacy shim module or collapse to one thin adapter calling `MiddlewareProvider(cache).build()`.

### P0-2: `utils/env_resolver.py` exposes duplicate class+module function APIs
- File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/env_resolver.py`
- Violation type: module-level business logic duplication.
- Evidence:
	- Class API exists: `EnvResolver` line 20.
	- Duplicate module-level functions: `resolve_env_var` line 93, `resolve_env_vars` line 148.
- Recommended primary class: `EnvResolver`.
- What to move:
	- Keep class static methods as canonical API; migrate call sites away from module-level wrappers.

### P0-3: `utils/config_yaml_uri.py` duplicates URI logic outside class
- File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/config_yaml_uri.py`
- Violation type: procedural wrappers around class business logic.
- Evidence:
	- Class API exists: `ConfigYamlUriBuilder` line 25.
	- Duplicate module functions: `build_skill_resource_uris` line 165, `build_prompt_resource_uri` line 203.
- Recommended primary class: `ConfigYamlUriBuilder`.
- What to move:
	- Route runtime use through class methods only; keep temporary adapters for backwards compatibility if needed.

### P0-4: `proxies/mcp/resource_path_utils.py` still keeps duplicated module helper
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/resource_path_utils.py`
- Violation type: class+function dual surface.
- Evidence:
	- Primary class: `ResourcePathNamespaceResolver` line 8.
	- Duplicate module function: `get_root_namespace` line 34.
- Recommended primary class: `ResourcePathNamespaceResolver`.
- What to move:
	- Keep only class API and retire module-level fallback in next compat cycle.

### P0-5: `utils/security.py` remains function-first despite class wrapper
- File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/security.py`
- Violation type: no single primary class ownership for business logic.
- Evidence:
	- Function-first implementations: `sanitize_error_response` line 31, `validate_url` line 148, etc.
	- Wrapper class appears late: `SecurityService` line 515, `SecurityUtils` line 533.
- Recommended primary class: `SecurityService`.
- What to move:
	- Move core logic into class methods; expose one canonical API surface.

### P0-6: `utils/serialization.py` lacks primary class
- File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/serialization.py`
- Violation type: missing primary class module with business helper.
- Evidence:
	- Only module function: `to_dict` line 8.
- Recommended primary class: `SerializationService`.
- What to move:
	- Encapsulate serialization strategy in class static methods and migrate imports.

### Re-check: `app/app_config_provider.py` (user-focused module)
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/app_config_provider.py`
- Status: **Mostly compliant with project OOP direction**, but still has a class-splitting smell.
- Evidence:
	- Two classes in module: `AppConfigReader` line 21 and `AppConfigProvider` line 44.
	- Key orchestration methods: `_get_auth_config` line 49, `_is_auth_enabled` line 90.
- Recommendation:
	- Prefer one primary class (`AppConfigProvider`) and convert `AppConfigReader` into an internal mixin/private helper or fold read methods into provider class.
	- Keep singleton creation (`get_instance`) in the same primary class.

## Method SRP Findings (P0.5)

### M1: `LlmProxiesProvider._anthropic_messages_endpoint` mixes 5 concerns
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/proxies_provider.py:499`
- Mixed concerns:
	- request parsing
	- validation
	- protocol conversion
	- provider dispatch
	- error mapping/audit
- Proposed private helpers:
	- `_parse_anthropic_request(request)`
	- `_validate_anthropic_payload(body)`
	- `_dispatch_anthropic_request(client, params)`
	- `_build_anthropic_http_response(response, is_streaming, model_id)`
- Extraction order: parse → validate → build params → dispatch → format response.

### M2: `LlmProxiesProvider._get_models_by_provider` mixes cache policy and provider I/O mapping
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/proxies_provider.py:167`
- Mixed concerns:
	- cache lookup/set
	- remote call execution
	- DTO transformation
- Proposed private helpers:
	- `_get_cached_models(cache_key)`
	- `_fetch_provider_models(provider_name)`
	- `_store_cached_models(cache_key, models)`

### M3: `MCPProxyServer.async_run` still combines bootstrap/configuration/serve lifecycle
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/server.py`
- Mixed concerns:
	- startup telemetry
	- provider construction
	- app composition
	- process serve kickoff
- Proposed private helpers:
	- `_load_config_provider()`
	- `_configure_mcp_services(config_provider)`
	- `_configure_llm_services(config_provider)`
	- `_start_runtime_server()`

### M4: `McpBaseProvider` remote methods duplicate orchestration across resource types
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/base_provider.py`
- Methods: `_add_remote_skill_proxy`, `_add_remote_agent_proxy`, `_add_remote_prompt_proxy`.
- Mixed concerns: overlap warnings, runtime creation, provider creation, registration and error mapping.
- Proposed private helpers:
	- `_get_remote_entries(resource_type)`
	- `_build_remote_provider(resource_type, entry, runtime)`
	- `_register_remote_provider(mcp, resource_type, provider)`

## Library-Native Findings

### L1: FastAPI router usage is good and aligned
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/router.py`
- Evidence:
	- Uses `APIRouter`, `Depends`, and app-level dependency injection pattern cleanly.
- Recommendation:
	- Keep this pattern as the package standard for LLM HTTP endpoints.

### L2: Mixed Starlette/FastAPI doc and routing composition adds maintenance burden
- Files:
	- `src/drunk_ai_proxy/drunk_ai_proxy/app/starlette_app.py`
	- `src/drunk_ai_proxy/drunk_ai_proxy/app/swagger_provider.py`
- Finding:
	- Custom schema composition may duplicate what FastAPI can generate for sub-apps.
- Library-native alternative:
	- Prefer native FastAPI OpenAPI generation per sub-app, and only merge specs when single-spec UX is mandatory.
- Effort: **M**

### L3: FastMCP provider lifecycle patterns are mostly correct
- Files:
	- `src/drunk_ai_proxy/drunk_ai_proxy/app/lifespan.py`
	- `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/base_provider.py`
- Finding:
	- Uses explicit lifespan and provider registration; aligns with FastMCP provider/lifecycle model.
- Improvement:
	- Consolidate repeated remote runtime creation (`httpx.AsyncClient`) under a single managed lifecycle context.

## DRY/Reuse Findings

### D1: duplicated compatibility wrappers in middleware assembly
- File: `src/drunk_ai_proxy/drunk_ai_proxy/app/middleware_provider.py`
- Reuse target: one canonical `MiddlewareProvider.build()` path.
- Expected gain: lower drift and easier policy updates.

### D2: duplicated class + module wrappers across URI/env/resource utils
- Files:
	- `utils/env_resolver.py`
	- `utils/config_yaml_uri.py`
	- `proxies/mcp/resource_path_utils.py`
- Reuse target: class-only APIs with optional temporary compatibility facade.

### D3: security function wrappers duplicate class surface
- File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/security.py`
- Reuse target: consolidate under `SecurityService`.

## SOLID Findings

### S1 (SRP): `LlmProxiesProvider` is a god-class for routing + model DTO + dispatch + protocol conversion
- File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/llm/proxies_provider.py`
- Fix:
	- Split into collaborators: `LlmModelCatalogService`, `AnthropicAdapter`, `LlmEndpointHandler`.

### S2 (DIP): proxy layer still risks coupling to app composition concerns
- Files:
	- `app/server.py`
	- `proxies/mcp/base_provider.py`
- Fix:
	- Ensure only protocols cross boundaries (`TokenStore`, `AuthProviderFactory`), not app infrastructure types.

### S3 (ISP): single LLM provider interface still accommodates divergent capability sets
- Files:
	- `proxies/llm/base_provider.py`
	- `proxies/llm/websocket_provider.py`
- Evidence:
	- Endpoint-only implementations can be forced into wider interfaces.
- Fix:
	- Split contracts into mountable and endpoint-only protocols.

## Best Practices Findings

### B1: logger pattern drift in `auth/auth_pass_through.py`
- File: `src/drunk_ai_proxy/drunk_ai_proxy/auth/auth_pass_through.py`
- Evidence:
	- Uses stdlib logger: `logger = logging.getLogger(__name__)` (line 8), not project standard `fastmcp.utilities.logging`.
- Fix:
	- Align with repository logger pattern.

### B2: broad `Any` remains in core modules
- Files (examples):
	- `app/app_config_provider.py`
	- `proxies/llm/anthropic_provider.py`
	- `utils/env_resolver.py`
- Fix:
	- Introduce precise typed aliases/protocols for payload maps at module boundaries.

### B3: entrypoint module (`main.py`) is procedural but acceptable as packaging exception
- File: `src/drunk_ai_proxy/drunk_ai_proxy/main.py`
- Evidence: `main()` line 11 and `if __name__ == "__main__"` line 26.
- Decision:
	- Treat as acceptable bootstrapping entrypoint; do not elevate as architecture violation.

## Prioritized Recommendations

1. **P0 cleanup: remove module-level business wrappers in `middleware_provider`, `env_resolver`, `config_yaml_uri`, `resource_path_utils`, `security`, `serialization`**
	 - Impact: High, Effort: **M**, Risk: Low.
2. **Refine `app_config_provider.py` to one primary class (fold `AppConfigReader`)**
	 - Impact: High (for this module), Effort: **S/M**, Risk: Low.
3. **Decompose `LlmProxiesProvider` high-complexity methods first (`_anthropic_messages_endpoint`, model catalog path)**
	 - Impact: High, Effort: **M**, Risk: Medium.
4. **Unify remote provider bootstrap in `McpBaseProvider`**
	 - Impact: Medium, Effort: **M**, Risk: Low/Med.
5. **Fix logger-pattern drift in auth passthrough**
	 - Impact: Medium, Effort: **S**, Risk: Low.

## Migration Strategy

### Stage 1 (quick wins)
- Normalize logger usage in `auth/auth_pass_through.py`.
- Keep class APIs as canonical in utility modules and mark wrappers deprecated.

### Stage 2 (focused OOP cleanup)
- Refactor `app/app_config_provider.py` to one primary class while preserving external method signatures.
- Remove duplicated wrappers once internal call sites are migrated.

### Stage 3 (SRP and contract hardening)
- Extract `LlmProxiesProvider` collaborators.
- Consolidate remote provider bootstrap runtime and ensure lifecycle-managed HTTP clients.

### Rollback path
- Preserve thin compatibility wrappers for one release cycle.
- Gate higher-risk refactors (LLM provider split) behind incremental PRs with targeted tests.

## Validation Plan
- Targeted tests:
	- `python -m pytest tests/test_app_config_provider_auth_enabled.py tests/test_starlette_app.py tests/test_middleware.py tests/test_server.py -q`
	- `python -m pytest tests/test_llm_proxies_provider.py tests/test_remote_prompt_provider.py tests/test_mcp_proxy_provider.py -q`
- Static checks:
	- `pyright`
	- `flake8 src tests`
- Architecture guardrail check:
	- run import-linter workflow locally/CI to confirm no new upward dependency violations.

## Open Questions
- Is strict removal of module-level compatibility wrappers allowed immediately, or should wrappers remain for one deprecation cycle?
- For `app/app_config_provider.py`, do you prefer folding `AppConfigReader` directly into `AppConfigProvider`, or keeping it as a private nested helper class?

---

## Review Status

**🗂 PLANNED** — 2026-03-16

A phased refactor plan has been derived from this review and is available at:

[docs/refactoring/refactor-plan-20260316-105749.md](../../refactoring/refactor-plan-20260316-105749.md)

The plan covers all P0 OOP violations (P0-1 through P0-7), method-SRP extractions (M1–M4),
library-native replacements, DRY cleanup, and SOLID remediation targeting scorecard ≥ 4/5 across all dimensions.
