# Feature Plan: On-Demand HTTPS Resources for Skills, Prompts, and Agents (No Local Sync)

## Goal
Support remote HTTPS resources for `skills`, `prompts`, and `agents` as **on-demand resources** that are fetched only when requested, then cached in cache storage with TTL derived from `REMOTE_RESOURCE_TTL_HOURS`.

## User Requirement (Updated)
- Do not download MCP remote resources to local filesystem at startup.
- Keep resources remote-first.
- Fetch on first access.
- Cache response content via cache manager (`CacheProvider.get_cache_store()`) with TTL tied to `REMOTE_RESOURCE_TTL_HOURS`.
- All section-level `remote_resources` entries are always enabled (no `enabled` flag).
- URI is auto-built from remote URL(s); config should not require manual `uri`.
- Skills support multiple URLs per resource entry; non-`SKILL.md` files are treated as supporting files.
- Multi-file support-file semantics apply only to skills (not agents/prompts).

## Current State (Verified)
- Startup sync exists today via `RemoteResourceSyncTask` and writes files under `CONFIG_DIR`.
- Resource providers (`SkillProvider`, `AgentProvider`, `PromptLoader`) currently read local filesystem paths.
- Generic TTL cache exists via `TTLAsyncKeyValue` and `CacheProvider.get_cache_store()`.

Conclusion: current architecture must introduce a provider-level remote resource reader abstraction instead of startup file sync.

---

## Design Decision (Recommended)
Introduce an **On-Demand Remote Resource Layer** that is invoked during resource read/list paths and backed by `TTLAsyncKeyValue`.

### Principles
1. **No startup download** for MCP section-level remotes.
2. **Remote fetch on demand** in `_read_resource` and prompt template materialization paths.
3. **Cache-aside strategy** with TTL in seconds = `REMOTE_RESOURCE_TTL_HOURS * 3600`.
4. **Preserve existing local dirs behavior**; remote and local can coexist.
5. **Keep top-level `remote_resources` feature as legacy-compatible**, but disable by default for MCP section resources when this mode is enabled.

---

## Proposed Config Shape

### Section-level remote declarations (preferred)
```yaml
mcp:
  - path: /resources
    spec_type: mcp
    skills:
      dirs:
        - skills/dknet
      remote_resources:
        - name: efcore-skill
          urls:
            - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/SKILL.md
            - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/query-plan.md
            - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/examples.md
    prompts:
      remote_resources:
        - name: code-review
          url: https://example.com/prompts/code-review.md
    agents:
      remote_resources:
        - name: reasoning-engine
          url: https://example.com/agents/reasoning-engine.md
```

### Optional shorthand compatibility
```yaml
skills:
  remote_resources:
    - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/SKILL.md
```

Normalization for shorthand:
- Auto-generate `uri` and `name` with deterministic rules derived from URL path.
- Log warning recommending explicit object form.

URI derivation rules:
- Skills: derive skill base URI from URL path folder containing `SKILL.md`.
  - `SKILL.md` maps to main skill resource.
  - All non-`SKILL.md` files map as support-file resources under same skill namespace.
- Agents: derive one agent URI from single URL; reject multi-file payloads.
- Prompts: derive one prompt URI from single URL; reject multi-file payloads.

---

## Architecture Changes

### 1) New typed model for section-level on-demand remotes
File: `src/drunk_ai_proxy/drunk_ai_proxy/utils/config_yaml.py`

Add model:
- `OnDemandRemoteResourceConfig`
  - `name: str`
  - `url: str | None = None` (single-file source for agents/prompts)
  - `urls: list[str] | None = None` (multi-file source for skills)
  - `headers: dict[str, str] | None = None` (optional/private endpoints)

Extend `McpResourceConfig`:
- `remote_resources: list[str | OnDemandRemoteResourceConfig] = []`

Validation:
- all URLs must be `https://`.
- no `enabled` field is allowed (implicit enabled=true always).
- skills allow `urls` with one-or-more files; at least one file should be `SKILL.md`.
- agents/prompts allow only single `url` and reject `urls` lists.
- derived URIs must be unique inside each section.

### 2) New cache-backed fetch service
New file (recommended):
- `src/drunk_ai_proxy/drunk_ai_proxy/proxies/resource/on_demand_remote_resource_service.py`

Responsibilities:
- `get_content(uri, url, headers) -> bytes | str`
- `get_many(skill_base_uri, urls, headers) -> dict[str, bytes | str]` (skills only)
- cache key format: `remote_resource:{uri}`
- cache metadata: `{content, content_type, etag?, last_modified?, fetched_at}`
- TTL: `get_env_int("REMOTE_RESOURCE_TTL_HOURS", REMOTE_RESOURCE_TTL_HOURS) * 3600`
- security checks:
  - https-only
  - `follow_redirects=False`
  - extension/content-type allow-list
  - max response size
- optional conditional request support:
  - send `If-None-Match` when cached ETag exists
  - handle `304 Not Modified` by extending cached freshness

### 3) Provider integration points

#### Skills
- Integrate remote URI lookup + fetch in skill resource read paths with URI derivation from URL.
- Keep local `CustomSkillsDirectoryProvider` for existing dirs.
- Add companion provider for purely remote skills if URI is not local.
- Implement support-file mapping: any file in `urls` not named `SKILL.md` is exposed as a skill support resource.

#### Agents
- In `AgentProvider._read_resource`, allow remote-backed read when derived agent URI maps to config.
- Keep manifest generation; include `source: remote|local` metadata.
- Enforce one remote URL per agent resource entry.

#### Prompts
- Avoid startup-only local loading for remote prompt templates.
- Add remote template fetch in prompt render path (or lazy preload during first registration call per prompt).
- Cache parsed template object or raw markdown by URI.
- Enforce one remote URL per prompt resource entry.

### 4) Startup/lifespan behavior
- Keep existing startup/lifespan flow unchanged.
- Keep root-level `remote_resources` startup sync behavior exactly as-is.
- Section-level on-demand remote resources are implemented at provider/read layer only and do not alter root-level sync orchestration.

---

## Detailed Execution Plan

### Phase 1 — Config + contracts
1. Add `OnDemandRemoteResourceConfig` model and validators.
2. Extend `McpResourceConfig` with typed `remote_resources`.
3. Add helper methods in `McpConfig`:
   - `get_skill_remote_resources()`
   - `get_prompt_remote_resources()`
   - `get_agent_remote_resources()`
4. Add URI derivation utility:
  - `build_skill_resource_uris(urls)`
  - `build_agent_resource_uri(url)`
  - `build_prompt_resource_uri(url)`

### Phase 2 — On-demand fetch/cache service
1. Implement `OnDemandRemoteResourceService` with injected dependencies:
   - `cache: TTLAsyncKeyValue`
   - `http_client: httpx.AsyncClient`
2. Implement cache-aside and TTL behavior using `REMOTE_RESOURCE_TTL_HOURS`.
3. Add secure request constraints and error sanitization.

### Phase 3 — Provider wiring
1. Add a remote resource registry per MCP route during proxy creation.
2. Wire providers to consult local first, then remote registry.
3. Ensure all remote reads pass through the on-demand service.

### Phase 4 — Deprecation and compatibility
1. Keep top-level `remote_resources` behavior for backward compatibility.
2. Add warnings when both top-level sync and section-level on-demand point to the same content.
3. Document migration path from `to_dir/paths` bundles to `uri/url` entries.

### Phase 5 — Documentation
1. Update `data/config.yaml` with on-demand examples.
2. Update docs to explain cache TTL behavior and lazy fetch semantics.
3. Clarify first-read latency and cache-hit behavior.

---

## Testing Plan

### New tests
1. `tests/test_on_demand_remote_resource_service.py`
   - cache miss fetch and set
   - cache hit bypass network
   - TTL expiry refetch
   - 304 handling with ETag (if implemented)
   - size/extension/https validation

2. `tests/test_config_yaml.py` additions
   - parse section-level `remote_resources` object + shorthand
  - verify `enabled` is rejected / ignored in strict mode
  - verify URI derivation input constraints by section
   - reject non-https URLs
  - reject `urls` list usage in agents/prompts
  - validate skills multi-file behavior (`SKILL.md` + support files)

3. Provider tests
   - `tests/test_custom_skills_directory_provider.py` remote fallback
   - `tests/test_agent_provider.py` remote-backed reads
   - `tests/test_prompt_loader.py`/`tests/test_prompt_provider.py` lazy remote template behavior

### Existing tests to adjust
- No lifespan behavior changes required.
- Keep `tests/test_lifespan.py` and `tests/test_remote_resource_sync_task.py` expectations unchanged for root-level `remote_resources`.

---

## Risks and Mitigations
1. **First request latency**
   - Mitigation: optional background warm-up endpoint or explicit prefetch command.
2. **Remote endpoint instability**
   - Mitigation: serve stale-on-error when cache entry exists.
3. **SSRF/security surface**
   - Mitigation: strict https-only, host allow-list option, no redirects, size limits.
4. **Prompt registration model mismatch**
   - Mitigation: introduce lazy prompt template materialization path, not startup-only disk scan.

---

## Rollout Strategy
1. Introduce on-demand service and config model behind feature flag.
2. Enable for `skills` first, then `agents`, then `prompts` (prompts are most coupled to startup loading).
3. Monitor cache hit ratio and remote fetch error metrics.
4. Default flag to on-demand once stable.

---

## Acceptance Criteria
- MCP section-level remote resources are not downloaded to local filesystem at startup.
- First resource access fetches remote content and stores cache entry with TTL based on `REMOTE_RESOURCE_TTL_HOURS`.
- Subsequent accesses within TTL are served from cache.
- On TTL expiry, resource is refetched and cache refreshed.
- Local `dirs` resources continue to function unchanged.
- No section-level `enabled` flag is required or processed.
- URIs are auto-derived from URL(s), not manually specified.
- Skills remote entries support multiple files; non-`SKILL.md` files are exposed as skill support files.
- Agents and prompts do not support multi-file support-file semantics.

---

## Sources Consulted
- OWASP SSRF Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
- MDN ETag header: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ETag
- MDN If-None-Match header: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match
- HTTPX client guidance: https://www.python-httpx.org/advanced/clients/
- Existing architecture analysis in repo: `docs/architecture/reviews/architecture-review-20260313-115704.md`

---

## Status

Implementation completed. All 709 tests passing.

### Completed Tasks

- ✅ Phase 1 — Config models (`OnDemandRemoteResourceConfig`, `McpResourceConfig.remote_resources`, shorthand normalization, `_validate_fields` updated to accept `remote_resources` as a valid non-empty section)
- ✅ Phase 2 — On-demand fetch/cache service (`proxies/resource/on_demand_remote_resource_service.py`) with HTTPS enforcement, extension/content-type validation, size limit, ETag conditional requests, stale-on-error, TTL from `REMOTE_RESOURCE_TTL_HOURS`
- ✅ Phase 3 — Remote skill provider (`remote_skill_provider.py`), remote agent provider (`remote_agent_provider.py`), remote prompt provider (`remote_prompt_provider.py`); wired into `base_provider._add_remote_*_proxy` and called from `proxy_provider.create_proxy()`
- ✅ Phase 4 — Overlap warnings logged when remote resource URIs conflict with existing local provider URIs
- ✅ Phase 5 — `data/config.yaml` updated with on-demand `remote_resources` examples for skills, prompts, and agents sections

### Tests Added / Fixed

- ✅ `tests/test_on_demand_remote_resource_service.py` — 24 new tests (cache miss, cache hit, ETag, stale-on-error, static validation helpers, `get_many`)
- ✅ `tests/test_config_yaml.py` — 24 new tests (`TestOnDemandRemoteResourceConfig`, `TestMcpResourceConfigRemoteResources`, `TestMcpConfigGetRemoteResources`)
- ✅ `tests/test_config_yaml_integration.py` — updated validation error message regex
- ✅ `tests/test_mcp_proxy_provider.py` — added `_add_remote_*_proxy` patches to existing `create_proxy` tests
- ✅ `tests/test_mcp_proxy_provider_extended.py` — added `get_skill/prompt/agent_remote_resources.return_value = []` to all mock configs
- ✅ `tests/test_openapi_mcp_provider.py` — added `_add_remote_*_proxy` `patch.object` entries to `with` blocks
