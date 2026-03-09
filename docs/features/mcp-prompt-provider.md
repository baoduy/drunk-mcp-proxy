# Plan: MCP Prompt Provider with Markdown Templates

**Status**: Draft  
**Last Updated**: 9 March 2026  
**Source**: Implement prompt provider loading markdown files from configurable directory with parameterized string interpolation via MCP protocol

## Overview

Add a new MCP provider that dynamically loads markdown-based prompts from a configurable directory, supporting parameterized string interpolation. Prompts are exposed via MCP protocol with type-safe parameters defined in markdown frontmatter.

## Key Decisions

- Store prompts in subdirectories under `data/` (configurable via `prompt_dir` in MCP config)
- Use YAML frontmatter for parameter type definitions (str, int, float, bool)
- Use Python `str.format()` or f-string-style `{param}` placeholders for interpolation
- Return single message strings (like the `ask_about_topic` example)
- Auto-discover all `.md` files in the configured directory
- Follow existing provider pattern from [src/proxies/mcp_proxy_provider.py](../../src/proxies/mcp_proxy_provider.py)

## Implementation Steps

### 1. Extend Config Schema

Update [src/drunk_ai_proxy/utils/config_yaml.py](../../src/drunk_ai_proxy/utils/config_yaml.py):
- Add `prompt_dir: str | None` field to `McpConfig` model (at the same level as `skill_dir`)
- Add validation: if `prompt_dir` is relative, resolve against `data/` base path
- Default to `None` (opt-in feature)

### 2. Create Prompt Model

New file [src/proxies/prompt_template.py](../../src/proxies/prompt_template.py):
- `PromptTemplate` class with:
  - `name: str` (derived from filename without `.md`)
  - `description: str` (from frontmatter `description` field)
  - `parameters: dict[str, type]` (parsed from frontmatter, e.g., `topic: str`, `count: int`)
  - `content: str` (markdown body after frontmatter)
  - `render(self, **kwargs) -> str` method that validates types and interpolates `{param}` placeholders
- Use `yaml.safe_load()` to parse frontmatter between `---` delimiters
- Map string type names to Python types: `{"str": str, "int": int, "float": float, "bool": bool}`

### 3. Create Prompt Loader

Add [src/proxies/prompt_loader.py](../../src/proxies/prompt_loader.py):
- `PromptLoader` class (follows standard logger and DI patterns from AGENTS.md)
- `__init__(self, prompt_dir: str)` – store directory path, validate it exists
- `load_prompts(self) -> dict[str, PromptTemplate]` – scan directory recursively for `.md` files
- Parse each file: extract frontmatter, validate required fields (`parameters`, `description`), create `PromptTemplate` instances
- Return dict keyed by prompt name (filename stem)
- Log errors for malformed files but continue loading valid ones

### 4. Create Prompt Provider

New file [src/proxies/mcp_prompt_provider.py](../../src/proxies/mcp_prompt_provider.py):
- `McpPromptProvider` class extending pattern from [src/proxies/mcp_base_provider.py](../../src/proxies/mcp_base_provider.py)
- `__init__(self, config: McpServerConfig)` – check if `prompt_dir` configured, initialize `PromptLoader`
- `_create_fastmcp_app(self) -> FastMCP` – create FastMCP instance
- Dynamically register prompts using `@mcp.prompt` decorator:
  - For each loaded `PromptTemplate`, create a function with signature matching parameters
  - Use `inspect.signature()` or dynamic function creation with correct type hints
  - Register function using `mcp.prompt(func)`
- Follow standard provider mounting pattern with `mount(app, prefix)`

### 5. Register Provider

Update [src/proxies/mcp_proxy_provider.py](../../src/proxies/mcp_proxy_provider.py):
- In `mount()` method, after existing MCP server mounts:
- Check each `McpServerConfig` for `prompt_dir` field
- If present, instantiate `McpPromptProvider` and mount at `/{server_name}/prompts`
- Log mount path at info level

### 6. Update Config Example

Update [data/config.yaml](../../data/config.yaml):
- Add example MCP server config with `prompt_dir` field:
  ```yaml
  mcp:
    mcp_servers:
      custom_prompts:
        type: prompts
        prompt_dir: prompts/custom
  ```
- Create example prompt file at `data/prompts/custom/ask-topic.md`:
  ```markdown
  ---
  description: Generates a user message asking for an explanation of a topic
  parameters:
    topic: str
  ---
  Can you please explain the concept of '{topic}'?
  ```

### 7. Add Unit Tests

Create [tests/test_prompt_template.py](../../tests/test_prompt_template.py):
- Test frontmatter parsing (valid, missing fields, invalid YAML)
- Test parameter type validation (correct types, type mismatches)
- Test `render()` with valid/invalid parameters
- Test placeholder interpolation

Create [tests/test_prompt_loader.py](../../tests/test_prompt_loader.py):
- Test directory scanning
- Test recursive discovery
- Test error handling for malformed files

Create [tests/test_mcp_prompt_provider.py](../../tests/test_mcp_prompt_provider.py):
- Test provider registration
- Test prompt function creation
- Test parameter binding

### 8. Add Integration Test

In [tests/](../../tests/):
- Create temporary directory with sample `.md` files
- Initialize `McpPromptProvider` with test config
- Verify FastMCP app has registered prompts
- Call prompt functions with parameters, verify rendered output

## Verification

### Unit Tests
```bash
python -m pytest tests/test_prompt_*.py -v
```

### Manual Test
1. Create `data/prompts/test/example.md` with frontmatter
2. Add MCP server config with `prompt_dir: prompts/test`
3. Start server: `python -m src.main`
4. Use MCP client to list prompts, call with parameters
5. Verify correct message returned with interpolated values

### Edge Cases
- Missing frontmatter (should log error, skip file)
- Invalid parameter types (should raise `ValueError` on render)
- Empty directory (should log warning, no prompts registered)
- Nested directories (should discover recursively)

## Technical Notes

- Use `pathlib.Path` for cross-platform path handling
- Sanitize prompt names (alphanumeric + hyphens/underscores only)
- Consider caching: load prompts once at startup, don't re-scan on each request
- For dynamic function creation, use `types.FunctionType` or `functools.partial` with proper `__name__`, `__doc__` attributes
- Follow logging pattern: `self._logger: Logger = setup_logging(__name__)`, log only exception types on errors
- Follow type hint requirements: avoid `Any`, use `dict[str, type]`, `str | None`, etc.

## Example Markdown Prompt File

```markdown
---
description: Generates a code generation request
parameters:
  language: str
  task_description: str
---
Write a {language} function that performs the following task: {task_description}
```

## Design Patterns & Standards

Following project conventions from AGENTS.md:

### Logger Pattern
```python
from logging import Logger
from tools.logging_config import setup_logging

class PromptLoader:
    def __init__(self, prompt_dir: str):
        self._logger: Logger = setup_logging(__name__)
        self._prompt_dir = prompt_dir
```

### Dependency Injection
```python
class McpPromptProvider:
    def __init__(self, config: McpServerConfig, loader: PromptLoader):
        self._logger: Logger = setup_logging(__name__)
        self._config = config
        self._loader = loader
```

### Error Handling
```python
try:
    template = self._parse_template(file_path)
except Exception as e:
    # Log only exception type, not message (security)
    self._logger.error("Failed to parse template %s: %s", file_path, type(e).__name__)
    continue
```

## Related Files

- [src/proxies/mcp_base_provider.py](../../src/proxies/mcp_base_provider.py) - Base provider pattern
- [src/proxies/mcp_proxy_provider.py](../../src/proxies/mcp_proxy_provider.py) - MCP proxy integration
- [src/tools/config_yaml.py](../../src/tools/config_yaml.py) - Configuration models
- [data/config.yaml](../../data/config.yaml) - Configuration file
- [AGENTS.md](../../AGENTS.md) - Development guidelines
