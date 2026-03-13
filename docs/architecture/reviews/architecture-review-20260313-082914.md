# Architecture Review — `src/drunk_ai_proxy/drunk_ai_proxy`

## Report File
`docs/architecture/reviews/architecture-review-20260313-082914.md`

## Scope + Assumptions
- Scope reviewed: `app`, `proxies`, `auth`, `middleware`, and `utils` packages under `src/drunk_ai_proxy/drunk_ai_proxy`.
- Assumed constraints: preserve current runtime behavior and FastMCP provider patterns; recommendations prioritize low-risk incremental changes.
- Analysis is static/read-only (no runtime profiling), based on source and test layout.

## Architecture Scorecard (0-5)
- Layering: **3.0/5**
- Security: **4.0/5**
- Naming consistency: **3.0/5**
- Boundaries/cohesion: **2.5/5**
- Testability/observability: **3.5/5**

## Findings (Evidence-backed)

### 1) Boundary inversion between `proxies` and `app`
- **Issue:** Proxy layer depends on app/config infrastructure directly.
- **Evidence:**
  - `proxies/mcp/base_provider.py` imports `AppConfigProvider` from `app.app_config_provider`.
  - `proxies/llm/proxies_provider.py` imports `AppConfigProvider` and dynamically imports `CacheProvider` from `app.cache_provider`.
- **Risk:** Tight coupling and hidden dependency direction make refactors (e.g., replacing config/auth/cache wiring) expensive and increase cycle risk.

### 2) Auth layer depends on app cache singleton
- **Issue:** `auth` package reaches into `app` package.
- **Evidence:** `auth/httpx_oauth_base.py` imports and defaults to `CacheProvider.get_oauth_store()`.
- **Risk:** Cross-layer coupling couples OAuth token behavior to app bootstrap details and complicates isolated auth testing.

### 3) Oversized, mixed-responsibility Swagger module
- **Issue:** `SwaggerProvider` combines route registration, endpoint schema composition, reusable component model construction, and large static schema definitions.
- **Evidence:** `app/swagger_provider.py` is ~1231 LOC and contains many schema builder helpers and endpoint constructors in one class/module.
- **Risk:** High maintenance cost, harder reviews, regression-prone edits, and low ownership clarity.

### 4) Duplicate auth-header middleware implementations (drift risk)
- **Issue:** Two different `AuthHeaderMiddleware` classes exist in different frameworks/contexts.
- **Evidence:**
  - `app/middleware_provider.py` defines Starlette `BaseHTTPMiddleware` auth header validation (and is used by `get_middlewares`).
  - `middleware/auth_header_middleware.py` defines FastMCP middleware variant, with no in-repo usage references found.
- **Risk:** Behavior drift and confusion over canonical auth enforcement path.

### 5) Security architecture generally strong at HTTP boundary
- **Issue:** Positive finding with minor centralization gap.
- **Evidence:**
  - `app/starlette_app.py` enforces global exception sanitization (`sanitize_error_response`) and adds security middlewares.
  - `app/security_headers_middleware.py` adds security headers and request size limiting.
  - `utils/security.py` centralizes sanitization, SSRF/path/input helpers, and audit helpers.
- **Risk:** Low immediate risk; primary risk is inconsistent use if utility functions are bypassed in future features.

### 6) Lazy imports are used as cycle-avoidance mechanism
- **Issue:** Many method-local imports indicate architecture pressure across package boundaries.
- **Evidence:**
  - `app/app_config_provider.py` method-local imports for many auth providers.
  - `proxies/mcp/base_provider.py` and `proxies/mcp/proxy_provider.py` method-local imports for provider creation/registration.
- **Risk:** Reduced static analyzability and discoverability; possible runtime import failures masked until specific codepaths execute.

## Prioritized Recommendations

### P1 — Introduce boundary-facing protocols for config/auth/cache access
- **Action:** Define small protocols/interfaces in a neutral package (e.g., `core/contracts` or `utils/contracts`) and inject them into proxy/auth constructors instead of importing `app.*` singletons.
- **Rationale:** Restores dependency direction (app composes, proxies/auth consume abstractions).
- **Impact:** High
- **Effort:** M
- **Risk:** Medium

### P1 — Split `SwaggerProvider` into cohesive components
- **Action:** Extract into focused modules/classes:
  - route mounting (`docs_routes.py`)
  - schema composition orchestrator (`schema_builder.py`)
  - reusable component schemas (`components/*.py` by domain: chat, embeddings, audio, images, anthropic)
- **Rationale:** Reduces blast radius and clarifies ownership boundaries.
- **Impact:** High
- **Effort:** M/L
- **Risk:** Medium

### P1 — Consolidate auth-header middleware source of truth
- **Action:** Decide canonical middleware (Starlette vs FastMCP), remove or deprecate the unused implementation, and document routing/auth boundary.
- **Rationale:** Prevents policy divergence and confusion.
- **Impact:** Medium/High
- **Effort:** S
- **Risk:** Low

### P2 — Move OAuth token-store defaulting out of auth base class
- **Action:** Require explicit `token_storage` injection from composition root (`app`), with optional factory helper in app layer.
- **Rationale:** Keeps `auth` package framework-agnostic and easier to test.
- **Impact:** Medium
- **Effort:** S/M
- **Risk:** Medium (constructor compatibility)

### P2 — Add architecture guardrails in CI
- **Action:** Add dependency rule checks (e.g., import-linter or lightweight custom checks) for allowed directions: `app -> proxies/auth/utils`, `proxies -> utils/contracts`, `auth -> utils/contracts`, and disallow reverse imports.
- **Rationale:** Prevents recurrence of boundary leaks.
- **Impact:** Medium
- **Effort:** S
- **Risk:** Low

### P3 — Normalize naming/docstring drift and package boundaries
- **Action:** Align naming/docstrings that reference outdated concepts (`config.json` references in MCP static provider docs while runtime uses YAML via `AppConfigProvider`), and tighten package-level ownership docs.
- **Rationale:** Improves onboarding and reduces maintenance confusion.
- **Impact:** Medium
- **Effort:** S
- **Risk:** Low

## Migration Strategy

### Quick wins (1-2 sprints)
1. Deprecate/remove duplicate unused auth middleware and update docs/tests.
2. Add import-direction guardrails in CI.
3. Normalize stale naming/docstring mismatches and package README ownership notes.

### Medium refactors (2-4 sprints)
1. Introduce config/auth/cache protocols and adapt `McpBaseProvider`, `LlmProxiesProvider`, and `HttpxOauthBase` to constructor injection.
2. Keep backward-compatible adapters in app layer to avoid immediate broad call-site breakage.

### Long-horizon (4+ sprints)
1. Decompose `SwaggerProvider` into composable schema modules with domain ownership.
2. Add snapshot-based schema regression tests per extracted domain.

### Compatibility notes
- Preserve current public imports/entrypoints (`app.__all__`, `proxies.__all__`) during transition.
- Use temporary adapter constructors/factory functions to avoid abrupt API breaks.

### Rollback path
- Keep original class wrappers delegating to new components for one release cycle.
- Gate major refactors with feature flags or dual-path execution in docs generation.

## Validation Plan
- Targeted tests:
  - `python -m pytest tests/test_middleware.py -q`
  - `python -m pytest tests/test_app_config_provider_auth_enabled.py tests/test_api_auth_provider.py tests/test_azure_oauth.py -q`
  - `python -m pytest tests/test_swagger_provider.py tests/test_starlette_app.py -q`
- Broader regression:
  - `python -m pytest tests/test_mcp_proxy_provider.py tests/test_openapi_mcp_provider.py tests/test_llm_proxies_provider.py -q`
- Static checks:
  - `flake8 src tests`
  - `pyright`
- Architecture guardrail checks:
  - CI import-direction rules for package boundaries.

## Open Questions
1. Is `middleware/auth_header_middleware.py` intended for future FastMCP middleware chaining, or can it be retired now?
2. Should `SwaggerProvider` remain manually modeled for OpenAI/Anthropic compatibility, or can parts be generated from typed request models to reduce duplication?
3. Is introducing a lightweight `contracts` package acceptable for dependency inversion, or should protocols live under `utils` to minimize package churn?
