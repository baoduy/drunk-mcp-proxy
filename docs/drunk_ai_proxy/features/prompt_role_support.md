# Prompt Role Support

**Status**: Implemented  
**Version**: 0.2.0  

## Overview

Prompt templates support a **role** field in YAML frontmatter that defines the message role (`user`, `assistant`, or `system`) for the rendered output. The role flows through to the MCP `Message` object, allowing clients to receive prompts with appropriate role context.

## Role Field

### Frontmatter Syntax

```markdown
---
description: Review code for quality
role: user
parameters:
  code: str
---
Please review the following code...
```

### Allowed Values

| Role | Supported by FastMCP | Behavior |
|------|---------------------|----------|
| `user` | Yes | Default role. Message delivered as user content. |
| `assistant` | Yes | Message delivered as assistant content. |
| `system` | Recognized but falls back | Parsed from frontmatter, but normalized to `user` with a warning since FastMCP does not support system-role messages. |

### Default Behavior

- If `role` is omitted from frontmatter, it defaults to `"user"`
- If `role` is set to an unrecognized value, it falls back to `"user"` with a warning logged
- If `role` is `"system"`, it is recognized as valid but falls back to `"user"` with a warning (FastMCP limitation)

## Implementation

### PromptTemplate (`prompt_template.py`)

```python
ALLOWED_ROLES = {"user", "system", "assistant"}
FASTMCP_ROLES = {"user", "assistant"}

class PromptTemplate:
    def __init__(self, name, description, parameters, content, role="user"):
        # Validates role against ALLOWED_ROLES
        # Falls back to "user" if not in FASTMCP_ROLES
        self.role: str = validated_role
```

**Validation logic:**
1. If `role` not in `ALLOWED_ROLES` → fall back to `"user"`, log warning
2. If `role` in `ALLOWED_ROLES` but not in `FASTMCP_ROLES` (i.e., `"system"`) → fall back to `"user"`, log warning
3. Otherwise → use as-is

### McpPromptProvider Integration

The role is passed directly into the MCP `Message` object during prompt rendering:

```python
# In McpPromptProvider._create_prompt_function()
return [Message(content=rendered_content, role=template.role)]
```

This means MCP clients receive the role as part of the prompt response, enabling them to use the message in the appropriate context.

## Examples

### User Role (default)

```markdown
---
description: Ask about a topic
parameters:
  topic: str
---
Can you explain {topic}?
```

MCP response: `Message(content="Can you explain Python?", role="user")`

### Assistant Role

```markdown
---
description: Pre-filled assistant response template
role: assistant
parameters:
  greeting: str
---
{greeting}! I'm here to help with your code review.
```

MCP response: `Message(content="Hello! I'm here to help...", role="assistant")`

### System Role (falls back to user)

```markdown
---
description: System context for code reviewer
role: system
parameters:
  focus_area: str
---
You are an expert code reviewer focused on {focus_area}.
```

MCP response: `Message(content="You are an expert...", role="user")` (with warning logged)

## Backward Compatibility

- Existing prompts without a `role` field continue to work unchanged (default: `"user"`)
- The render logic is unaffected by role — it only changes the `Message.role` output
- No breaking changes to any public API

## Testing

```bash
python -m pytest tests/test_prompt_template.py -v -k "role"
```

### Test Coverage
- Role parsing from YAML frontmatter
- Default role when field is omitted
- Valid roles (`user`, `assistant`)
- System role fallback behavior
- Invalid/unrecognized role fallback
- Role propagation through `Message` output
- Backward compatibility with role-less prompts

## Related

- [MCP Prompt Provider](./mcp-prompt-provider.md) — Full prompt provider documentation
- [Agents Directory](./agents-directory-implementation.md) — Similar pattern for agent definitions
