# Architecture Remediation Implementation Plan

## Context
This plan operationalizes the findings in the architecture review:
- `docs/drunk_ai_proxy/architecture/reviews/architecture-review-20260313-082914.md`

Target area:
- `src/drunk_ai_proxy/drunk_ai_proxy`

## Goals
1. Re-establish clean dependency direction across `app`, `proxies`, `auth`, and `utils`.
2. Reduce change risk and cognitive load in oversized modules (especially Swagger docs generation).
3. Remove duplicate/ambiguous middleware ownership.
4. Add automated architecture guardrails to prevent regressions.

## Non-goals
- No behavior changes to API routes, auth semantics, or MCP/LLM transport behavior.
- No redesign of the security framework in `utils/security.py`.
- No package rename/restructure outside changes required for boundary enforcement.

## Constraints
- Preserve public imports and runtime entrypoints during migration.
- Prefer tiny, reversible steps with tests green at each step.
- Keep backward-compatible adapters for one release cycle where constructor or import signatures change.

## Implementation Strategy
Use an incremental “strangler” style rollout:
- Introduce seams (contracts/adapters) first.
- Redirect consumers one component at a time.
- Remove temporary compatibility shims only after test and release stabilization.

---

## Workstream A — Dependency Inversion for Config/Auth/Cache (P1)

### A1. Create contracts package
**Deliverable**
- New contracts module (recommended path: `src/drunk_ai_proxy/drunk_ai_proxy/utils/contracts/`) containing minimal protocols:
  - `ConfigProviderContract`
  - `AuthProviderFactoryContract`
  - `TokenStorageProviderContract`

**Acceptance criteria**
- Contracts are framework-agnostic and typed.
- No import from `app.*` inside contracts.

### A2. Add app-layer adapters
**Deliverable**
- App composition adapters that implement contracts using existing singletons:
  - wraps `AppConfigProvider`
  - wraps `CacheProvider`

**Acceptance criteria**
- Existing behavior unchanged.
- Adapters are unit-tested with current `AppConfigProvider` and `CacheProvider` stubs/mocks.

### A3. Refactor proxy/auth constructors to dependency injection
**Targets**
- `proxies/mcp/base_provider.py`
- `proxies/llm/proxies_provider.py`
- `auth/httpx_oauth_base.py`

**Deliverable**
- Replace direct `app.*` imports with constructor-injected contracts.
- Keep transitional defaults via adapter wrappers for compatibility.

**Acceptance criteria**
- No direct import from `proxies/*` or `auth/*` into `app.*` internals except composition root wiring.
- All existing tests for these modules pass.

### A4. Remove temporary defaults (release +1)
**Deliverable**
- Remove fallback defaults that hide missing dependencies after one stable release.

**Acceptance criteria**
- Constructor dependencies explicit in all call sites.
- No runtime dependency discovery via method-local imports for these concerns.

---

## Workstream B — Swagger Provider Decomposition (P1)

### B1. Extract schema composition boundaries
**Deliverable**
- Split `app/swagger_provider.py` into focused modules:
  - `swagger/docs_routes.py` (mounts `/openapi.json`, `/docs`)
  - `swagger/schema_builder.py` (top-level OpenAPI assembly)
  - `swagger/components/` (domain schemas: chat, embeddings, audio, images, anthropic)

**Acceptance criteria**
- Public `SwaggerProvider` API remains stable (facade pattern).
- Pure schema builders are deterministic and side-effect free.

### B2. Preserve behavior with snapshot/contract tests
**Deliverable**
- Golden/snapshot tests for schema output and key path coverage.

**Acceptance criteria**
- `tests/test_swagger_provider.py` remains green.
- Added tests assert preserved operation IDs and schema refs.

### B3. Final cleanup
**Deliverable**
- Remove dead helper methods and duplicated schema snippets.
- Keep only orchestration in `SwaggerProvider` facade.

**Acceptance criteria**
- Reduced module size and complexity.
- Clear ownership map for schema domains.

---

## Workstream C — Auth Header Middleware Source-of-Truth (P1)

### C1. Decide canonical middleware path
**Decision required**
- Canonical runtime path should remain Starlette middleware in `app/middleware_provider.py` unless explicit FastMCP middleware usage is required.

### C2. Deprecate/remove duplicate implementation
**Target**
- `middleware/auth_header_middleware.py`

**Deliverable**
- Either remove unused middleware module or mark as internal experimental path with explicit wiring docs.

**Acceptance criteria**
- Single documented auth-header enforcement path.
- Tests verify canonical middleware behavior only.

---

## Workstream D — CI Architecture Guardrails (P2)

### D1. Introduce import-linter contracts
**Deliverable**
- Add `.importlinter` configuration with rules:
  - Layered rule for `app -> proxies/auth/utils/contracts`
  - Forbidden rules to prevent `proxies -> app` and `auth -> app` direct imports
  - Optional acyclic siblings rule for high-risk packages

### D2. CI integration
**Deliverable**
- Add architecture lint command in CI pipeline and local docs.

**Acceptance criteria**
- Failing architecture contract blocks merge.
- Developer docs include remediation steps for violations.

---

## Workstream E — Naming/Docs Consistency (P3)

### E1. Correct stale references
**Targets**
- stale mentions of `config.json` where runtime behavior uses YAML.

### E2. Ownership docs
**Deliverable**
- Brief package ownership guidance for `app`, `proxies`, `auth`, `utils/contracts`.

**Acceptance criteria**
- Terminology and runtime docs are consistent.
- New contributors can identify composition root vs domain modules quickly.

---

## Proposed Sequencing (Sprints)

### Sprint 1 (Low-risk foundation)
1. Workstream C (middleware consolidation decision + cleanup)
2. Workstream D (import-linter setup in warn-only mode)
3. Workstream E (naming/doc cleanup)

**Exit criteria**
- One canonical auth middleware path documented.
- Architecture checks running in CI (non-blocking initially).

### Sprint 2 (Core boundary refactor)
1. Workstream A1-A3 (contracts + adapters + dependency injection migration)
2. Promote import-linter to blocking mode after migration PRs merge.

**Exit criteria**
- `proxies` and `auth` no longer directly import `app` internals for config/cache.

### Sprint 3 (Swagger decomposition)
1. Workstream B1-B2 (facade + extracted builders + snapshots)
2. Workstream B3 cleanup

**Exit criteria**
- Swagger behavior parity preserved via tests.
- Module decomposition complete with clear component boundaries.

### Sprint 4 (Hardening)
1. Workstream A4 cleanup of transitional defaults
2. Expand architecture contracts (independence/acyclic as needed)

**Exit criteria**
- No temporary adapters/defaults left that conceal boundary violations.

---

## Testing and Verification Plan

### Required test suite per PR
- `python -m pytest tests/test_middleware.py -q`
- `python -m pytest tests/test_app_config_provider_auth_enabled.py tests/test_api_auth_provider.py tests/test_azure_oauth.py -q`
- `python -m pytest tests/test_swagger_provider.py tests/test_starlette_app.py -q`
- `python -m pytest tests/test_mcp_proxy_provider.py tests/test_openapi_mcp_provider.py tests/test_llm_proxies_provider.py -q`

### Static and architecture checks
- `flake8 src tests`
- `pyright`
- `lint-imports` (from import-linter)

### Success metrics
- Zero forbidden import violations in CI.
- `SwaggerProvider` complexity reduced (module LOC and helper count reduced).
- No increase in failing tests on target suites.
- No auth/security behavior regressions on health/docs/protected endpoints.

---

## Risks and Mitigations

1. **Constructor signature churn breaks call sites**
   - Mitigation: transitional adapter defaults; migrate callers incrementally; remove defaults later.

2. **Swagger output drift during decomposition**
   - Mitigation: snapshot tests for generated schema and operation IDs before extraction.

3. **Over-constraining architecture checks early**
   - Mitigation: run import-linter in non-blocking mode first sprint, then enforce.

4. **Accidental behavior changes during refactor**
   - Mitigation: small PRs, structure-only changes separated from behavior edits.

---

## Rollout and Rollback

### Rollout
- Use small PRs by workstream step (A1, A2, A3...).
- Merge only with full targeted test pass + architecture checks.
- Announce migration notes for constructor/dependency injection changes.

### Rollback
- Keep compatibility facades/wrappers for one release cycle.
- Revert by workstream PR if regression appears; avoid multi-workstream mega-PRs.

---

## Ownership and Tracking
- Suggested tracking epic: “Architecture Remediation 2026Q2”.
- Child tasks: A1-A4, B1-B3, C1-C2, D1-D2, E1-E2.
- Each child task should include:
  - impacted files
  - acceptance criteria
  - required tests
  - rollback note

---

## Decision Log (to confirm before execution)
1. Confirm canonical auth-header middleware path (Starlette-only or dual-path with explicit use-case).
2. Confirm contracts package location (`utils/contracts` recommended to minimize churn).
3. Confirm whether Swagger schema generation remains manual or partially model-derived.

---

## Sources consulted
- Review baseline: `docs/drunk_ai_proxy/architecture/reviews/architecture-review-20260313-082914.md`
- Import Linter docs: https://import-linter.readthedocs.io/en/stable/
- Strangler Fig modernization pattern: https://martinfowler.com/bliki/StranglerFigApplication.html
- Large-class incremental refactoring approach: https://martinfowler.com/articles/class-too-large.html
