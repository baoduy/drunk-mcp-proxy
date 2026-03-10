# Feature Plan: Remote MCP Client with Skill Auto-Install (STDIO)

**Status**: Draft  
**Last Updated**: 9 March 2026

## Goal

Create a local MCP client executable at `src/drunk_ai_client/client.py` that:

1. Connects to a remote Drunk AI Proxy MCP endpoint (example: `http://0.0.0.0:9123/deepsea/mcp`).
2. Detects available skills from the remote server and installs them into a user-provided folder automatically.
3. Runs in `stdio` mode for compatibility with desktop MCP hosts.

## Scope

- In scope:
  - A stdio MCP server process that internally acts as an MCP client to the remote endpoint.
  - Skill discovery + local install/sync workflow.
  - Environment-variable based configuration with optional CLI overrides.
  - Unit tests for discovery, sync behavior, and failure handling.
- Out of scope (phase 1):
  - Bi-directional skill edits back to remote.
  - Full marketplace/package manager semantics for skills.
  - Long-running file watch daemon.

## Existing Codebase Facts

- `client/main.py` currently exists but is empty.
- Server-side MCP providers already support skills via `SkillsDirectoryProvider` in `src/drunk_ai_proxy/proxies/mcp/base_provider.py`.
- MCP config model already includes `skill_dir` in `src/drunk_ai_proxy/utils/config_yaml.py`.
- Proxy docs already describe `skill_dir` behavior and directory layout in `docs/features/mcp/proxy-management.md`.

## Architecture Decision

Implement a local bridge process (stdio-facing) that proxies to remote MCP and optionally mirrors skill resources to a local folder.

- Front side: `stdio` transport (what desktop clients connect to).
- Back side: remote HTTP MCP endpoint (`/mcp`).
- Skill sync: pull metadata/content from remote resources and write local skill files to configured destination.

This preserves requirement (3) while still fulfilling requirement (1).

## Implementation Plan

### 1. Add client module skeleton at requested path

Target file: `src/drunk_ai_client/client.py`

- Add a class-first design:
  - `RemoteMcpClientConfig`
  - `RemoteSkillSyncService`
  - `StdioMcpBridgeServer`
  - `CliEntrypoint`
- Keep orchestration in class methods (project convention).
- Add Google-style docstrings and full type hints.

Note:
- Directory name `drunk_ai_client` is importable as a standard Python package.
- Execution can use module paths or a console script (`python -m drunk_ai_client.main`).

### 2. Define runtime configuration contract

Support environment variables first, with optional CLI override:

- `API_URL` (required): remote MCP endpoint URL.
- `API_KEY` (optional): bearer token or API key for remote auth.
- `SKILL_DIR` (required for auto-install mode): local destination folder for installed skills.
- `SYNC_ON_START` (optional, default `true`): whether to run skill sync during startup.
- `SYNC_INTERVAL_SECONDS` (optional, default `0`): `0` means startup-only sync.

Optional CLI flags (override env vars when provided):

- `--remote-url`
- `--api-key`
- `--skills-dir`
- `--sync-on-start`
- `--sync-interval-seconds`

Validation rules:

- Effective `remote_url` must be absolute HTTP/HTTPS.
- Effective `skills_dir` must be writable (create if missing).
- `sync_on_start` defaults to enabled when unset.
- Reject invalid boolean/integer env values early with clear startup error.

### 3. Implement remote MCP connectivity layer

- Build a small adapter for JSON-RPC MCP calls over HTTP to remote endpoint.
- Minimum supported operations:
  - initialize/handshake
  - list tools/resources/prompts
  - fetch resource content for skill artifacts
- Implement retries with bounded backoff and request timeout.
- Error sanitation: log exception type only, avoid leaking tokens.

### 4. Implement skill discovery strategy

Use this sequence:

1. Query remote resources list.
2. Filter resources that represent skills (naming/path/content-type heuristics).
3. Group by skill root folder name.
4. Pull each skill file content.

Heuristics should be configurable and conservative:

- Prefer explicit prefixes if available (for example `skills/` or known provider namespaces).
- Ignore binary payloads in phase 1.
- Require at least one markdown file (`SKILL.md` or equivalent) per skill root.

### 5. Implement local skill installer

- Create deterministic layout under provided folder:
  - `<skills_dir>/<skill_name>/...`
- Write files atomically (temp + rename).
- Maintain sync state manifest:
  - `.drunk-mcp-client-sync.json`
  - remote resource id/hash -> local file
  - last sync timestamp
- Conflict policy:
  - default overwrite files previously managed by sync
  - preserve unknown user files
- Cleanup policy:
  - optional delete stale managed files removed remotely

### 6. Implement stdio MCP bridge behavior

- Start a local FastMCP server in `stdio` mode.
- Expose bridge tools/resources that proxy to remote endpoint.
- Ensure the local process can be registered in MCP host configs as a stdio command.
- During startup:
  - initialize remote connection
  - run skill sync on start by default
  - continue serving stdio MCP requests

### 7. Add observability and safe logging

- Structured logs for:
  - startup config (non-sensitive)
  - sync summary (skills/files written)
  - remote call failures
- Follow repository security convention:
  - log exception type only (`type(e).__name__`)
  - truncate tokens if ever logged for diagnostics

### 8. Testing plan

Add tests (new file suggestions):

- `tests/test_drunk_mcp_client_config.py`
- `tests/test_drunk_mcp_client_skill_sync.py`
- `tests/test_drunk_mcp_client_stdio_bridge.py`

Test cases:

- Config validation (valid URL, invalid URL, missing dir, auth options).
- Skill discovery from mocked remote resources.
- File install idempotency and atomic write behavior.
- Manifest updates and stale cleanup behavior.
- Startup behavior when remote endpoint unavailable.
- StdIO bridge starts and responds using mocked remote backend.

### 9. Documentation and examples

- Add usage doc under `docs/features/mcp/` for:
 - Add usage doc under `docs/features/mcp/` for:
  - command-line invocation
  - environment variable invocation (`API_URL`, `API_KEY`, `SKILL_DIR`)
  - sample host config for stdio
  - remote auth examples
  - troubleshooting (network/auth/path issues)
- Include minimal quick-start examples:
  - Env-based (recommended):
    - `API_URL=http://0.0.0.0:9123/deepsea/mcp SKILL_DIR=./data/skills python src/drunk_ai_client/client.py`
  - With auth:
    - `API_URL=http://0.0.0.0:9123/deepsea/mcp API_KEY=your_token SKILL_DIR=./data/skills python src/drunk_ai_client/client.py`

## Risks and Mitigations

- Remote server may expose skills in non-standard resource layout.
  - Mitigation: configurable detection patterns + explicit allowlist prefixes.
- Large skill payloads may slow startup.
  - Mitigation: one-time sync + optional interval; add max file size guard.
- Hyphenated source path complicates imports and packaging.
  - Mitigation: keep execution path-based first; add packaging alias in phase 2.

## Rollout Plan

1. Deliver phase 1 with one-time startup sync and stdio bridge.
2. Validate against your target endpoint `http://0.0.0.0:9123/deepsea/mcp`.
3. Add periodic sync mode only after baseline stability.
4. Add optional package-friendly module path once behavior is proven.

## Acceptance Criteria

- Running `python src/drunk_ai_client/client.py ...` starts successfully in stdio mode.
- Running with env vars (`API_URL`, `SKILL_DIR`) starts successfully in stdio mode.
- Client can reach remote MCP endpoint and complete handshake/listing.
- If remote skills exist, they are installed to provided folder automatically.
- Default behavior performs skill sync on startup when `SYNC_ON_START` is unset.
- Re-running sync is idempotent and does not duplicate files.
- Failures are surfaced clearly without leaking sensitive data.

## Sources Consulted

- https://gofastmcp.com/python-sdk/fastmcp-server-providers-skills-__init__
- `src/drunk_ai_proxy/proxies/mcp/base_provider.py`
- `src/drunk_ai_proxy/proxies/mcp/proxy_provider.py`
- `src/drunk_ai_proxy/proxies/mcp/mcp_proxy_builder.py`
- `src/drunk_ai_proxy/utils/config_yaml.py`
- `docs/features/mcp/proxy-management.md`
