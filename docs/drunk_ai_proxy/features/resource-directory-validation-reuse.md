# Resource Directory Validation Reuse Plan

## Goal

Add one reusable method in `resource_path_utils.py` to validate/configure resource directories and reuse it for all resource types (skills, agents, prompts), eliminating repeated checks for:

- path resolution from config-relative paths
- existence and directory type
- markdown file presence (`*.md`)
- skip logging with consistent messages

## Current-State Findings

Duplicated validation logic exists in multiple places:

1. `McpBaseProvider._add_agent_proxy(...)`
   - resolves `CONFIG_DIR/<dir>`
   - checks `exists()` and `is_dir()`
   - checks markdown count with `rglob("*.md")`

2. `McpProxyProvider._add_prompt_proxy(...)`
   - resolves absolute/relative prompt path
   - checks `exists()` and `is_dir()`
   - checks markdown count with `rglob("*.md")`

3. `McpBaseProvider._add_skill_proxy(...)` currently only checks `exists()` and does not align with markdown validation behavior used for agents/prompts.

## Proposed Utility Method

File: `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/resource_path_utils.py`

Add a new reusable function (name proposal):

- `collect_valid_resource_dirs(...) -> list[Path]`

### Suggested signature

```python
def collect_valid_resource_dirs(
    *,
    configured_dirs: list[str],
    config_dir: str,
    mcp_path: str,
    resource_label: str,
    require_markdown: bool = True,
    logger: Logger,
) -> list[Path]:
```

### Responsibilities

1. Normalize each configured directory to absolute path:
   - if absolute: use as-is
   - if relative: resolve under `config_dir`
2. Validate path exists and is a directory.
3. Optionally validate at least one markdown file if `require_markdown=True`.
4. Emit existing-style warnings:
   - `Skipping <resource_label> directory for path '%s' because it does not exist: %s`
   - `Skipping <resource_label> directory for path '%s' because it has no markdown files: %s`
5. Return only valid absolute `Path` values.

## Refactor Plan by Call Site

### 1) `McpBaseProvider._add_agent_proxy`

Replace the loop and manual checks with:

- `agents_dir_paths = collect_valid_resource_dirs(...)`
- Keep provider construction/mount logic unchanged.

### 2) `McpProxyProvider._add_prompt_proxy`

Use `collect_valid_resource_dirs(...)` for validation and path checks.

Compatibility note:
- current prompt provider constructor receives original configured strings (`prompt_dirs=valid_prompt_dirs`) and has tests asserting that behavior.
- chosen solution: keep the constructor contract unchanged by returning rich entries from the utility (original + resolved), then pass filtered `original` values to `McpPromptProvider`.

### 3) `McpBaseProvider._add_skill_proxy`

Adopt the same utility to align behavior with agents/prompts.

Decision:
- set `require_markdown=False` for skills in phase 1 (backward-compatible behavior).
- set `require_markdown=True` for agents and prompts (no behavior change).
- add an opt-in switch (env/config) for skill markdown enforcement in phase 2, then flip default after deprecation window.

## Type/Style Conformance

- Keep Python 3.10+ typing (`list[str]`, `str | None` style).
- Use project logger pattern; no sensitive message logging changes needed.
- Keep function-level docstring in Google style.

## Test Impact and Plan

### Update/add tests in:

1. `tests/test_resource_path_utils.py` (new or extend existing)
   - relative and absolute path handling
   - missing path skip
   - non-directory skip
   - markdown-empty skip
   - successful valid path collection

2. `tests/test_mcp_proxy_provider.py`
   - prompt path validation remains stable
   - confirm provider is not created when no valid dirs

3. `tests/test_mcp_proxy_provider_extended.py`
   - skill/agent path behavior still works after extraction

4. any tests patching old per-method path checks should be adjusted to patch utility behavior where needed.

### Verification commands

```bash
/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest tests/test_resource_path_utils.py tests/test_mcp_proxy_provider.py tests/test_mcp_proxy_provider_extended.py -q
```

If no dedicated utility test file exists yet, use:

```bash
/Users/steven/_CODE/drunk-mcp-proxy/.venv/bin/python -m pytest tests/test_mcp_proxy_provider.py tests/test_mcp_proxy_provider_extended.py tests/test_resource_path_utils.py -q
```

## Risks and Mitigations

1. Behavior drift for prompt dirs
   - Risk: switching to absolute paths may break tests expecting original relative strings.
   - Solution:
     - Keep utility output as a structure containing both values:
       - `original_dir` (exact config string)
       - `resolved_path` (absolute `Path` used for filesystem validation)
     - For prompt registration, pass only filtered `original_dir` values into `McpPromptProvider`.
     - Add a regression test asserting `McpPromptProvider(..., prompt_dirs=["prompts/custom"])` still receives relative values.

2. Skill provider strictness increase
   - Risk: enforcing markdown presence may change existing deployments.
   - Solution:
     - Keep skills permissive initially (`require_markdown=False`) to match current behavior.
     - Keep agents/prompts strict (`require_markdown=True`) because this is already expected.
     - Add a migration path:
       1. Phase 1: permissive skills + warning when skill dir has zero markdown files.
       2. Phase 2: configurable strict mode for skills.
       3. Phase 3: strict-by-default for skills (optional, only after release note + changelog).
     - Add tests for both skill modes to prevent accidental default flips.

3. Logging message regressions
   - Risk: changed warning text can break assertion-based tests.
   - Solution:
     - Centralize warning templates as constants in the utility and reuse exact legacy text.
     - Keep placeholders and wording identical:
       - `Skipping <resource> directory for path '%s' because it does not exist: %s`
       - `Skipping <resource> directory for path '%s' because it has no markdown files: %s`
     - Add focused tests asserting the warning message text (or stable substrings) for each resource label.

## Final Implementation Decisions

1. Utility return shape
   - Return `list[ValidatedResourceDir]` with fields:
     - `original_dir: str`
     - `resolved_path: Path`

2. Call-site usage
   - Skills/agents providers use `resolved_path` for provider roots.
   - Prompt provider uses filtered `original_dir` list to preserve API contract.

3. Strictness defaults
   - Skills: `require_markdown=False` (phase 1 compatibility).
   - Agents: `require_markdown=True`.
   - Prompts: `require_markdown=True`.

4. Logging stability
   - Preserve existing warning strings exactly and verify in tests.

## Rollout Notes

1. Land utility + call-site refactor in one PR to avoid mixed behavior.
2. Add changelog entry under `[Unreleased]` → `### Changed`.
3. If skill behavior changes, document it explicitly in migration notes.

## Sources Consulted

- Repository code:
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/resource_path_utils.py`
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/base_provider.py`
  - `src/drunk_ai_proxy/drunk_ai_proxy/proxies/mcp/proxy_provider.py`
- Existing project conventions in `AGENTS.md` and `.github/copilot-instructions.md`.
