# Architecture Review — `src/drunk_ai_proxy/drunk_ai_proxy`

> **Status: PLANNED** — Refactor plan created at [docs/drunk_ai_proxy/refactoring/refactor-plan-20260313-005439.md](../../refactoring/refactor-plan-20260313-005439.md)

**Date:** 2026-03-13  
**Reviewer:** GitHub Copilot (Architecture Reviewer mode)  
**Scope:** `src/drunk_ai_proxy/drunk_ai_proxy/` — all packages: `app`, `auth`, `middleware`, `proxies`, `utils`

---

## Scope and Assumptions

- Review covers module/package structure, layering, dependency direction, DRY compliance, naming, security touch-points, and testability.
- Hard constraints: `AGENTS.md` and `.github/copilot-instructions.md` are treated as authoritative conventions.
- Existing import-linter baseline (`.importlinter`) is acknowledged; violations confirmed by code inspection.
- No test files were modified; findings are read-only analysis only.

---

## Architecture Scorecard (0–5)

| Dimension            | Score | Notes |
|----------------------|-------|-------|
| Package structure    | 3 / 5 | Good domain grouping; empty `middleware/` package is misleading |
| Module structure     | 3 / 5 | Most modules are coherent; `app_config_provider.py` violates SRP |
| DRY / reuse          | 3 / 5 | Directory-validation logic triplicated across `base_provider` + `proxy_provider` |
| Layering             | 2 / 5 | Two confirmed upward dependency violations (`proxies→app`, `auth→app`) |
| Security             | 4 / 5 | Good sanitised-error + audit-log coverage; dual rate-limit gate is a minor concern |
| Naming consistency   | 3 / 5 | Module/class names are mostly clear; legacy docstring mismatch and stale stub found |
| Boundaries           | 3 / 5 | `FastAuthMiddleware` lives in wrong package; `middleware/` is effectively a ghost package |
| Testability          | 3 / 5 | Singleton `AppConfigProvider` accessed directly in `proxies` layer makes unit isolation harder |

**Overall: 3 / 5** — Solid foundations with clear remediation targets.

---

## Dependency / Layer Map

```
main.py
  └─ app/
       ├─ server.py              (orchestration)
       ├─ starlette_app.py       (web / ASGI assembly)
       ├─ app_config_provider.py (config + auth-factory singleton)
       ├─ cache_provider.py      (TTL key-value store)
       ├─ lifespan.py            (startup / shutdown management)
       ├─ middleware_provider.py (AuthHeaderMiddleware, RateLimitMiddleware, get_middlewares)
       ├─ security_headers_middleware.py
       ├─ swagger_provider.py
       └─ tasks/remote_resource_sync_task.py
  └─ proxies/
       ├─ llm/   (base_provider, proxies_provider, anthropic_provider, client_factory, websocket_*)
       ├─ mcp/   (base_provider, proxy_provider, static_provider, mcp_proxy_builder, resource_path_utils, custom_skills_...)
       ├─ agent/ (agent_provider, custom_agents_directory_provider)
       └─ prompt/(prompt_loader, prompt_provider, prompt_template)
  └─ auth/
       ├─ api_auth_provider.py, auth_pass_through.py
       └─ httpx_azure_oauth.py, httpx_oauth_base.py      ← VIOLATION
  └─ utils/
       ├─ config_yaml.py, env.py, env_resolver.py
       ├─ security.py, serialization.py, auth_header_policy.py
       └─ error_utils.py                                 ← DEAD STUB
```

**Desired flow:** `app → proxies/auth/utils | proxies → utils | auth → utils`  
**Actual violations:** `proxies → app`, `auth → app`

---

## Findings (Evidence-backed)

### F-1 · Upward Dependency — `proxies → app` (CONFIRMED import-linter violation)
| | |
|---|---|
| **Files** | `proxies/mcp/base_provider.py:10`, `proxies/llm/proxies_provider.py:6,88` |
| **Symbol** | `from drunk_ai_proxy.app.app_config_provider import AppConfigProvider` / `CacheProvider` |
| **Risk** | HIGH — circular potential; `proxies` cannot be tested without instantiating the `app` singleton. Prevents future library extraction of the proxy layer. |

`McpBaseProvider._get_app_auth_provider()` calls `AppConfigProvider.get_instance()` directly. `LlmProxiesProvider.__init__` calls both `AppConfigProvider.get_instance()` and `CacheProvider.get_cache_store()`.

---

### F-2 · Upward Dependency — `auth → app` (CONFIRMED import-linter violation)
| | |
|---|---|
| **File** | `auth/httpx_oauth_base.py:23` |
| **Symbol** | `from drunk_ai_proxy.app.cache_provider import CacheProvider` |
| **Risk** | HIGH — same implications as F-1; token storage is hardwired to the app's cache singleton. |

`HttpxOauthBase.__init__` accepts `token_storage: AsyncKeyValue | None` but the module-level import of `CacheProvider` is live (not inside `TYPE_CHECKING`).

---

### F-3 · `AppConfigProvider` Violates SRP (God Object)
| | |
|---|---|
| **File** | `app/app_config_provider.py` |
| **Evidence** | Single class is simultaneously a config reader, a 12-branch FastMCP auth-provider factory, and an httpx client-auth factory. Adding a new auth provider requires editing this file. |
| **Risk** | MEDIUM — any new provider forces changes to a central class; test surface is large. |

The `match/case` for `get_fast_mcp_auth_provider()` handles 12 `AuthType` values inline. Each `case` imports a provider module; the logic does not follow OCP.

---

### F-4 · `error_utils.py` is a Dead Stub (DRY / Clutter)
| | |
|---|---|
| **File** | `utils/error_utils.py` |
| **Evidence** | Single function `sanitize_error_message(_: str) -> str` that ignores its argument and returns a hardcoded string. `security.py` provides `sanitize_error_response()` and `get_actionable_message()` which supersede it. |
| **Risk** | LOW — dead code causes confusion; any new code that discovers `error_utils.py` via search may use the inferior stub. |

---

### F-5 · `middleware/` Package is Empty (Ghost Package)
| | |
|---|---|
| **Path** | `src/drunk_ai_proxy/drunk_ai_proxy/middleware/` |
| **Evidence** | Directory contains only `__pycache__/`. All middleware implementations (`AuthHeaderMiddleware`, `RateLimitMiddleware`, `SecurityHeadersMiddleware`, `RequestSizeLimitMiddleware`) live in `app/middleware_provider.py` and `app/security_headers_middleware.py`. |
| **Risk** | LOW-MEDIUM — misleading to new contributors; discoverability for middleware logic is poor. |

---

### F-6 · `FastAuthMiddleware` Misplaced in `proxies/llm/proxies_provider.py`
| | |
|---|---|
| **File** | `proxies/llm/proxies_provider.py` (class `FastAuthMiddleware`, lines ~40–60) |
| **Evidence** | An auth-enforcement middleware class is defined inside the LLM proxies module. |
| **Risk** | MEDIUM — auth concerns are coupled to one proxy type; other proxy types cannot reuse it without importing `proxies/llm`. |

---

### F-7 · Directory-Validation Logic Triplicated (DRY Violation)
| | |
|---|---|
| **Files** | `proxies/mcp/base_provider.py` (`_add_skill_proxy`, `_add_agent_proxy`), `proxies/mcp/proxy_provider.py` (`_add_prompt_proxy`) |
| **Evidence** | All three methods share an identical pattern: (1) get dirs from config, (2) resolve Path, (3) check exists+is_dir, (4) count `.md` files, (5) `logger.warning` and skip, (6) try/except with `logger.error` + `audit_log`. |
| **Risk** | MEDIUM — bug fixes or behavioural changes must be applied in three places; a single omission creates inconsistency. |

---

### ~~F-8 · Logger Pattern Non-Compliance~~ — DISMISSED
| | |
|---|---|
| **Status** | **Dismissed** — user decision: module-level `fastmcp` logger is the accepted project standard |
| **Resolution** | AGENTS.md updated to document `from fastmcp.utilities import logging; logger = logging.get_logger(__name__)` as the canonical pattern. A single logger per module is shared across all classes in that file. No code changes required. |

---

### F-9 · `Optional[X]` Used in `config_yaml.py` (Coding Standard Drift)
| | |
|---|---|
| **File** | `utils/config_yaml.py` |
| **Evidence** | `from typing import Any, Optional, cast` and multiple `Optional[str]` field annotations. AGENTS.md and `.github/copilot-instructions.md` mandate `str | None` syntax (Python 3.10+). |
| **Risk** | LOW — cosmetic, but pollutes the convention baseline for new contributors. |

---

### F-10 · `StaticProxiesProvider` Docstring Refers to Deleted Class Name
| | |
|---|---|
| **File** | `proxies/mcp/static_provider.py` |
| **Evidence** | Class docstring says "ProxyConfigProvider" in multiple places; the class is named `StaticProxiesProvider`. |
| **Risk** | LOW — documentation mismatch; confusing when grepping or reading code. |

---

### F-11 · Dual Rate-Limit Gate (Security Configuration Smell)
| | |
|---|---|
| **Files** | `app/middleware_provider.py` (`get_middlewares`, `RateLimitMiddleware.__init__`) |
| **Evidence** | Rate limiting is guarded by both `RATE_LIMIT_ENABLED` env var (controls whether the middleware is added at all in `get_middlewares()`) AND `self._enabled` inside `RateLimitMiddleware` (based on `max_requests > 0 && window_seconds > 0`). These can produce conflicting effective states. |
| **Risk** | LOW-MEDIUM — if env var is `True` but limits are 0, `self._enabled` disables the gate silently; if env var is `False` but limits are set, middleware is never mounted regardless. Auditing effective rate-limit state requires checking two places. |

---

### F-12 · `get_provider()` Module-Level Function in `app_config_provider.py`
| | |
|---|---|
| **File** | `app/app_config_provider.py` (last line) |
| **Evidence** | A module-level function `get_provider()` is exported. AGENTS.md states: "avoid module-level procedural core logic". The function simply calls `AppConfigProvider.get_instance()`, adding no value. |
| **Risk** | LOW — minor convention breach; two public entry points (`AppConfigProvider.get_instance()` and `get_provider()`) promote inconsistency. |

---

## Refactor Candidates

### RC-1 · Inject Config/Cache into Proxies and Auth via Protocol
**Issue:** F-1 and F-2 — upward imports from `proxies` and `auth` into `app`.  
**Proposed refactor:**
1. Define lightweight `Protocol` interfaces in `utils` (or a new `utils/protocols.py`):
   ```python
   class AuthProviderFactory(Protocol):
       def get_fast_mcp_auth_provider(self, provider_name: AuthType | None = None) -> AuthProvider | None: ...
   
   class TokenStore(Protocol):
       async def get(self, key: str) -> object | None: ...
       async def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None: ...
   ```
2. Pass them via constructor injection into `McpBaseProvider.__init__` and `HttpxOauthBase.__init__`.
3. The `app` layer injects concrete instances when constructing proxies/auth.

**Maintainability gain:** Removes import-linter violations, enables unit testing proxies without the `app` singleton.  
**Migration risk:** LOW — additive change; existing call sites in `server.py` inject the concrete `AppConfigProvider`.

---

### RC-2 · Split `AppConfigProvider` into Config Reader + Auth Provider Registry
**Issue:** F-3 — SRP violation.  
**Proposed refactor:**
- Keep `AppConfigProvider` as a config-data accessor only (`get_mcp_configs`, `get_llm_configs`, `get_remote_resources`).
- Extract `AuthProviderRegistry` (or `AuthProviderFactory`) that encapsulates the 12-branch `match/case` logic.
  - Register providers via a dict mapping `AuthType → Callable[..., AuthProvider]`.
  - Each registration entry is a factory callable, enabling the registry to be extended without modification (OCP).
- `get_client_auth_handler` moves to a separate `ClientAuthHandlerFactory`.

**Maintainability gain:** High — new auth providers require only a dict entry, not a class modification; test surface is smaller.  
**Migration risk:** MEDIUM — requires updating all callers of the two factory methods; app wiring in `server.py` must be adjusted.

---

### RC-3 · Extract `_validate_resource_directory()` Helper to `McpBaseProvider`
**Issue:** F-7 — triplicated dir-validation pattern.  
**Proposed refactor:**
```python
def _validate_resource_directories(
    self,
    dirs: list[str],
    resource_type: str,
) -> list[Path]:
    """Returns valid Path objects for directories containing .md files."""
    ...
```
Used by `_add_skill_proxy`, `_add_agent_proxy`, and `_add_prompt_proxy`.

**Maintainability gain:** HIGH — single point for path validation logic; any future change (e.g., count threshold, warn message format) applies once.  
**Migration risk:** LOW — purely additive; method is private (no public API change).

---

### RC-4 · Move Middleware to `middleware/` Package
**Issue:** F-5 and F-6.  
**Proposed refactor:**
- Populate `middleware/` with:
  - `auth_header.py` → `AuthHeaderMiddleware` (from `app/middleware_provider.py`)
  - `rate_limit.py` → `RateLimitMiddleware`
  - `security_headers.py` → `SecurityHeadersMiddleware`, `RequestSizeLimitMiddleware` (from `app/security_headers_middleware.py`)
  - `fast_auth.py` → `FastAuthMiddleware` (from `proxies/llm/proxies_provider.py`)
- Keep `app/middleware_provider.py` as the assembly/composition point only (`get_middlewares()` factory).

**Maintainability gain:** MEDIUM — middleware is discoverable in one package; eliminates confusion between `middleware/` (empty) and `app/` (contains middleware).  
**Migration risk:** LOW — imports update only; no behavioural change.

---

### RC-5 · Remove `error_utils.py`
**Issue:** F-4.  
**Proposed refactor:** Delete `utils/error_utils.py`. Confirm no remaining callers (search indicates zero; the stub function ignores its argument and duplicates `security.py`).  
**Migration risk:** LOW (near zero if no callers).

---

## Prioritized Recommendations

| # | Action | Rationale | Impact | Effort | Risk |
|---|--------|-----------|--------|--------|------|
| 1 | **Fix F-1/F-2: Inject `AppConfigProvider`/`CacheProvider` as protocols into `proxies` and `auth`** | Resolves both import-linter violations; critical for testability | HIGH | M | Low |
| 2 | **Fix F-7: Extract `_validate_resource_directories()` helper in `McpBaseProvider`** | Eliminates triplicated code now; no API surface change | HIGH | S | Low |
| 3 | **Fix F-3: Split `AppConfigProvider` into config reader + `AuthProviderRegistry`** | Removes god-object; OCP compliance for future auth providers | MEDIUM | M | Med |
| 4 | **Fix F-4: Delete `error_utils.py`** | Remove dead stub before it misleads future contributors | LOW | S | Low |
| 5 | **Fix F-6: Move `FastAuthMiddleware` to `middleware/` package (RC-4)** | Consolidates auth middleware; removes proxies→auth concern bleed | MEDIUM | S | Low |
| 6 | **Fix F-5: Populate `middleware/` package (RC-4)** | Naming clarity and discoverability for all middleware | LOW | S | Low |
| 7 | **Fix F-9: Replace `Optional[X]` with `X \| None` in `config_yaml.py`** | Standards compliance | LOW | S | Low |
| 8 | **Fix F-10: Correct `StaticProxiesProvider` docstring** | Documentation accuracy | LOW | S | Low |
| 9 | **Fix F-11: Collapse rate-limit guard to single control point** | Eliminate silent configuration drift | LOW | S | Low |
| 10 | **Fix F-12: Remove `get_provider()` module-level alias** | Convention compliance; prefer `AppConfigProvider.get_instance()` | LOW | S | Low |

---

## Migration Strategy

### Phase 1 — Quick Wins (1–3 days)
These are safe, isolated changes with no behavioural impact.

1. Delete `utils/error_utils.py` (confirm zero callers via `grep -r "error_utils"`)
2. Fix `StaticProxiesProvider` docstring.
3. Replace `Optional[X]` → `X | None` in `config_yaml.py`.
4. Remove `get_provider()` alias from `app_config_provider.py`; update `app/__init__.py`.
5. Consolidate rate-limit flag — remove `self._enabled` logic from `RateLimitMiddleware`, rely solely on `RATE_LIMIT_ENABLED` gate in `get_middlewares()`.
6. Extract `_validate_resource_directories()` to `McpBaseProvider`; refactor the three `_add_*_proxy` methods to call it.

**Rollback:** each item is a single-file edit; revert via `git revert` per commit.

### Phase 2 — Structural Improvements (1 week)
7. Move `FastAuthMiddleware` to `middleware/fast_auth.py`. Update import in `proxies/llm/proxies_provider.py`.
8. Migrate `AuthHeaderMiddleware`, `RateLimitMiddleware`, `SecurityHeadersMiddleware` into `middleware/` sub-modules. Update `app/middleware_provider.py` to import from `middleware/`.
9. Define Protocol interfaces (`AuthProviderFactory`, `TokenStore`) in `utils/protocols.py`.
10. Update `McpBaseProvider.__init__` and `HttpxOauthBase.__init__` to accept injected protocols.
11. Update `app/server.py` to pass concrete `AppConfigProvider` instance at construction time.

**Compatibility:** no external API changes; only internal import paths shift. Run targeted regression suite after each step:
```bash
.venv/bin/python -m pytest tests/test_api_auth_provider.py tests/test_auth_pass_through.py \
    tests/test_azure_oauth.py tests/test_mcp_proxy_provider.py tests/test_openapi_mcp_provider.py \
    tests/test_llm_proxies_provider.py -q
```

### Phase 3 — Long-Horizon Refactor (2–4 weeks, requires team coordination)
12. Split `AppConfigProvider` into `AppConfigProvider` (data) + `AuthProviderRegistry` (factory) + `ClientAuthHandlerFactory`.
13. Evaluate logger pattern: adopt `fastmcp.utilities.logging.get_logger` as the project standard (update AGENTS.md) **or** migrate all files to `setup_logging` — pick one, document, enforce via lint.

**Rollback path (Phase 3):** Since `AppConfigProvider` is a frequently-touched class, feature-flag the split behind a new constructor parameter during transition; remove flag once all callers are migrated.

---

## Validation Plan

### After Phase 1:
```bash
# Confirm no callers of deleted stub
grep -r "error_utils" src/ tests/
# Run full suite
python -m pytest -q
# Import linter (should still show same baseline violations until Phase 2)
cd src/drunk_ai_proxy && python -m importlinter
```

### After Phase 2 (F-1/F-2 resolved):
```bash
# Import linter should report ZERO violations
cd src/drunk_ai_proxy && python -m importlinter
# Full targeted proxy/auth regression
.venv/bin/python -m pytest tests/test_api_auth_provider.py tests/test_auth_pass_through.py \
    tests/test_azure_oauth.py tests/test_mcp_proxy_provider.py tests/test_openapi_mcp_provider.py \
    tests/test_llm_proxies_provider.py tests/test_llm_websocket_provider.py \
    tests/test_llm_websocket_transport.py -q
# Type checking
pyright
# Lint
flake8 src tests
```

### After Phase 3:
```bash
python -m pytest --cov=src -q
# Verify coverage is maintained at or above current baseline (76%)
```

---

## Open Questions

1. ~~**Logger convention decision**~~ — **RESOLVED:** `fastmcp.utilities.logging.get_logger` at module level is the accepted standard. AGENTS.md has been updated accordingly. No migration work needed.
2. **`StaticProxiesProvider` value** — Given that `StaticProxiesProvider.get_config_services()` is essentially a delegation chain through to `McpProxyProvider`, is the class providing enough abstraction to justify its existence, or should `server.py` call `McpProxyProvider` factory methods directly?
3. **`middleware/` package intent** — Was the empty `middleware/` directory an in-progress refactor that was abandoned? Confirming this determines whether RC-4 is a continuation of existing intent or net-new work.

---

*Report generated by GitHub Copilot — Architecture Reviewer mode.*
