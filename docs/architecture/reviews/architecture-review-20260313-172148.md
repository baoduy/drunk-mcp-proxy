# Architecture Review — src/drunk_ai_client

**Status:** PLANNED → [refactor-plan-20260313-172424.md](../../refactoring/refactor-plan-20260313-172424.md)

## Scope + Assumptions
- Scope reviewed: `src/drunk_ai_client/drunk_ai_client/client.py`, `src/drunk_ai_client/drunk_ai_client/main.py`, `src/drunk_ai_client/drunk_ai_client/__init__.py`.
- Review date: 2026-03-13.
- Assumption: Repository standards in `AGENTS.md` and `.github/copilot-instructions.md` are mandatory (class-first design, no module-level procedural business logic).
- Library-native references grounded against current docs snapshots from Context7:
  - FastAPI (`/fastapi/fastapi`) guidance on `APIRouter`/dependency composition.
  - FastMCP (`/prefecthq/fastmcp`) guidance on stdio runtime and proxying (`create_proxy`, `FastMCP.from_client`, composition).

## Architecture Scorecard (0–5)
- OOP/class-per-module: **1.0/5**
- Library-native usage: **4.0/5**
- DRY/reuse: **3.0/5**
- SOLID compliance: **2.5/5**
- Layering/dependency direction: **4.0/5**
- Security architecture: **3.5/5**
- Naming/readability: **4.0/5**
- Testability: **2.5/5**

## OOP/Class Findings (P0 — first)

### P0-1 — Mixed responsibilities + procedural orchestration in module
- **Module:** `src/drunk_ai_client/drunk_ai_client/client.py`
- **Violation type:** mixed responsibility, procedural logic outside class, mutable module-level state.
- **Evidence:**
  - Module-level state mutation before imports: line 36 (`os.environ.setdefault(...)`).
  - Multiple class families + orchestration functions in same file: `ResourceSyncManager` (72–358), `ClientConfig` (361–460), plus top-level business/orchestration functions `create_authenticated_client` (462–478), `sync_remove_resources` (481–511), `run_stdio_bridge` (515–549).
- **Recommended primary class:** `StdioBridgeApplication`.
- **What to move into it:**
  - `run_stdio_bridge` startup sequence.
  - Client creation/auth decisions.
  - startup sync workflow invocation.
  - transform registration and server mount/run lifecycle.
  - encapsulate env/log-level bootstrap in an initialization method (not module body).

### P0-2 — Missing single primary class boundary in entrypoint module
- **Module:** `src/drunk_ai_client/drunk_ai_client/main.py`
- **Violation type:** missing primary class.
- **Evidence:** only top-level function `main()` at lines 8–10.
- **Recommended primary class:** `ClientCliEntrypoint`.
- **What to move into it:**
  - `main()` forwarding behavior as class method (e.g., `run()`), keeping module-level `main()` as thin adapter only if packaging requires it.

### P0-3 — Overloaded domain model + service concerns in same module
- **Module:** `src/drunk_ai_client/drunk_ai_client/client.py`
- **Violation type:** mixed responsibilities.
- **Evidence:** domain/data models (`ResourceSummary`, `ResourceFile`, `ResourceManifest` at 46–69), config parsing (`ClientConfig` at 361–460), sync service (`ResourceSyncManager` at 72–358), and application composition (`run_stdio_bridge` at 515–549) coexist.
- **Recommended primary class:** `StdioBridgeApplication` in this module, with extraction of support classes into dedicated modules:
  - `resource_sync_manager.py`
  - `client_config.py`
  - `resource_models.py`

## Library-Native Findings
- **Good use of FastMCP proxy composition:** `create_proxy(client)` + `server.mount(proxy)` in `run_stdio_bridge` (533, 546) aligns with FastMCP composition docs.
- **Potential simplification:** replace manual `create_proxy` + mount sequence with `FastMCP.from_client(...)` where feature parity is sufficient.
  - Current hand-rolled path: 530–546.
  - Built-in alternative: `FastMCP.from_client(...)`.
  - Effort: **S**.
- **Good use of stdio transport:** explicit `server.run(transport="stdio")` (549), aligned with FastMCP stdio guidance.

## DRY/Reuse Findings
- **Duplicated resource content write logic**
  - Locations: 262–266 and 298–303.
  - Proposed abstraction: private `_write_resource_content(file_path, content)` utility in `ResourceSyncManager`.
  - Expected gain: centralize blob/text handling and reduce branching bugs.
- **Repeated path-security checks + path materialization**
  - Locations: 248–252 and 286–289.
  - Proposed abstraction: `_resolve_safe_path(base_dir, resource_name) -> Path | None`.
  - Expected gain: single security boundary for traversal protection.

## SOLID Findings
- **SRP violation**
  - File/class area: `client.py` module-level composition.
  - Evidence: env parsing, auth construction, sync behavior, and runtime/server lifecycle all in one module.
  - Minimal fix: move orchestration into `StdioBridgeApplication`; keep config and sync as collaborators.
- **DIP violation**
  - File/class: `ResourceSyncManager.__init__` (75–80).
  - Evidence: dependency on concrete `Client[Any]` instead of protocol abstraction.
  - Minimal fix: define `ResourceClientProtocol` with `list_resources` and `read_resource`; depend on protocol.
- **OCP pressure point**
  - File/class: `ResourceSyncManager._matches_pattern` and `_extract_name` (326–358).
  - Evidence: URI style branching (`/suffix` vs `.suffix`) embedded in conditionals.
  - Minimal fix: strategy object for URI parsing if additional resource schemes are expected.

## Best Practices Findings
- **Type hint quality:** `Any` usage appears in `Client[Any]` annotations (77, 462), conflicting with repo preference to avoid `Any` where possible.
- **Docstring coverage gaps:** `_get_env_int` (445–449) and `_get_env_bool` (452–460) lack Google-style docstrings.
- **Logger pattern:** compliant (`logger = logging.get_logger(__name__)`, module-level).
- **Error handling:** broad `except Exception` without logging in `_get_resource_manifest` (231–232) suppresses diagnostics; repository guidance favors logging exception type.
- **Module-level side effect:** `os.environ.setdefault(...)` at line 36 mutates global process state at import time.

## Prioritized Recommendations
1. **[P0] Introduce `StdioBridgeApplication` and move orchestration into class methods.**
   - Rationale: satisfies hard class-first architecture rule.
   - Impact: High maintainability/testability.
   - Effort: **M**.
   - Risk: **Medium** (entrypoint behavior changes).
2. **[P0] Split `client.py` into one-primary-class modules.**
   - Rationale: resolves mixed responsibilities and enforces module boundaries.
   - Impact: High architecture clarity.
   - Effort: **M**.
   - Risk: **Medium** (imports/packaging adjustments).
3. **[P1] Add protocol abstraction for resource client dependency.**
   - Rationale: improves DIP and unit-test mockability.
   - Impact: Medium.
   - Effort: **S**.
   - Risk: **Low**.
4. **[P1] Extract duplicated file-write/path-guard helpers.**
   - Rationale: DRY + safer future extension.
   - Impact: Medium.
   - Effort: **S**.
   - Risk: **Low**.
5. **[P2] Replace broad silent exception in manifest read path with type-only logging + narrow exceptions.**
   - Rationale: improves observability/security posture.
   - Impact: Medium.
   - Effort: **S**.
   - Risk: **Low**.
6. **[P2] Evaluate `FastMCP.from_client` for runtime simplification.**
   - Rationale: reduce custom composition code where no transform limitation exists.
   - Impact: Low-Medium.
   - Effort: **S**.
   - Risk: **Low**.

## Migration Strategy
- **Phase 1 (quick wins, low risk):**
  - Add protocol interface for client dependency.
  - Extract duplicated write/path helpers.
  - Add missing docstrings and exception-type logging.
- **Phase 2 (structural):**
  - Introduce `StdioBridgeApplication` class in `client.py` and route existing functions through methods.
  - Keep backward-compatible top-level wrappers during transition.
- **Phase 3 (module boundary enforcement):**
  - Split config/sync/models into dedicated modules, one primary class each.
  - Keep package exports stable in `__init__.py` to avoid external breakage.
- **Rollback path:**
  - Preserve adapter wrappers (`run_stdio_bridge`, `main`) until tests stabilize; revert wrappers to original function wiring if regressions appear.

## Validation Plan
- Targeted tests:
  - `python -m pytest tests/test_client_sync.py -q`
  - `python -m pytest tests/test_package_imports.py -q`
- Broader safety net:
  - `python -m pytest -q`
- Static quality checks:
  - `pyright`
  - `flake8 src/drunk_ai_client tests`
- Architecture guardrails:
  - Add/update import-linter contracts for `drunk_ai_client` module boundaries (after refactor) to prevent future class/module drift.

## Open Questions
- Is preserving CLI/environment precedence behavior exactly as-is (CLI over env) a hard compatibility requirement for downstream users?
- Are search transforms (`RegexSearchTransform`, `BM25SearchTransform`) mandatory for all client modes, or can they be optional/configurable during refactor?