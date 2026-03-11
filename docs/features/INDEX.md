# MCP Proxy Features Documentation

This directory contains documentation for all features of the drunk-mcp-proxy server.

## Available Features

### Agent Ecosystem (New in v0.2.0)

Complete agent lifecycle management with remote synchronization.

- [**Agent Directory Implementation**](./agents-directory-implementation.md) - Agent provider architecture and directory loading
- Agent files use YAML frontmatter with `description` and `enabled` fields
- URI scheme: `agent://{name}` for content, `agent://{name}/_manifest` for metadata
- Supports flat (`root/*.md`) and namespaced (`root/namespace/*.md`) layouts

### Prompt System (New in v0.2.0)

Markdown-based prompt templates with typed parameters exposed via MCP protocol.

- [**Prompt Provider Plan**](./mcp-prompt-provider.md) - Architecture and implementation guide
- [**Role Support**](./prompt_role_support.md) - Role-based prompt configuration (`user`/`assistant`/`system`)
- Parameters: `str`, `int`, `float`, `bool` with type validation
- Dynamic MCP prompt registration with `inspect.Signature` metadata

### LLM Proxy (New in v0.2.0)

Multi-provider LLM gateway with OpenAI-compatible endpoints.

- [**Anthropic Provider**](./anthropic-provider.md) - Messages API bidirectional conversion
- [**WebSocket Responses API**](./websocket/plan-wsResponses.prompt.md) - Real-time streaming
- Model ID format: `{provider}_{model_name}` (e.g., `openai_gpt-4o`)
- Endpoints: `/chat/completions`, `/messages`, `/responses` (WS), `/embeddings`, `/models`, `/providers`

### MCP Proxy Management

Core MCP proxy orchestration and configuration.

- [**Proxy Management**](./mcp/proxy-management.md) - Managing MCP server proxies
- [**STDIO Client**](./mcp/drunk-mcp-client-stdio.md) - Local STDIO bridge to remote proxy
- [**Unified Resources Config**](./mcp/unified-resources-config.md) - Skills, prompts, agents, remote resources

### [OpenAPI Integration](./openapi/)

Load OpenAPI specifications and transform them into MCP servers.

**Quick Links:**

- [README](./openapi/README.md) - Start here for overview
- [Quick Reference](./openapi/QUICKREF_OPENAPI.md) - Quick start guide (5 min read)
- [Complete Guide](./openapi/OPENAPI_LOADER_GUIDE.md) - Full documentation (20 min read)
- [Implementation Details](./openapi/OPENAPI_IMPLEMENTATION_SUMMARY.md) - Technical deep-dive
- [Code Examples](./openapi/EXAMPLES_OPENAPI_LOADER.py) - Runnable examples
- [Naming Convention](./openapi/OPENAPI_NAMING_CONVENTION.md) - File naming rules

### Authentication

Enterprise authentication with 14+ providers.

- [**Authentication Overview**](./authentication/overview.md) - Architecture, providers, and configuration
- [**Environment Variable Resolution**](./ENV_VARIABLE_RESOLUTION.md) - `$VAR` / `${VAR}` resolution in YAML config

Supported providers: basic, auth0, aws, azure, discord, github, google, in_memory, introspection, jwt, oci, supabase.

## Directory Structure

```
docs/features/
├── INDEX.md                              (This file)
├── agents-directory-implementation.md    (Agent ecosystem)
├── anthropic-provider.md                 (Anthropic Messages API)
├── mcp-prompt-provider.md                (Prompt system)
├── prompt_role_support.md                (Prompt roles)
├── ENV_VARIABLE_RESOLUTION.md            (Env var resolution)
├── FILTERS_CONFIG.md                     (Filter configuration)
├── authentication/
│   └── overview.md                       (Auth providers)
├── mcp/
│   ├── proxy-management.md               (MCP proxy management)
│   ├── drunk-mcp-client-stdio.md         (STDIO client)
│   └── unified-resources-config.md       (Unified resource config)
├── openapi/
│   ├── README.md                         (OpenAPI overview)
│   ├── QUICKREF_OPENAPI.md               (Quick reference)
│   ├── OPENAPI_LOADER_GUIDE.md           (Complete guide)
│   ├── EXAMPLES_OPENAPI_LOADER.py        (Code examples)
│   └── ...                               (Additional guides)
└── websocket/
    └── plan-wsResponses.prompt.md        (WebSocket plan)
```

## Feature Summary Table

| Feature | Status | Key Files | Config Key |
|---------|--------|-----------|------------|
| Agent Provider | Implemented | `proxies/agent/` | `agents_dir` |
| Prompt Templates | Implemented | `proxies/prompt/` | `prompt_dir` |
| Skills Directory | Implemented | `proxies/mcp/custom_skills_directory_provider.py` | `skill_dir` |
| LLM Proxy | Implemented | `proxies/llm/` | `llm` section |
| Anthropic API | Implemented | `proxies/llm/anthropic_provider.py` | via `/messages` endpoint |
| WebSocket API | Implemented | `proxies/llm/websocket_provider.py` | `websocket: true` in LLM config |
| Remote Sync | Implemented | `app/tasks/remote_resource_sync_task.py` | `remote_resources` section |
| OpenAPI | Implemented | `proxies/mcp/openapi_provider.py` | `spec_type: openapi` |
| Authentication | Implemented | `auth/` | `auth` section |
| STDIO Client | Implemented | `drunk_ai_client/` | `API_URL`, `API_KEY` env vars |

## Adding New Features

When adding a new feature to the MCP proxy server:

1. **Create documentation**: Add a markdown file in `docs/features/` or a subdirectory
2. **Update this index**: Add a link and description in this INDEX.md
3. **Update docs/INDEX.md**: Add to the main documentation index
4. **Update CHANGELOG.md**: Document in the appropriate version section

### Feature Documentation Template

```markdown
# {Feature Name}

## Overview
Brief description of the feature.

## Architecture
How the feature fits into the system.

## Configuration
YAML config and environment variables.

## Usage
Code examples and API usage.

## Testing
How to run tests for this feature.
```

## Navigation

### By Feature Type

**Data Providers** (load and serve content as MCP resources)
- Agent Provider - `agent://` resources
- Skills Provider - `skill://` resources
- Prompt Provider - MCP prompts with parameters

**API Gateways** (proxy and convert API requests)
- LLM Proxy - OpenAI-compatible endpoints at `/api/v1`
- Anthropic Provider - Messages API conversion
- WebSocket Provider - Real-time streaming

**Infrastructure** (background tasks and configuration)
- Remote Resource Sync - Periodic HTTPS downloads
- Authentication - 14+ enterprise auth providers
- Config System - Unified YAML with env var resolution

### By Reading Time

- **5 minutes**: Feature overview sections above
- **10 minutes**: Individual feature README files
- **20+ minutes**: Complete guides (OpenAPI, Auth)
- **30+ minutes**: Implementation details and architecture docs
