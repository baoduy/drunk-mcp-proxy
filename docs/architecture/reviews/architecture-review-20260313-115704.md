# Architecture Review — HTTPS Remote Resources for Skills/Prompts/Agents

## Scope + Assumptions
- Scope: enable MCP resource sections (`skills`, `prompts`, `agents`) to support HTTPS-backed content in addition to local `dirs`.
- Request context: user wants syntax like:
  - `skills.dirs: [...]`
  - `skills.remote_resources: [https://...]`
- Assumptions:
  - Keep current startup background sync behavior (non-blocking startup).
  - Preserve current local-directory behavior and compatibility.
  - Prefer minimal, additive changes over rewrites.

## Architecture Scorecard (0–5)
- Library-native usage: **3.5/5**
- DRY/reuse: **3.0/5**
- OOP/class-per-module: **4.0/5**
- SOLID compliance: **3.5/5**
- Layering/dependency direction: **3.0/5**
- Security architecture: **4.0/5**
- Naming/config clarity: **3.0/5**
- Testability: **3.5/5**

## Library-Native Findings
1) Existing design already has a reusable remote sync primitive
- Evidence: `RemoteResourceSyncTask` in `src/drunk_ai_proxy/drunk_ai_proxy/app/tasks/remote_resource_sync_task.py`, wired by `AppLifespanManager.lifespans()` in `src/drunk_ai_proxy/drunk_ai_proxy/app/lifespan.py`.
- Why it matters: this is the correct library-native integration point (Starlette/FastAPI lifespan background orchestration), so section-level HTTPS support should reuse it.
- Replacement recommendation: do **not** add per-provider fetchers; keep one sync pipeline and feed it expanded configs.
- Effort: **S**

2) Current resource section model cannot represent remote resources
- Evidence: `McpResourceConfig` only has `dirs` in `src/drunk_ai_proxy/drunk_ai_proxy/utils/config_yaml.py`.
- Why it matters: user-provided `skills.remote_resources` currently lands in `extra` (because `ConfigBaseModel.extra="allow"`) and is not consumed by `get_skill_dirs()/get_prompt_dirs()/get_agent_dirs()`.
- Recommendation: add typed remote fields to `McpResourceConfig` and normalize them into top-level `RemoteResourceConfig` inputs for the existing sync task.
- Effort: **M**

3) FastMCP provider usage is correct for local discovery; remote support belongs before provider mounting
- Evidence: `McpProxyProvider._add_skill_proxy`, `_add_prompt_proxy`, `_add_agent_proxy` in `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/proxy_provider.py` and base provider methods in `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/base_provider.py`.
- Why it matters: providers consume local files/directories. Remote URLs should be materialized to local disk first, then existing providers continue unchanged.
- Recommendation: keep provider classes mostly unchanged; only update config expansion + startup sync inputs.
- Effort: **S**

## DRY/Reuse Findings
1) Remote sync config now exists in one place only (top-level), but section-level expansion is missing
- Duplication risk: implementing separate URL-download logic in skills/prompts/agents providers would duplicate validation/retry/TTL logic already in `RemoteResourceSyncTask`.
- Proposed shared abstraction:
  - New class: `RemoteResourceConfigExpander` (e.g., under `src/drunk_ai_proxy/drunk_ai_proxy/app/` or `utils/`)
  - Responsibility: merge top-level `remote_resources` + section-level declarations into one normalized `list[RemoteResourceConfig]`.
- Expected gain: single download path, consistent security controls, lower maintenance.

2) Directory validation logic is shared for local dirs, but remote intent-to-dir mapping is undefined
- Evidence: `_validate_resource_directories()` in `McpBaseProvider` validates resolved local directories.
- Proposed abstraction: add normalization helper that resolves remote resource targets into deterministic local directories before validation.
- Expected gain: avoids ad-hoc path inference in multiple providers.

## OOP/Class Findings
1) Missing dedicated class for config expansion/normalization
- Module: `app/app_config_provider.py`
- Violation type: mixed responsibility risk (raw config access plus future normalization logic if added here).
- Recommended fix: keep `AppConfigProvider` as accessor; create a dedicated class (`RemoteResourceConfigExpander`) and call it from server bootstrap flow.

2) Provider modules remain class-first and should stay that way
- Modules reviewed: `proxies/mcp/base_provider.py`, `proxies/mcp/proxy_provider.py`, `proxies/prompt/prompt_provider.py`, `proxies/agent/custom_agents_directory_provider.py`, `proxies/mcp/custom_skills_directory_provider.py`.
- Recommendation: do not add module-level procedural fetch logic in these files.

## SOLID Findings
1) SRP risk if section-level parsing is embedded into providers
- Evidence: `McpProxyProvider.create_proxy()` already orchestrates auth, mcp/openapi, and resources.
- Minimal fix: move section-level remote parsing/expansion into one dedicated class before runtime wiring.

2) OCP improvement opportunity in config model
- Evidence: `McpResourceConfig` is closed to explicit remote declarations today (only `dirs`).
- Minimal fix: extend with typed remote declarations while preserving existing `dirs` behavior.

3) DIP opportunity
- Evidence: startup flow in `MCPProxyServer.async_run()` directly uses `AppConfigProvider` return values.
- Minimal fix: inject a protocol-backed expander/normalizer into server bootstrap; keep tests mockable.

## Best Practices Findings
- Type hints/docstrings/logger pattern: generally aligned in reviewed files.
- Pydantic v2: in use; however `extra="allow"` can silently accept unsupported section keys (e.g., `skills.remote_resources`) without effect.
- Python syntax: modern style largely followed.
- Key config risk: silent acceptance of unsupported keys can cause operator confusion; add explicit typed fields + validation to fail fast on malformed section-level entries.

## Prioritized Recommendations
1) **Add typed section-level remote declarations**
- Action: extend `McpResourceConfig` with `remote_resources` typed field.
- Rationale: make `skills/prompts/agents` HTTPS intent explicit and validated.
- Impact: High | Effort: M | Risk: Low

2) **Normalize all remote declarations into one startup sync list**
- Action: implement `RemoteResourceConfigExpander` that emits `list[RemoteResourceConfig]` for lifespan sync.
- Rationale: reuse existing security/retry/TTL logic in `RemoteResourceSyncTask`.
- Impact: High | Effort: M | Risk: Low

3) **Define deterministic destination mapping (avoid ambiguous URL-only entries)**
- Action: support object form for section-level entries (recommended):
  - `url` (required)
  - `to_dir` (required for section-level to avoid guesswork)
  - `headers` (optional, future-ready)
  - `enabled` (optional, default true)
- Rationale: URL-only list cannot reliably infer skill folder layout (e.g., `SkillProvider` expects folder containing `SKILL.md`).
- Impact: High | Effort: M | Risk: Medium

4) **Optional compatibility mode for simple URL list**
- Action: if keeping `skills.remote_resources: [https://...]`, map to first configured dir with explicit warning logs.
- Rationale: supports user shorthand, but should be clearly documented as best-effort.
- Impact: Medium | Effort: S | Risk: Medium

5) **Prompt hot-reload gap handling**
- Action: document that prompt provider currently loads at registration and does not auto-reload newly synced files without restart/remount.
- Evidence: `PromptLoader.load_prompts()` is called during registration in `McpPromptProvider`.
- Impact: Medium | Effort: S | Risk: Low

## Recommended Target Config Shape
### Preferred (unambiguous)
```yaml
mcp:
  - path: /resources
    spec_type: mcp
    skills:
      dirs:
        - skills/dknet
        - skills/dotnet
      remote_resources:
        - url: https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/SKILL.md
          to_dir: skills/dotnet/optimizing-ef-core-queries
```

### Backward compatible with existing top-level bundles
```yaml
remote_resources:
  - name: dotnet_skill_efcore
    to_dir: skills/dotnet/optimizing-ef-core-queries
    paths:
      - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/SKILL.md

mcp:
  - path: /resources
    spec_type: mcp
    skills:
      dirs:
        - skills/dotnet
```

## Migration Strategy
### Quick wins (S)
1. Keep top-level `remote_resources` as canonical source for startup sync.
2. Add documentation examples for skills/prompts/agents remote usage.
3. Add startup logs that show resolved remote bundles and destination dirs.

### Medium refactor (M)
1. Add typed section-level remote field(s) to `McpResourceConfig`.
2. Implement `RemoteResourceConfigExpander`.
3. Wire expander in bootstrap (`MCPProxyServer.async_run()`), pass expanded list to `StarletteApp.add_remote_resources()`.
4. Keep provider mounting unchanged (still local dir readers).

### Long-horizon (L)
1. If needed, add dynamic re-registration for prompts after sync completion.
2. Add optional auth headers support in `RemoteResourceSyncTask._download_one()` (already noted by TODO).

### Compatibility + rollback
- Compatibility: existing top-level `remote_resources` and `dirs` continue to work unchanged.
- Rollback: disable section-level expansion path and rely only on top-level bundles.

## Validation Plan
- Unit tests:
  - `python -m pytest tests/test_config_yaml.py -q`
  - `python -m pytest tests/test_lifespan.py tests/test_remote_resource_sync_task.py -q`
  - add/extend tests for section-level parsing + expander behavior (new test module suggested: `tests/test_remote_resource_config_expander.py`).
- Integration slice:
  - `python -m pytest tests/test_mcp_proxy_provider.py tests/test_prompt_loader.py tests/test_custom_agents_directory_provider.py tests/test_custom_skills_directory_provider.py -q`
- Static checks:
  - `pyright`
  - `flake8 src tests`

## Open Questions
1) For section-level `remote_resources`, should `to_dir` be mandatory per URL entry (recommended), or should the system infer a destination from `dirs`/URL path?
2) Should section-level entries be converted into top-level named bundles at load time (for observability), or remain implicit runtime expansions only?
