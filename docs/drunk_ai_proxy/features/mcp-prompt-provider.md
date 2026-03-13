# MCP Prompt Provider

**Status**: Implemented  
**Version**: 0.2.0  

## Overview

The MCP Prompt Provider dynamically loads markdown-based prompt templates from a configurable directory, supporting parameterized string interpolation. Prompts are exposed via the MCP protocol with type-safe parameters defined in YAML frontmatter and role-based message output.

## Architecture

```
data/prompts/
  ask-topic.md       → MCP prompt "ask_topic" (user role)
  code-review.md     → MCP prompt "code_review" (user role)
  system-setup.md    → MCP prompt "system_setup" (system → user fallback)
```

### Components

| Component | File | Role |
|-----------|------|------|
| `PromptTemplate` | `proxies/prompt/prompt_template.py` | Typed template model with parameters, role, and `str.format()` rendering |
| `PromptLoader` | `proxies/prompt/prompt_loader.py` | Recursive `.md` file scanner and template parser |
| `McpPromptProvider` | `proxies/prompt/prompt_provider.py` | Dynamic FastMCP prompt registration with `inspect.Signature` |
| `McpConfig.prompt_dir` | `utils/config_yaml.py` | Configuration field for prompt directory path |

### Data Flow

```
config.yaml (prompt_dir) → McpBaseProvider
    → McpPromptProvider(config)
        → PromptLoader(prompt_dir).load_prompts()
            → scans *.md files recursively
            → parses YAML frontmatter
            → creates PromptTemplate instances
        → _create_prompt_function() per template
            → builds dynamic function with inspect.Signature
            → mcp.prompt(func) registration
    → MCP clients call prompts with typed parameters
        → template.render(**kwargs) → Message(content, role)
```

## Prompt File Format

Each prompt is a markdown file with YAML frontmatter:

```markdown
---
description: Generates a code generation request
role: user
parameters:
  language: str
  task_description: str
---
Write a {language} function that performs the following task: {task_description}
```

### Frontmatter Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `description` | `string` | (required) | Human-readable description of the prompt |
| `role` | `string` | `"user"` | Message role: `user`, `assistant`, or `system` (see [Role Support](./prompt_role_support.md)) |
| `parameters` | `dict` | `{}` | Parameter names mapped to type names (`str`, `int`, `float`, `bool`) |

### Parameter Types

| Type Name | Python Type | Example |
|-----------|-------------|---------|
| `str` | `str` | `topic: str` |
| `int` | `int` | `count: int` |
| `float` | `float` | `threshold: float` |
| `bool` | `bool` | `verbose: bool` |

### Placeholder Syntax

Use Python `str.format()` placeholders in the markdown body:

```markdown
---
description: Explain a concept at a given level
parameters:
  topic: str
  level: str
---
Can you explain the concept of '{topic}' at a {level} level?
```

## Configuration

### YAML Config

```yaml
mcp:
  - path: /mcp
    spec_type: mcp
    prompt_dir: prompts       # relative to CONFIG_DIR (data/)
```

### Validation

- `prompt_dir` path is resolved relative to `CONFIG_DIR`
- Directory must exist and be accessible
- An MCP spec type requires at least one of: `spec_file`, `mcp_servers`, `prompt_dir`, or `agents_dir`

## Implementation Details

### PromptTemplate (`prompt_template.py`, 341 lines)

- **Constructor**: Accepts `name`, `description`, `parameters`, `content`, `role`
- **Role validation**: Allowed roles are `{"user", "system", "assistant"}`. FastMCP-supported roles are `{"user", "assistant"}`. If a `system` role is specified, it falls back to `user` with a warning since FastMCP does not support system-role prompts.
- **`render(**kwargs)`**: Validates parameter types, performs `str.format()` interpolation
- **`from_markdown_file(path)`**: Class method to parse a `.md` file into a `PromptTemplate`

### PromptLoader (`prompt_loader.py`)

- Recursively scans a directory for `.md` files
- Parses each file via `PromptTemplate.from_markdown_file()`
- Returns `dict[str, PromptTemplate]` keyed by prompt name (filename stem)
- Log-and-continue pattern for malformed files

### McpPromptProvider (`prompt_provider.py`, 255 lines)

Extends `McpBaseProvider`:

- **`_create_prompt_function(template)`**: Dynamically builds a callable with:
  - Proper `__signature__` matching template parameters
  - Correct `__annotations__` for type hints
  - `__name__` and `__doc__` for FastMCP introspection
  - Returns `[Message(content=rendered, role=template.role)]`

- **`_register_prompts(mcp)`**: Iterates all templates and registers each via `mcp.prompt(func)`

- **`create_proxy()`**: Creates a `FastMCP` instance, configures auth, loads templates, registers prompts, caches result

- **`register_to_mcp(mcp)`**: Alternative entry point to register into an existing FastMCP instance. Returns count of templates loaded.

- **`get_mcp_prompts()`**: Returns a copy of the loaded templates dictionary

## Usage

### Example Prompts

**Simple prompt** (`data/prompts/explain-concept.md`):
```markdown
---
description: Explain a concept in simple terms
parameters:
  topic: str
---
Can you please explain the concept of '{topic}' in simple terms?
```

**Multi-parameter prompt** (`data/prompts/code-review.md`):
```markdown
---
description: Review code for quality and best practices
role: user
parameters:
  code: str
  language: str
---
Please review the following {language} code for quality and best practices:

{code}
```

### MCP Client Interaction

Once registered, MCP clients can:

1. **List prompts**: Discover all available prompt names and descriptions
2. **Get prompt details**: See parameter names, types, and descriptions
3. **Call prompts**: Provide parameter values, receive rendered messages with role

## Testing

```bash
# Run prompt template tests
python -m pytest tests/test_prompt_template.py -v

# Run prompt loader tests
python -m pytest tests/test_prompt_loader.py -v

# Run prompt provider tests
python -m pytest tests/test_mcp_prompt_provider.py -v
```

### Test Coverage
- Frontmatter parsing (valid, missing fields, invalid YAML)
- Parameter type validation and type mismatches
- `render()` with valid and invalid parameters
- Placeholder interpolation
- Role parsing and fallback behavior
- Directory scanning and recursive discovery
- Provider registration and prompt function creation
- Dynamic signature generation
- Error handling for malformed files

## Related

- [Prompt Role Support](./prompt_role_support.md) — Role system details
- [Agents Directory](./agents-directory-implementation.md) — Similar pattern for agent definitions
- [Anthropic Provider](./anthropic-provider.md) — LLM proxy layer
