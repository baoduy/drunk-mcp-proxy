# `remote_resources` — Background Sync for Remote Resource Files

## Status

**Phase:** ✅ **COMPLETE** (Phases 1–4 + enhancements implemented and tested)  
**Priority:** Medium  
**Additive to:** `skill_dir`, `prompt_dir`, `agents_dir` flat fields in `McpConfig` (those are unchanged)

### Completion Summary
- ✅ Phase 1: Config models, accessor, tests
- ✅ Phase 2: RemoteResourceSyncTask with URL validation, TTL freshness, file size guards, per-URL error isolation
- ✅ Phase 3: Lifespan integration, background task scheduling, cancel on shutdown, reload enabled for Skills/Agents providers
- ✅ Phase 4: Config examples, environment variable documentation
- ✅ Latest enhancements: Configurable retry transport, periodic resync loop, per-bundle concurrent downloads, headers placeholder for future auth, explicit env constants

---

## Overview

Currently all resource directories (`skill_dir`, `prompt_dir`, `agents_dir`) only support **local** files that are bundled with the deployment. There is no mechanism to pre-fetch content from remote URLs (GitHub, wikis, CDNs, etc.) into those directories before the MCP providers load them.

The goal is to add a top-level `remote_resources` section to `config.yaml` that:

1. Declares named bundles of remote HTTPS files to be synced to local directories.
2. Downloads files at startup as a **non-blocking background task** (server starts immediately).
3. Only re-downloads a file if it is **older than a configurable TTL** (default 24 h).
4. Only accepts `https://` URLs and a configurable allow-list of file extensions.
5. Silently skips / logs failures so a network hiccup never blocks the proxy from starting.
6. Is completely **additive** — existing `skill_dir`/`prompt_dir`/`agents_dir` fields continue to work unchanged.

### Target YAML shape

`remote_resources` is a **top-level section** in `config.yaml`, parallel to `auth`, `llm`, and `mcp`:

```yaml
# ============================================================================
# REMOTE RESOURCE SYNC CONFIGURATION
# ============================================================================
# Files are downloaded at startup (background, non-blocking) into the data/
# directory. Each entry identifies a named bundle, a local destination folder,
# and a list of HTTPS source URLs.
#
remote_resources:
  - name: dotnet_prompt                  # logical name (used in logs)
    to_dir: prompts/dotnet               # local destination, relative to data/
    paths:
      - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/skills/optimizing-ef-core-queries/SKILL.md

  - name: dotnet_agent
    to_dir: agents/dotnet
    paths:
      - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/agents/ef-core-agent/agent.yaml

  - name: dotnet_skills
    to_dir: skills/dotnet
    paths:
      - https://raw.githubusercontent.com/dotnet/skills/refs/heads/main/plugins/dotnet-data/codebases/ef-core-codebase/codebase.yaml
```

The existing MCP entry then references `to_dir` values like any other local directory:

```yaml
mcp:
  - path: /prompts
    spec_type: mcp
    skill_dir: skills         # picks up skills/dotnet/** after sync
    prompt_dir: prompts       # picks up prompts/dotnet/** after sync
    agents_dir: agents        # picks up agents/dotnet/** after sync
```

> **Important:** `remote_resources` is downloaded in the background. On the very first cold start, files won't be present until the download completes. Subsequent restarts use the cached copies. Design around this expectation.

---

## Current Architecture (as-is)

```
config.yaml
  └─ McpConfig (config_yaml.py)
       ├─ skill_dir: Optional[str]   ← unchanged
       ├─ prompt_dir: Optional[str]  ← unchanged
       └─ agents_dir: Optional[str]  ← unchanged

McpProxyProvider.create_proxy()
  ├─ _create_skill_proxy()   → CustomSkillsDirectoryProvider(roots=[Path])
  ├─ _create_prompt_proxy()  → McpPromptProvider(prompt_dir=str)
  └─ _create_agent_proxy()   → CustomAgentsDirectoryProvider(roots=[Path])
       (all in base_provider.py / proxy_provider.py)
```

Key files:
| File | Role |
|---|---|
| `utils/config_yaml.py` | Pydantic models – `McpConfig`, `McpServerConfig`, `ConfigYaml` |
| `app/lifespan.py` | `AppLifespanManager` – startup/shutdown context manager |
| `app/starlette_app.py` | `StarletteApp` – wires lifespan into Starlette |
| `app/server.py` | `MCPProxyServer` – app entry point |
| `proxies/mcp/base_provider.py` | `McpBaseProvider` – `_create_skill_proxy`, `_create_agent_proxy` |
| `proxies/mcp/proxy_provider.py` | `McpProxyProvider` – `_create_prompt_proxy`, `create_proxy` |
| `proxies/resource/` | **Empty placeholder** – target for new task code |

---

## Proposed Architecture (to-be)

### New Pydantic models (`utils/config_yaml.py`)

```python
class RemoteResourceConfig(ConfigBaseModel):
    """Single named remote resource bundle."""

    name: str = Field(description="Logical name used in logs and cache keys")
    enabled: bool = Field(
        default=True,
        description="Enable/disable sync for this bundle (defaults to true)"
    )
    to_dir: str = Field(
        description="Local destination directory, relative to data/ (e.g. 'prompts/dotnet')"
    )
    paths: list[str] = Field(
        description="Ordered list of HTTPS URLs to download"
    )


class ConfigYaml(ConfigBaseModel):
    auth: Optional[AuthConfig] = Field(default=None)
    llm: Optional[list[LlmConfig]] = Field(default=None)
    mcp: Optional[list[McpConfig]] = Field(default=None)
    remote_resources: Optional[list[RemoteResourceConfig]] = Field(default=None)  # NEW
```

`McpConfig` is **unchanged** — `skill_dir`, `prompt_dir`, `agents_dir` remain exactly as they are. The remote sync simply writes files into the local directories those fields point to.

Per-item sync control is configured directly under `remote_resources` using `enabled: true|false`. When omitted, `enabled` defaults to `true`.

---

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `REMOTE_RESOURCE_TTL_HOURS` | `24` | Minimum age in hours before a cached file is re-downloaded |
| `REMOTE_RESOURCE_ALLOWED_EXTENSIONS` | `.md,.yaml,.yml,.json,.py,.js,.ts` | Comma-separated list of permitted file extensions |
| `REMOTE_RESOURCE_MAX_SIZE_MB` | `10` | Maximum individual file download size in megabytes |

---

### New background task (`app/tasks/remote_resource_sync_task.py`)

Location: `src/drunk_ai_proxy/drunk_ai_proxy/app/tasks/`

The class uses `asyncio` (non-blocking, `httpx.AsyncClient`) and is scheduled as an `asyncio.Task` at lifespan startup — matching the spirit of [FastAPI's background task pattern](https://fastapi.tiangolo.com/tutorial/background-tasks/) but hooked into the existing `AppLifespanManager`.

```python
class RemoteResourceSyncTask:
    """Downloads remote_resources entries to local data/ directories at startup.

    The task runs in the background so the server starts immediately.
    Individual download failures are silently logged and skipped.
    """

    def __init__(self, configs: list[RemoteResourceConfig]) -> None:
        self._logger: Logger = setup_logging(__name__)
        self._configs = configs
        self._ttl_hours: int = int(os.environ.get("REMOTE_RESOURCE_TTL_HOURS", "24"))
        self._allowed_extensions: frozenset[str] = _parse_allowed_extensions()
        self._max_size_bytes: int = int(
            os.environ.get("REMOTE_RESOURCE_MAX_SIZE_MB", "10")
        ) * 1024 * 1024

    async def run(self) -> None:
        """Entry point — iterates all configs, downloads each path."""
        async with httpx.AsyncClient(follow_redirects=False, timeout=30) as client:
            for config in self._configs:
                await self._sync_bundle(client, config)

    async def _sync_bundle(
        self, client: httpx.AsyncClient, config: RemoteResourceConfig
    ) -> None:
        dest_dir = Path(CONFIG_DIR) / config.to_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        for url in config.paths:
            try:
                await self._download_one(client, url, dest_dir, config.name)
            except Exception as e:
                # Never propagate — log exception type only
                self._logger.warning(
                    "Failed to sync '%s' url (skipped): %s", config.name, type(e).__name__
                )

    async def _download_one(
        self,
        client: httpx.AsyncClient,
        url: str,
        dest_dir: Path,
        bundle_name: str,
    ) -> None:
        self._validate_url(url)
        filename = Path(urlparse(url).path).name
        self._validate_extension(filename)

        dest_file = dest_dir / filename

        if self._is_fresh(dest_file):
            self._logger.debug("Cache fresh, skipping: %s", filename)
            return

        response = await client.get(url)
        response.raise_for_status()

        content = response.content
        if len(content) > self._max_size_bytes:
            raise ValueError("File exceeds maximum allowed size")

        dest_file.write_bytes(content)
        self._logger.info(
            "Downloaded '%s' → %s (%d bytes)", bundle_name, dest_file, len(content)
        )

    def _validate_url(self, url: str) -> None:
        """Accept only https:// scheme — reject http, file, ftp, etc."""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError(f"Only https:// URLs are allowed (got scheme '{parsed.scheme}')")

    def _validate_extension(self, filename: str) -> None:
        ext = Path(filename).suffix.lower()
        if ext not in self._allowed_extensions:
            raise ValueError(f"Extension '{ext}' not in allowed list")

    def _is_fresh(self, path: Path) -> bool:
        if not path.exists():
            return False
        age_hours = (time.time() - path.stat().st_mtime) / 3600
        return age_hours < self._ttl_hours
```

---

### Updated `AppLifespanManager` (`app/lifespan.py`)

The lifespan manager receives the `remote_resources` config at construction and schedules `RemoteResourceSyncTask.run()` as a non-awaited `asyncio.Task` — the server is unblocked immediately.

```python
@asynccontextmanager
async def lifespans(
    self,
    _: object,
    mcp_apps: list[tuple[str | None, StarletteWithLifespan]],
    remote_resources: list[RemoteResourceConfig] | None = None,
) -> AsyncGenerator[None, None]:
    # 1. Kick off background resource sync — does NOT block startup
    sync_task: asyncio.Task[None] | None = None
    if remote_resources:
        from drunk_ai_proxy.app.tasks.remote_resource_sync_task import RemoteResourceSyncTask
        sync_task = asyncio.create_task(
            RemoteResourceSyncTask(remote_resources).run(),
            name="remote_resource_sync",
        )
        logger.info("Remote resource sync task scheduled (%d bundles)", len(remote_resources))

    # 2. Start MCP app lifespans as before
    async with self._create_app_lifespans(mcp_apps):
        yield

    # 3. Cancel sync task on shutdown if still running
    if sync_task and not sync_task.done():
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
```

The `StarletteApp.build_with_lifespan()` method passes `remote_resources` through:

```python
# starlette_app.py (partial)
lifespan = partial(
    self.lifespan_manager.lifespans,
    mcp_apps=self.mcp_apps,
    remote_resources=self._remote_resources,  # new
)
```

`self._remote_resources` is set in `StarletteApp.add_remote_resources(configs)` — a new single-purpose method:

```python
def add_remote_resources(self, configs: list[RemoteResourceConfig] | None) -> None:
    """Register remote resource configurations for background sync."""
    self._remote_resources = configs or []
```

Called from `MCPProxyServer.run()` after building the app.

---

### Module layout

```
src/drunk_ai_proxy/drunk_ai_proxy/
├── app/
│   ├── tasks/                              ← NEW directory
│   │   ├── __init__.py                     ← exports RemoteResourceSyncTask
│   │   └── remote_resource_sync_task.py    ← RemoteResourceSyncTask class
│   ├── lifespan.py                         ← MODIFY: schedule sync task
│   └── starlette_app.py                    ← MODIFY: add_remote_resources()
└── utils/
    └── config_yaml.py                      ← MODIFY: RemoteResourceConfig, ConfigYaml.remote_resources
```

---

## File Map — Implementation Status

| Status | Action | File |
|---|---|---|
| ✅ DONE | **Modify** | `utils/config_yaml.py` – add `RemoteResourceConfig` model; add `remote_resources` to `ConfigYaml`; add `headers` placeholder field |
| ✅ DONE | **Modify** | `app/app_config_provider.py` – add `get_remote_resources()` method |
| ✅ DONE | **Modify** | `proxies/mcp/mcp_proxy_provider.py` – pass `reload=True` to `CustomSkillsDirectoryProvider` and `CustomAgentsDirectoryProvider` |
| ✅ DONE | **Create** | `app/tasks/__init__.py` |
| ✅ DONE | **Create** | `app/tasks/remote_resource_sync_task.py` – `RemoteResourceSyncTask` with periodic loop, retry transport, concurrent downloads |
| ✅ DONE | **Modify** | `app/lifespan.py` – add `remote_resources` param to `lifespans()`; schedule task with `name="remote_resource_sync"`; proper cancellation logic |
| ✅ DONE | **Modify** | `app/starlette_app.py` – add `add_remote_resources()`, pass to lifespan |
| ✅ DONE | **Modify** | `app/server.py` – call `starlette_app.add_remote_resources(config_provider.get_remote_resources())` |
| ✅ DONE | **Modify** | `tools/env.py` – add env constants (`REMOTE_RESOURCE_TTL_HOURS`, `REMOTE_RESOURCE_ALLOWED_EXTENSIONS`, `REMOTE_RESOURCE_MAX_SIZE_MB`, `REMOTE_RESOURCE_RETRY_ATTEMPTS`) |
| ✅ DONE | **Create** | `tests/test_remote_resource_sync_task.py` – comprehensive coverage including periodic loop, retry, concurrency |
| ✅ DONE | **Create** | `tests/test_app_config_provider_remote_resources.py` – config provider accessor tests |
| ✅ DONE | **Modify** | `tests/test_lifespan.py` – task scheduling, cancellation, edge case tests |
| ✅ DONE | **Modify** | `tests/test_config_yaml.py` – `RemoteResourceConfig` parsing; `ConfigYaml.remote_resources`; headers placeholder |
| ✅ DONE | **Modify** | `tests/test_starlette_app.py` – add `add_remote_resources()` test |
| ✅ DONE | **Modify** | `tests/test_mcp_proxy_provider.py` – expectations updated for `reload=True` |
| ✅ DONE | **Modify** | `data/config.yaml` – add `remote_resources` section example with multiple bundles |
| ✅ DONE | **Modify** | `docs/configuration/environment-variables.md` – add remote resource env section with defaults and descriptions; included retry env var |
| ✅ DONE | **Modify** | `docs/configuration/config-files.md` – add remote resources structure and field reference |
| ✅ DONE | **Modify** | `docs/examples/configurations.md` – add remote bundle example; corrected code fences; added env examples |

---

## Implementation Phases

### Phase 1 — Config Models (no breaking changes) ✅ COMPLETE
1. ✅ Add `RemoteResourceConfig` model to `config_yaml.py`.
2. ✅ Add `remote_resources: Optional[list[RemoteResourceConfig]]` to `ConfigYaml`.
3. ✅ Add `get_remote_resources() → list[RemoteResourceConfig]` to `AppConfigProvider`.
4. ✅ Add/update unit tests in `test_config_yaml.py`.
5. ✅ Add optional `headers: dict[str, str] | None` placeholder field for future private URL auth.

**Risk:** None. Existing `McpConfig` fields unchanged.

---

### Phase 2 — `RemoteResourceSyncTask` ✅ COMPLETE
1. ✅ Create `app/tasks/__init__.py` and `app/tasks/remote_resource_sync_task.py`.
2. ✅ Implement `RemoteResourceSyncTask` with:
   - ✅ `https://` only URL validation (raise `ValueError` for any other scheme)
   - ✅ Extension allow-list from `REMOTE_RESOURCE_ALLOWED_EXTENSIONS` env var (default `.md,.yaml,.yml,.json,.py,.js,.ts`)
   - ✅ TTL check from `REMOTE_RESOURCE_TTL_HOURS` env var (default 24)
   - ✅ File size guard from `REMOTE_RESOURCE_MAX_SIZE_MB` env var (default 10)
   - ✅ Async periodic loop with configurable sleep interval from TTL hours
   - ✅ Retry transport with `REMOTE_RESOURCE_RETRY_ATTEMPTS` env var (default 2)
   - ✅ Per-bundle concurrent URL downloads via `asyncio.gather(..., return_exceptions=True)`
   - ✅ `dest_dir.mkdir(parents=True, exist_ok=True)` implemented
   - ✅ Per-URL try/except — skips failed URLs, logs only `type(e).__name__`
3. ✅ Write `tests/test_remote_resource_sync_task.py` with comprehensive coverage:
   - ✅ URL scheme validation (`http://` rejected, `ftp://` rejected, `https://` accepted)
   - ✅ Extension validation (`.md` accepted, `.exe` rejected)
   - ✅ TTL fresh check (file mtime < TTL → skip download)
   - ✅ TTL stale check (file mtime ≥ TTL → download)
   - ✅ Successful download writes file to `to_dir`
   - ✅ `httpx.HTTPStatusError` → silently skipped
   - ✅ `httpx.TimeoutException` → silently skipped
   - ✅ File size limit exceeded → silently skipped
   - ✅ Periodic loop cancellation on shutdown
   - ✅ Per-bundle concurrent download logic

**Risk:** `httpx` already available (bundled with `fastmcp`). No new dependencies.

---

### Phase 3 — Lifespan integration + Provider Reload Enablement ✅ COMPLETE
1. ✅ **Enable reload on Skills/Agents providers:**
   - ✅ Modify `proxies/mcp/mcp_proxy_provider.py` to pass `reload=True` when creating `CustomSkillsDirectoryProvider` and `CustomAgentsDirectoryProvider`
   - ✅ Newly-downloaded skill and agent files are discovered on each request
2. ✅ **Integrate RemoteResourceSyncTask:**
   - ✅ Add `remote_resources` parameter to `AppLifespanManager.lifespans()`
   - ✅ Schedule `asyncio.create_task(RemoteResourceSyncTask(remote_resources).run(...), name="remote_resource_sync")` before entering `_create_app_lifespans`
   - ✅ Cancel the task on shutdown if still running
   - ✅ Handle completed tasks (do not cancel if already done)
3. ✅ **Update Starlette app:**
   - ✅ Add `self._remote_resources: list[RemoteResourceConfig] = []` attribute to `StarletteApp`
   - ✅ Add `add_remote_resources(configs)` method
   - ✅ Pass `remote_resources=self._remote_resources` to the lifespan partial
4. ✅ **Update MCPProxyServer:**
   - ✅ Call `starlette_app.add_remote_resources(config_provider.get_remote_resources())` in `run()` after building the app
5. ✅ **Update tests:**
   - ✅ `tests/test_starlette_app.py` – verify `add_remote_resources` stores list correctly
   - ✅ `tests/test_lifespan.py` – verify task scheduling, cancellation, and edge cases

**Note:** `McpPromptProvider` does NOT get reload capability in this phase (see Known Limitations section).

---

### Phase 4 — Config and docs ✅ COMPLETE
1. ✅ Update `data/config.yaml` to show `remote_resources` section example.
2. ✅ Add env var documentation to `docs/` reference for:
   - ✅ `REMOTE_RESOURCE_TTL_HOURS` (default 24)
   - ✅ `REMOTE_RESOURCE_ALLOWED_EXTENSIONS` (default `.md,.yaml,.yml,.json,.py,.js,.ts`)
   - ✅ `REMOTE_RESOURCE_MAX_SIZE_MB` (default 10)
   - ✅ `REMOTE_RESOURCE_RETRY_ATTEMPTS` (default 2)

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Top-level config section | `remote_resources` is a global sync concern, not tied to a single MCP path; placing it at root keeps `McpConfig` clean |
| `to_dir` not `type` | Delegates the "where does this land" decision to the operator, matching existing `skill_dir`/`prompt_dir`/`agents_dir` patterns exactly |
| `asyncio.create_task()` (not blocking `await`) | Allows the Starlette server to start serving requests before downloads are complete; mirrors FastAPI background task semantics |
| `follow_redirects=False` on `httpx` | Prevents SSRF via open-redirect chains; logged URL is the URL actually fetched |
| Only `https://` — no `http` | Mandatory encryption for all remote content fetches |
| Extension allow-list in env var | Operators can add project-specific types without code changes; `.exe`, `.sh`, `.bat` are never in the default list |
| File size cap | Prevents OOM from unexpectedly large files at a URL |
| Write directly to `data/<to_dir>/` | Files land exactly where existing providers already look — no DI changes needed in `_create_skill_proxy` etc. |
| Task cancelled on shutdown | Avoids dangling coroutines if the server is stopped mid-download |
| Per-URL try/except | One bad URL never prevents other URLs in the bundle from being fetched |

---

## Security Considerations

- **SSRF:** Only `https://` scheme accepted; `follow_redirects=False` prevents attacking internal services via open redirects.
- **Path traversal:** Destination is always `Path(CONFIG_DIR) / config.to_dir / filename`. `to_dir` comes from the operator-controlled config file only. URL path component only contributes the filename (via `Path(urlparse(url).path).name`), never directory parts.
- **Extension filtering:** Only explicitly listed extensions are downloaded. Even a URL that passes scheme validation is rejected if its extension is not in the allow list.
- **File size:** 10 MB default cap; configurable up but never bypassed.
- **Logging:** Only `type(e).__name__` is logged for download errors (not full message, which may contain tokens in query params). For reference logging, URLs are only shown truncated or with authority portion masked if they contain query strings.
- **No auth tokens in URLs:** `RemoteResourceConfig` has no `headers` field in this scope; authenticated remote resources are a future extension.

---

## Known Limitations & Future Enhancements

### McpPromptProvider Real-Time Reload (Future Enhancement)

**Limitation:** `McpPromptProvider` does **NOT** support real-time reloading of downloaded prompt templates. Once the FastMCP instance is created and prompts are registered, the provider caches them at initialization. Newly-downloaded prompt `.md` files are NOT picked up without a server restart.

**Why:** FastMCP's prompt registration mechanism uses decorators that are applied at MCP instance creation time. Currently, there is no standard way to un-register and re-register prompts dynamically while the server is running.

**Comparison:**
- ✅ **CustomSkillsDirectoryProvider** — Re-scans on each request (reload=True enabled in Phase 3)
- ✅ **CustomAgentsDirectoryProvider** — Re-scans on each request (reload=True enabled in Phase 3)
- ❌ **McpPromptProvider** — Loads once at init; no runtime refresh

**Workaround:** Operators can restart the server to pick up new prompt templates after downloading them.

**Future Path:**
1. Investigate FastMCP's prompt lifecycle API for dynamic registration support
2. Implement a `reload=True` mode for `McpPromptProvider` once FastMCP provides the capability
3. Consider lazy-loading prompts on first request instead of at initialization

---

## Provider Reload Capability — Critical Requirement

When remote resource files are downloaded to local directories (e.g., `data/prompts/dotnet/`, `data/agents/dotnet/`, `data/skills/dotnet/`), the three directory-scanning MCP providers must immediately reload and expose those newly-available resources.

### Current Provider Implementation Status

#### ✅ CustomSkillsDirectoryProvider (`proxies/mcp/custom_skills_directory_provider.py`)
- **Current:** Already has reload capability via `reload=True` parameter in `__init__`
- **Mechanism:** `_ensure_discovered()` re-scans directories on every request when `reload=True`
- **No changes needed:** Initialize with `reload=True` (or set based on env var `REMOTE_RESOURCES_RELOAD_MODE`)

**Example:**
```python
provider = CustomSkillsDirectoryProvider(
    roots=Path("data/skills"),
    reload=True  # Re-discover skills on each request
)
```

#### ✅ CustomAgentsDirectoryProvider (`proxies/agent/custom_agents_directory_provider.py`)
- **Current:** Already has reload capability via `reload=True` parameter in `__init__`
- **Mechanism:** `_ensure_discovered()` re-scans directories on every request when `reload=True`
- **No changes needed:** Initialize with `reload=True` (or set based on env var `REMOTE_RESOURCES_RELOAD_MODE`)

**Example:**
```python
provider = CustomAgentsDirectoryProvider(
    roots=Path("data/agents"),
    reload=True  # Re-discover agents on each request
)
```

#### ⚠️ McpPromptProvider (`proxies/prompt/prompt_provider.py`) — Future Enhancement
- **Current:** Does NOT have reload capability; loads templates once at initialization and caches them
- **Limitation:** New prompt `.md` files downloaded to `data/prompts/` are NOT picked up after startup (server restart required)
- **Decision:** Skip real-time reload for now; revisit once FastMCP supports dynamic prompt re-registration
- **Workaround:** Operators can restart the server to pick up newly-downloaded prompt templates

**Note:** This is a known limitation for Phase 1–3. The three provider tiers handle reloads differently:
- **Skills & Agents:** Re-scanned on each request (reload=True)
- **Prompts:** No refresh until server restart

This will be addressed in a future phase once a performant solution is found for FastMCP prompt re-registration.

### Path Constraint: Files Go Under FASTMCP_CONFIG_DIR

All downloaded files are written to subdirectories under `FASTMCP_CONFIG_DIR` (default `data/`):

```
FASTMCP_CONFIG_DIR = data/  (set in .env)

Downloaded files land at:
  data/prompts/dotnet/  ← prompt_dir points here
  data/agents/dotnet/   ← agents_dir points here  
  data/skills/dotnet/   ← skill_dir points here
```

`McpConfig` entries reference these directories directly:
```yaml
mcp:
  - path: /dotnet
    spec_type: mcp
    skill_dir: skills/dotnet      # data/skills/dotnet/
    agents_dir: agents/dotnet     # data/agents/dotnet/
    prompt_dir: prompts/dotnet    # data/prompts/dotnet/
```

Providers scan these directories at each request (when reload=True), so newly-downloaded files are immediately available.

### Immediate Availability Guarantee

The remote resource sync task runs in the background, but files become immediately available once written to disk because:

1. **File write is atomic:** `dest_file.write_bytes(content)` is atomic on most filesystems
2. **Folder scan is on-demand:** Providers re-scan on each request when `reload=True`, not at a fixed interval
3. **No cache refresh needed:** Providers read directly from filesystem; no MCP- or Python-level caching needs to be invalidated

**Flow:**
```
1. Client makes a request to /agents/list-resources
2. McpProxyProvider._get_provider("agents_dotnet") → CustomAgentsDirectoryProvider.reset()
3. CustomAgentsDirectoryProvider._list_resources() → calls _ensure_discovered()
4. If reload=True: re-scans data/agents/dotnet/ and picks up newly-download .md files
5. New agents are exposed immediately in response
```

---

## Testing Strategy

### New test file
| Test | What to verify |
|---|---|
| `TestRemoteResourceSyncTaskValidation` | HTTPS accepted; HTTP/FTP/file rejected |
| `TestRemoteResourceSyncTaskExtension` | Allowed extensions pass; disallowed blocked |
| `TestRemoteResourceSyncTaskTTL` | Fresh file skipped; stale file re-downloaded |
| `TestRemoteResourceSyncTaskDownload` | Successful download writes file at correct path |
| `TestRemoteResourceSyncTaskErrors` | `HTTPStatusError`, `TimeoutException`, size limit → all silently skip |
| `TestRemoteResourceSyncTaskBundle` | One URL failure does not stop remaining URLs |

### Updated test files
| File | What to add |
|---|---|
| `test_config_yaml.py` | `RemoteResourceConfig` parses correctly; `ConfigYaml.remote_resources` field |
| `test_starlette_app.py` | `add_remote_resources()` stores list; lifespan partial includes it |

### Integration check
Run `python -m pytest tests/ -q` after each phase.

---

## Implemented Enhancements (Post-Phase 4)

### ✅ Retry on Failure
- **Status:** COMPLETE
- Configurable via `REMOTE_RESOURCE_RETRY_ATTEMPTS` env var (default 2)
- Implemented using `httpx.AsyncHTTPTransport(retries=...)`
- Transparent retry handling with per-URL error isolation

### 🔄 Authentication for Private URLs
- **Status:** PLACEHOLDER IMPLEMENTED (TODO for actual header injection)
- Added optional `headers: dict[str, str] | None` field to `RemoteResourceConfig`
- Wired into model, config parsing, and tests
- TODO: Implement actual request header injection in `_download_one()` method when deploying
- Future support for `Authorization: Bearer $GITHUB_TOKEN` and similar patterns

### ✅ Periodic Re-sync
- **Status:** COMPLETE
- Implemented as continuous `asyncio` loop in `RemoteResourceSyncTask.run()`
- Sleep interval derived from `REMOTE_RESOURCE_TTL_HOURS` env var
- Keeps resources fresh without server restart
- Proper cancellation on shutdown

### ✅ Download Concurrency
- **Status:** COMPLETE
- Implemented per-bundle using `asyncio.gather(..., return_exceptions=True)`
- All URLs in a bundle downloaded concurrently
- Individual URL failures isolated; one failure doesn't block others

## Open Questions & Future Scope

1. **McpPromptProvider dynamic reload** — Once FastMCP supports prompt un-registration/re-registration, add reload capability to `McpPromptProvider` matching the other providers.

2. **Authentication header injection** — Currently placeholder only. Implement actual header application in `_download_one()` when needed for private URLs (e.g., GitHub private repos with `Authorization` header).

3. **Jitter/backoff for periodic loops** — Optional enhancement: add exponential backoff and jitter to periodic resync cycles for better resilience and load distribution.

4. **Separate periodic interval configuration** — Optional: allow independent periodic-resync interval separate from TTL-based freshness check.

