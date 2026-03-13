# Architecture Review — `src/drunk_ai_proxy/drunk_ai_proxy`

**Date:** 2026-03-13  
**Reviewer:** GitHub Copilot (Architecture Reviewer mode)  
**Scope:** Full audit of `src/drunk_ai_proxy/drunk_ai_proxy/` — all packages (`app`, `auth`, `middleware`, `proxies`, `utils`)  
**Status:** ✅ PLANNED — [Refactor Plan 2026-03-13](../../refactoring/refactor-plan-20260313-153911.md)  
**Assumptions:**
- `AGENTS.md` and `.github/copilot-instructions.md` are treated as hard constraints.
- "One primary class per module" is a non-negotiable project rule.
- Library-native means current FastMCP + FastAPI conventions (latest stable).

---

## Architecture Scorecard (0–5)

| Dimension | Score | Notes |
|---|---|---|
| **OOP / class-per-module** | 2 / 5 | 5 modules have zero primary class; 3 more have mixed responsibilities |
| **Library-native usage** | 3 / 5 | APIRouter not used; no `response_model` on LLM endpoints; lifespan shim hand-rolled |
| **DRY / reuse** | 3 / 5 | Resource-mount pattern repeated 6× in proxy_provider; LLM endpoint boilerplate repeated 5× |
| **SOLID compliance** | 3 / 5 | `LlmProxiesProvider` and `McpProxyProvider` violate SRP; two factory classes duplicating structural logic |
| **Layering / dependency direction** | 3 / 5 | `proxies/mcp/base_provider.py` references `app` layer; auth module imports `app.cache_provider` |
| **Security architecture** | 4 / 5 | `security.py` utilities in place; audit_log used; a few Pydantic v1 compat imports weaken posture |
| **Naming conventions** | 4 / 5 | Mostly consistent; compatibility shim naming ambiguity in `base_provider.py` |
| **Testability** | 3 / 5 | Module-level state (`CacheProvider` statics) and no-class factory functions are harder to mock |

---

## P0 — OOP / Class-per-Module Findings

### F-OOP-01 · `app/middleware_provider.py` — **No primary class at all**

All code is procedural module-level functions: `_parse_csv`, `_create_cors_middleware`, `_create_auth_header_middleware`, `_create_rate_limit_middleware`, `_create_request_size_limit_middleware`, `_create_security_headers_middleware`, `get_middlewares`. The file reads env vars, constructs middleware, and returns them — all business logic, zero class encapsulation.

**Lines:** entire file (~150 lines).  
**Recommended primary class:** `MiddlewareProvider`  
**What moves in:**
- Constructor reads or accepts env-derived settings (CORS, rate-limit, auth flags).
- `build() -> list[Middleware]` is the single public method.
- All `_create_*` become private methods.
- `_parse_csv` becomes a private static helper.

```python
class MiddlewareProvider:
    def __init__(self, cache: TTLAsyncKeyValue) -> None:
        self._cache = cache

    def build(self) -> list[Middleware]:
        middlewares = [self._cors(), self._request_size_limit(), self._security_headers()]
        if AUTH_ENABLED:
            middlewares.append(self._auth_header())
        if RATE_LIMIT_ENABLED:
            middlewares.append(self._rate_limit())
        return middlewares

    def _cors(self) -> Middleware: ...
    def _rate_limit(self) -> Middleware: ...
    # etc.
```

---

### F-OOP-02 · `proxies/agent/agent_provider.py` — **Business logic at module level**

Two module-level functions contain parsing business logic:
- `parse_frontmatter(content: str)` — YAML frontmatter parsing (non-trivial regex + type coercion).
- `compute_file_hash(path: Path)` — SHA-256 file hashing.

These are invoked by `AgentProvider` but live outside any class.

**Lines:** `parse_frontmatter` (~35 lines), `compute_file_hash` (~10 lines).  
**Recommended fix:** Move both into a private static `AgentProvider` method or a dedicated `AgentParser` helper class.

```python
class AgentParser:
    """Parses YAML frontmatter and computes file hashes for agent files."""

    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]: ...

    @staticmethod
    def compute_file_hash(path: Path) -> str: ...
```

---

### F-OOP-03 · `utils/security.py` — **No primary class; all module-level utility functions**

The entire module (~200 lines) exposes utility functions at module level: `sanitize_error_response`, `is_user_actionable_error`, `get_actionable_message`, `validate_url`, `validate_path`, `audit_log`, `mask_sensitive`, etc. While pure utilities are tolerated the project convention still requires a primary class.

**Recommended primary class:** `SecurityUtils` with all functions as `@staticmethod` methods.  
This also makes mocking in tests trivially clean: patch `SecurityUtils.audit_log` rather than a bare module function.

**Lines:** all ~200 lines outside a class.

---

### F-OOP-04 · `utils/env.py` — **Module-level helper functions and all-constant module**

`get_env_string`, `get_env_int`, `get_env_bool` are private helper functions defined at module level. All constants (80+ lines) are also module-level. While read-only config constants at module level are less harmful than mutable state, the project rule is clear. More importantly, having the three helper functions outside a class makes them invisible to standard OOP dependency injection.

**Recommended primary class:** `EnvConfig` (classmethod factory) or move helpers to a static `EnvReader` class with all constants as `class` attributes.  
Low coupling impact — only minor refactor needed since these are read-once at startup.

---

### F-OOP-05 · `proxies/mcp/base_provider.py` — **Compatibility shim class masking the real `AppConfigProvider`**

The file declares:
```python
class AppConfigProvider:
    """Compatibility shim for tests patching legacy AppConfigProvider path."""

    @staticmethod
    def get_instance() -> None:
        return None
```

This creates a dangerously named ghost class in a module that also defines `McpBaseProvider` (the actual primary class). The shim name collides with the real `AppConfigProvider` from `app/app_config_provider.py`, causing confusion for readers and import patchers.

**Recommended fix:** Remove the shim entirely. Tests that patched this path should patch the canonical `app.app_config_provider.AppConfigProvider` instead. This also eliminates a layering violation (see F-LAYER-01).

---

### F-OOP-06 · `utils/config_yaml.py` — **Over-large multi-class module**

The module defines 15+ classes (all Pydantic models + `ConfigYaml`). While model-only files are a common exception, the module is growing (likely 500+ lines) and mixing the `ConfigYaml` loader class with all model definitions makes navigation and testing harder.

**Recommended split (medium effort):**
- `config_yaml_models.py` — all Pydantic model definitions only.
- `config_yaml.py` — only `ConfigYaml` (the file-loading class).

---

## Library-Native Findings

### F-LIB-01 · `proxies/llm/proxies_provider.py` — **APIRouter not used; no `response_model`**

All 8 HTTP routes are registered via raw `app.add_api_route()`. FastAPI's standard pattern is `APIRouter` with decorator syntax and `response_model`.

**Current:**
```python
app.add_api_route("/chat/completions", self._chat_completions_endpoint, methods=["POST"])
```

**FastAPI native:**
```python
router = APIRouter()

@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(body: ChatCompletionRequest, ...) -> ChatCompletionResponse: ...

app.include_router(router)
```

**Missing `response_model`** on all 8 endpoints disables automatic OpenAPI docs generation, response validation, and serialization. Effort: **M**. Risk: **Low** (behavior-preserving).

---

### F-LIB-02 · `proxies/llm/proxies_provider.py` — **Missing Pydantic request models on LLM endpoints**

Endpoints accept raw `Request` and manually call `await request.json()` or `await request.form()`. FastAPI can deserialize, validate, and document these natively via Pydantic models as function parameters.

**Current:**
```python
async def _chat_completions_endpoint(self, request: Request):
    body = await request.json()
    result = self.extract_and_validate_model(body)
```

**FastAPI native:**
```python
class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[MessageDict]
    stream: bool = False

@router.post("/chat/completions")
async def chat_completions(body: ChatCompletionRequest) -> StreamingResponse | ChatCompletionResponse:
    ...
```

Benefit: automatic validation, documentation, removal of `extract_and_validate_model` boilerplate. Effort: **M**. Risk: **Low**.

---

### F-LIB-03 · `proxies/llm/proxies_provider.py` — **WebSocket registered via `add_websocket_route` on FastAPI**

```python
app.add_websocket_route("/responses", self.websocket_provider.websocket_response_endpoint)
```

FastAPI provides `@app.websocket("/responses")` decorator and strongly encourages it over the raw Starlette `add_websocket_route`. Using `add_websocket_route` on a FastAPI instance also bypasses FastAPI dependency injection. Effort: **S**. Risk: **Low**.

---

### F-LIB-04 · `starlette_app.py` — **Manual lifespan composition via `partial()`**

The Starlette `lifespan=` is wired as `partial(self.lifespan_manager.lifespans, mcp_apps=..., remote_resources=...)`. FastAPI/Starlette 0.20+ support `@asynccontextmanager` directly; `AppLifespanManager` already uses `@asynccontextmanager` internally. The `partial()` wrapper can be eliminated by giving `AppLifespanManager` a `__call__` that matches the Starlette `(app)` signature directly and captures `mcp_apps` + `remote_resources` as constructor args. Effort: **S**. Risk: **Low**.

---

## DRY / Reuse Findings

### F-DRY-01 · `proxies/mcp/proxy_provider.py` — **6× repeated resource-attach pattern**

The following private methods share the exact same structural pattern: (1) get dirs from config, (2) validate dirs, (3) create provider, (4) register to mcp:

- `_add_skill_proxy`
- `_add_remote_skill_proxy`
- `_add_prompt_proxy`
- `_add_remote_prompt_proxy`
- `_add_agent_proxy`
- `_add_remote_agent_proxy`

All six are ~20–35 lines each with identical validation logic and error logging.

**Proposed abstraction:**
```python
def _attach_resource(
    self,
    mcp: FastMCP,
    resource_type: str,
    dirs: list[str],
    provider_factory: Callable[[McpConfig, list[str]], object],
    register_fn: Callable[[object, FastMCP], int],
) -> None:
    valid_dirs = self._validate_resource_directories(dirs, resource_type)
    if not valid_dirs:
        return
    provider = provider_factory(self.config, valid_dirs)
    count = register_fn(provider, mcp)
    logger.info("Registered %d %s(s) for path '%s'", count, resource_type, self.config.path)
```

This eliminates ~120 lines of duplicated code with one generic helper. Effort: **M**. Expected reduction: ~70%.

---

### F-DRY-02 · `proxies/llm/proxies_provider.py` — **5× LLM endpoint method boilerplate**

`_chat_completions_endpoint`, `_embeddings_endpoint`, `_audio_transcriptions_endpoint`, `_audio_translations_endpoint`, `_images_generations_endpoint` all follow this pattern:

```python
body = await request.[json|form]()
result = self.extract_and_validate_model(body)
if isinstance(result, JSONResponse):
    return result
provider_name, model_name = result
return await self._call_openai_endpoint(provider_name=..., model_name=..., payload=..., ...)
```

**Proposed abstraction:** A `_dispatch_json_endpoint` and `_dispatch_form_endpoint` wrapper that handles body extraction + validate + call in one place, each endpoint providing only the discriminating `known_params`, `call_fn`, `response_builder`. This reduces ~200 lines to ~60 lines. Effort: **M**.

---

### F-DRY-03 · `app/auth_provider_registry.py` + `app/client_auth_handler_factory.py` — **Two parallel match blocks for `AuthType`**

Both files contain a `match name:` switch over the same `AuthType` enum to create the inward (FastMCP) and outward (httpx) auth objects respectively. Adding a new provider type requires editing both files in the same structural way.

**Proposed abstraction:** A single `AuthTypeConfig` registry that stores `(fastmcp_factory, httpx_factory)` per `AuthType`, so adding new providers is a single-entry change. Effort: **S–M**.

---

## SOLID Findings

### F-SOLID-01 · `proxies/llm/proxies_provider.py` — **`LlmProxiesProvider` violates SRP** (~600 lines)

`LlmProxiesProvider` is simultaneously:
1. HTTP routing controller (registers 8 routes + 1 WebSocket).
2. Request parsing + model extraction + parameter splitting.
3. Model list cache manager.
4. Streaming response formatter.
5. Anthropic ↔ OpenAI request/response converter delegation.
6. FastAPI app wiring (dependency injection, middleware).

**Fix:** Split into at least:
- `LlmRouter` — FastAPI app construction and route registration only.
- `LlmRequestDispatcher` — model extraction, parameter building, call delegation.
- Keep `LlmProxiesProvider` as a thin orchestrator wiring these together.

---

### F-SOLID-02 · `proxies/mcp/proxy_provider.py` — **`McpProxyProvider` violates SRP** (~250 lines)

`McpProxyProvider.create_proxy()` does:
1. FastMCP server creation.
2. MCP spec proxy creation.
3. OpenAPI proxy creation + route filtering.
4. Auth setup.
5. Skill/agent/prompt wiring (delegated but orchestrated here).
6. Caching of the created `FastMCP` instance.

**Fix:** Extract `McpServerFactory` (creates a bare `FastMCP` with transforms) and keep `McpProxyProvider` as a decorator that wires extensions onto the base server.

---

### F-SOLID-03 · `app/app_config_provider.py` — **`AppConfigProvider` violates ISP**

`AppConfigProvider` exposes both:
- Server-side auth (`get_fast_mcp_auth_provider`)
- Client-side auth (`get_client_auth_handler`)
- MCP config (`get_mcp_configs`)
- LLM config (`get_llm_configs`)
- Remote resources (`get_remote_resources`)

Callers in `proxies/` only need the auth factories, not the config getters. `Protocols.AuthProviderFactory` already partially solves this for auth but `AppConfigProvider` itself is not split.

**Fix:** Consider splitting into `AppConfigReader` (pure config getters) and keeping `AppConfigProvider` as auth-factory only, implementing the `AuthProviderFactory` Protocol.

---

### F-SOLID-04 · `proxies/mcp/base_provider.py` — **DIP violation: shim class couples proxies to app layer**

The `AppConfigProvider` shim in `base_provider.py` pulls the name from the `app` layer into `proxies`, blurring the dependency boundary. Even as a no-op, its presence invites future mis-use.

**Fix:** Remove shim (see F-OOP-05). Enforce boundary via import-linter (already in place — this is one of the two known violations per repo memory).

---

### F-SOLID-05 · `app/cache_provider.py` — **`CacheProvider` mixes store creation with TTL logic**

`CacheProvider` is a static-attribute class that doubles as both a factory (`_create_key_value_store`, `get_oauth_store`, `get_cache_store`) and effectively a singleton store holder (`token_storage`, `cache_storage` as class-level mutable state). `TTLAsyncKeyValue` is a clean wrapper but lives in the same file.

**Fix:** Move `TTLAsyncKeyValue` to its own `ttl_key_value.py` module. Split `CacheProvider` into a factory (`CacheStoreFactory`) and a services locator (`AppCacheRegistry`). Effort: **S**.

---

## Best Practices Findings

### F-BP-01 · `auth/api_auth_provider.py` — **Pydantic v1 compat import**

```python
from pydantic.v1 import AnyHttpUrl
```

This project enforces Pydantic v2. The `pydantic.v1` compatibility shim should not be used. Replace with `pydantic.AnyUrl` or `str` where appropriate.

---

### F-BP-02 · `app/app_config_provider.py` — **Missing module docstring and `from __future__ import annotations`**

The first line is a bare import (`from typing import TYPE_CHECKING, Any`). Both conventions are required by `AGENTS.md`.

---

### F-BP-03 · `app/cache_provider.py` — **Missing module docstring**

File starts directly with imports — no module-level docstring required by convention.

---

### F-BP-04 · `app/auth_provider_registry.py` + `app/client_auth_handler_factory.py` — **Return type `object`**

```python
def create(...) -> object:
```

The return type should be `AuthProvider` (from `fastmcp.server.auth`) and `httpx.Auth` respectively. Using `object` disables all downstream type-checking for callers.

---

### F-BP-05 · `utils/security.py` — **Uses `Optional` and `Any`**

```python
from typing import Any, Optional
```

Both `Optional[X]` and `Any` violate the project's Python 3.10+ type conventions: use `X | None` and `object | Protocol` respectively. The function signature `def sanitize_error_response(...) -> JSONResponse` is fine, but `Optional` usages in parameter annotations need replacement.

---

### F-BP-06 · `proxies/llm/proxies_provider.py` — **Commented-out dead code block**

```python
# _BLOCKED_FORWARD_HEADERS = {
#     "authorization",
#     ...
# }
# _BLOCKED_FORWARD_PREFIXES = ("x-forwarded-",)
```

This large commented block (11 lines) should be removed or replaced with a TODO issue reference.

---

### F-BP-07 · `proxies/llm/proxies_provider.py` — **LLM endpoint methods missing `async` return type annotations**

```python
async def _chat_completions_endpoint(self, request: Request):
async def _embeddings_endpoint(self, request: Request):
```

All 8 endpoint methods lack return type annotations. FastAPI fully supports typed returns and uses them for `response_model` inference.

---

### F-BP-08 · `proxies/llm/base_provider.py` — **`Any` type in `Mapping` parameter**

`LlmBaseProvider` uses `from typing import Any, Mapping` — both flagged by the project's no-`Any` policy.

---

### F-BP-09 · `app/server.py` — **`from typing import Any` import**

Line 1: `from typing import TYPE_CHECKING, Any`. The `Any` type is used as the type for `llm_services` tuple. Replace with the concrete `LlmProxiesProvider` type (already imported via `TYPE_CHECKING`).

---

## Prioritized Recommendations

| # | Action | Rationale | Impact | Effort | Risk |
|---|---|---|---|---|---|
| **1** | Wrap `middleware_provider.py` in `MiddlewareProvider` class | Hardest OOP violation; no class at all | High | S | Low |
| **2** | Remove `AppConfigProvider` shim from `base_provider.py` | Fixes layering violation + naming confusion | High | S | Low |
| **3** | Move `parse_frontmatter` / `compute_file_hash` into `AgentParser` class | OOP violation with business logic outside class | Medium | S | Low |
| **4** | Wrap `security.py` functions in `SecurityUtils` static class | OOP convention compliance + mockability | Medium | S | Low |
| **5** | Extract `_attach_resource` helper in `proxy_provider.py` | Eliminates 6× duplicated resource-attach boilerplate | High | M | Low |
| **6** | Add `APIRouter` + `response_model` to all LLM endpoints | Library-native compliance, enables OpenAPI docs | High | M | Low |
| **7** | Refactor `LlmProxiesProvider` → `LlmRouter` + `LlmRequestDispatcher` | SRP; file is 600+ lines | High | M | Med |
| **8** | Unify `AuthProviderRegistry` + `ClientAuthHandlerFactory` into one registry | DRY; single-point extension | Medium | S | Low |
| **9** | Split `config_yaml.py` into models + loader | Reduce 500+ line module | Medium | M | Low |
| **10** | Fix `pydantic.v1` import in `api_auth_provider.py` | Pydantic v2 compliance + correctness | High | S | Low |
| **11** | Add return types to all LLM endpoint methods | Type-hint completeness (`AGENTS.md` requirement) | Medium | S | Low |
| **12** | Replace `Optional` / `Any` in `security.py` | Python 3.10+ convention | Low | S | Low |
| **13** | Move `TTLAsyncKeyValue` out of `cache_provider.py` | SRP, file cohesion | Medium | S | Low |

---

## Migration Strategy

### Phase 1 — Quick Wins (1–2 days, zero behavior change)

These are pure structural moves with no logic change:

1. **F-OOP-01** — Create `MiddlewareProvider` class; move all functions in as private methods; keep module-level `get_middlewares()` as a compatibility shim calling `MiddlewareProvider(cache).build()`.
2. **F-OOP-05** — Delete `AppConfigProvider` compatibility shim from `base_provider.py`; update any test patches to the canonical `app.app_config_provider.AppConfigProvider` path.
3. **F-OOP-02** — Move `parse_frontmatter` and `compute_file_hash` into `AgentParser` class in same file.
4. **F-OOP-03** — Wrap `security.py` functions in `SecurityUtils` static class.
5. **F-BP-01** — Replace `pydantic.v1.AnyHttpUrl` with `pydantic.AnyUrl`.
6. **F-BP-02/03** — Add missing module docstrings.
7. **F-BP-04** — Narrow return types on registry factories.
8. **F-BP-06** — Delete commented-out `_BLOCKED_FORWARD_HEADERS`.

---

### Phase 2 — Medium Refactors (3–5 days)

9. **F-DRY-01** — Extract `_attach_resource` in `McpProxyProvider`.
10. **F-LIB-01/02** — Introduce `APIRouter` in `LlmProxiesProvider`; define Pydantic request models for at least `ChatCompletionRequest` and `EmbeddingsRequest`; add `response_model` to each route.
11. **F-DRY-03** — Consolidate `AuthProviderRegistry` + `ClientAuthHandlerFactory` into a unified registry.
12. **F-BP-05** — Purge `Optional` / `Any` from `security.py`.

---

### Phase 3 — Long-Horizon Boundary Redesign (1–2 weeks)

13. **F-SOLID-01** — Split `LlmProxiesProvider` into `LlmRouter` + `LlmRequestDispatcher`.
14. **F-SOLID-02** — Extract `McpServerFactory` from `McpProxyProvider`.
15. **F-SOLID-03** — Split `AppConfigProvider` into `AppConfigReader` + auth factory role.
16. **F-OOP-06** — Split `config_yaml.py` into models file + loader file.
17. **F-LIB-04** — Replace `partial()` lifespan wiring with clean dataclass in `AppLifespanManager`.

---

## Validation Plan

```bash
# After each Phase 1 step — run full targeted regression suite
/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest \
    tests/test_api_auth_provider.py \
    tests/test_auth_pass_through.py \
    tests/test_azure_oauth.py \
    tests/test_mcp_proxy_provider.py \
    tests/test_openapi_mcp_provider.py \
    tests/test_llm_proxies_provider.py \
    tests/test_middleware.py \
    tests/test_security.py \
    -q

# Full suite
/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest -q

# Type checking
pyright

# Lint
flake8 src tests

# Import-linter (verify no new layering violations introduced)
lint-imports --config src/drunk_ai_proxy/.importlinter
```

---

## Open Questions

1. **`pydantic.v1.AnyHttpUrl` in `api_auth_provider.py`** — is `TokenVerifier.base_url` typed as `AnyHttpUrl` in fastmcp itself? If so, the v1 compat import may be forced by the library until fastmcp updates to Pydantic v2. Confirm before replacing.
2. **`LlmProxiesProvider` scope** — are all 8 endpoints intended to remain in a single class, or is there a planned split already tracked elsewhere? Confirms Phase 3 scope.

---

**Report File:** /Users/steven/_CODE/drunk-mcp-proxy/docs/architecture/reviews/architecture-review-20260313-153911.md
