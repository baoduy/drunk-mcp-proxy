# Agents Directory MCP Provider

**Status**: Implemented  
**Version**: 0.2.0  

## Overview

The Agents Directory provider loads markdown files from a configurable directory and exposes them as MCP resources with the `agent://` URI prefix. This enables MCP clients to discover and retrieve agent definitions (system prompts, personas, behavioral instructions) through the standard MCP resource protocol.

## Architecture

```
data/agents/
  reasoning.md              → agent://reasoning
  core/
    planning.md             → agent://core/planning
    analysis.md             → agent://core/analysis
  tools/
    code-refactor.md        → agent://tools/code_refactor
```

### Components

| Component | File | Role |
|-----------|------|------|
| `AgentProvider` | `proxies/agent/agent_provider.py` | Exposes a single agent `.md` file as an MCP resource |
| `CustomAgentsDirectoryProvider` | `proxies/agent/custom_agents_directory_provider.py` | Recursively scans directories, creates `AgentProvider` instances |
| `McpConfig.agents_dir` | `utils/config_yaml.py` | Configuration field for agent directory path |
| `McpBaseProvider._create_agent_proxy` | `proxies/mcp/base_provider.py` | Integration point that mounts the agent provider |

### Data Flow

```
config.yaml (agents_dir) → McpBaseProvider._create_agent_proxy()
    → CustomAgentsDirectoryProvider(roots=[resolved_path])
        → scans *.md files recursively
        → parses YAML frontmatter (description, enabled)
        → creates AgentProvider per file
            → AgentResource (content + manifest)
    → mounted into FastMCP instance
    → MCP clients query agent:// resources
```

## Agent File Format

Each agent is a markdown file with optional YAML frontmatter:

```markdown
---
description: SDLC lifecycle and agent responsibilities
enabled: true
---
# Agent Description and Instructions

Full agent definition with system instructions, guidelines, and behavioral constraints.
Supports markdown formatting, code blocks, and detailed specifications.

## How to Use
- Use this agent when you need to...
- Key responsibilities: ...
```

### Frontmatter Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `description` | `string` | (required) | Brief description of the agent's purpose |
| `enabled` | `boolean` | `true` | Whether the agent is active and discoverable |

The markdown content after frontmatter is served as-is without any transformation.

## Configuration

### YAML Config

```yaml
mcp:
  - path: /mcp
    spec_type: mcp
    agents_dir: agents         # relative to CONFIG_DIR (data/)
```

### Validation Rules

- `agents_dir` path is resolved relative to `CONFIG_DIR`
- Directory must exist and be accessible
- Directory must contain at least one `.md` file
- An MCP spec type requires at least one of: `spec_file`, `mcp_servers`, `prompt_dir`, or `agents_dir`

## Directory Structure Support

Both flat and namespaced layouts are supported:

```
data/agents/
  reasoning.md              # Flat: agent://reasoning
  code-analyzer.md          # Flat: agent://code_analyzer

  core/
    planning.md             # Namespaced: agent://core/planning
    reasoning-engine.md     # Namespaced: agent://core/reasoning_engine

  tools/
    code-refactor.md        # Namespaced: agent://tools/code_refactor
    test-generator.md       # Namespaced: agent://tools/test_generator
```

### Name Normalization

- Agent names are derived from file paths relative to the root directory
- Hyphens and spaces are replaced with underscores
- Names are lowercased
- Subdirectory separators become `/` in the URI

## Features

### Agent Discovery
- Recursive directory scan via `glob()` patterns
- Lazy loading on first access (`_ensure_discovered()`)
- Optional reload mode for re-discovery on each request

### Resource Exposure
Each agent exposes two resources:
1. **Markdown content** — the raw agent definition
2. **JSON manifest** (`_manifest`) — metadata including SHA256 hash for cache validation

### Error Handling
- Log-and-continue pattern for malformed files
- Duplicate agent name detection (warns and skips duplicates)
- Files missing `description` are skipped with a warning
- Disabled agents (`enabled: false`) are excluded from discovery
- Graceful handling of missing or empty directories

## Implementation Details

### AgentProvider (`agent_provider.py`, 410 lines)

Extends FastMCP `Provider`. Manages a single agent file:

- `AgentResource` — Pydantic model storing metadata, file path, enabled status
- `AgentInfo` / `AgentFileInfo` — dataclasses for structured agent metadata
- SHA256 file hashing for cache invalidation
- `_list_resources()` / `_get_resource()` / `_read_resource()` — standard MCP resource interface

### CustomAgentsDirectoryProvider (`custom_agents_directory_provider.py`, 281 lines)

Extends FastMCP `AggregateProvider`. Manages the full directory:

- `_discover_agents()` — scans and loads all agents
- `_parse_frontmatter()` — extracts YAML fields from markdown
- `_sanitize_agent_name()` — normalizes file paths to agent names
- `_iter_agent_files()` — yields all `.md` files in directory tree
- Creates one `AgentProvider` instance per valid agent file

## Testing

```bash
# Run agent provider tests
python -m pytest tests/test_agent_provider.py -v

# Run directory provider tests
python -m pytest tests/test_custom_agents_directory_provider.py -v
```

### Test Coverage
- Agent file loading and frontmatter parsing
- Flat and namespaced directory structures
- Name normalization and sanitization
- Enabled/disabled agent filtering
- Duplicate name detection
- Missing directory handling
- Empty directory handling
- Malformed frontmatter handling

## Related

- [MCP Prompt Provider](./mcp-prompt-provider.md) — Similar pattern for prompt templates
- [Anthropic Provider](./anthropic-provider.md) — LLM proxy layer
- [Prompt Role Support](./prompt_role_support.md) — Role system in prompt templates
