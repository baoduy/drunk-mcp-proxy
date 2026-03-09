# Feature Plan: Role Support in Prompt Templates

**Feature**: Add role definitions to prompt files to support system-level context/persona configuration.

**Status**: Planning  
**Created**: 2026-03-09  
**Type**: Enhancement

---

## Overview

Currently, prompt templates in the Drunk MCP Proxy support:
- **Description**: Human-readable explanation of what the prompt does
- **Parameters**: Input variables with type definitions
- **Content**: Template body with parameter placeholders

This feature adds support for **roles** — a top-level persona or system context that defines how the LLM should behave when executing the prompt. Roles can serve as:
- System instructions for OpenAI, Claude, or other LLMs
- Execution context that can be passed to MCP servers
- Metadata for logging and monitoring which context is being used

### Example Use Case

Instead of having role information buried in the prompt content:
```markdown
---
description: Code review request
parameters:
  code: str
---
You are an expert code reviewer. Please review this code...
```

Authors can declare the role explicitly:
```markdown
---
description: Code review request
role: code_reviewer
parameters:
  code: str
---
Please review this code for quality and best practices...
```

---

## Requirements

### Functional Requirements

1. **Role Field in Frontmatter**
   - Add optional `role` field to YAML frontmatter
   - Role should be a string value (e.g., "code_reviewer", "teacher", "system_architect")
   - Role field is **optional** (backward compatible with existing prompts)

2. **PromptTemplate Enhancement**
   - Store role as instance attribute: `self.role: str | None`
   - Expose role via property for read-only access
   - Include role in template's `__repr__()` for debugging

3. **Parsing Logic**
   - Extract role from frontmatter during template loading
   - Handle missing role gracefully (default to `None`)
   - Validate role value (must be non-empty string if provided)

4. **MCP Prompt Registration**
   - Pass role information to MCP prompt metadata
   - Make role available to MCP clients that request prompt details
   - Each prompt's MCP descriptor should include role in metadata

5. **Backward Compatibility**
   - Existing prompts without `role` field continue to work unchanged
   - No breaking changes to the public API
   - Render logic remains identical (role does not affect template interpolation)

### Non-Functional Requirements

- **Type Safety**: Maintain strict type hints (no `Any` types)
- **Logging**: Follow project logging conventions
- **Testing**: Comprehensive coverage for new code
- **Performance**: Minimal impact on template loading
- **Documentation**: Update format documentation with examples

---

## Architecture & Design

### 1. PromptTemplate Changes

**File**: `src/drunk_ai_proxy/proxies/prompt/prompt_template.py`

**Changes**:
```python
class PromptTemplate:
    """Represents a prompt template loaded from a markdown file.
    
    A prompt template consists of:
    - YAML frontmatter with optional role, required description, and parameters
    - Markdown content body with {param} placeholders
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, str],
        content: str,
        role: str | None = None  # NEW
    ):
        """Initialize a PromptTemplate.
        
        Args:
            name: Template name (derived from filename).
            description: Human-readable description of the prompt.
            parameters: Parameter names to type names mapping.
            content: Template content with {param} placeholders.
            role: Optional role/persona for the prompt (e.g., "code_reviewer").
        
        Raises:
            ValueError: If role is provided but empty string.
        """
        self._logger: Logger = setup_logging(__name__)
        self.name = name
        self.description = description
        self.content = content
        
        # NEW: Validate and store role
        if role is not None and not isinstance(role, str):
            raise ValueError("role must be a string or None")
        if role is not None and not role.strip():
            raise ValueError("role cannot be an empty string")
        
        self.role: str | None = role.strip() if role else None
        
        # Parse parameter types (existing code)
        self.parameters: dict[str, type] = {}
        for param_name, type_name in parameters.items():
            # ... existing parameter parsing ...
```

**Methods to update**:
- `__init__()`: Add `role` parameter validation
- `from_markdown_file()` classmethod: Extract role from frontmatter
- `__repr__()`: Include role in debug representation

**YAML Frontmatter Format**:
```yaml
---
description: Brief description of the prompt
role: optional_role_name
parameters:
  param1: str
  param2: int
---
Template content...
```

### 2. PromptLoader Changes

**File**: `src/drunk_ai_proxy/proxies/prompt/prompt_loader.py`

**Changes**:
- No public API changes needed
- The frontmatter parsing is handled by `PromptTemplate.from_markdown_file()`, so no changes required here
- Verify tests still pass with new role field

### 3. McpPromptProvider Changes

**File**: `src/drunk_ai_proxy/proxies/prompt/prompt_provider.py`

**Changes**:
- Update `_create_prompt_function()` to include role in function signature or metadata
- Role data should be accessible to MCP clients when they query prompt metadata
- May need to enhance the FastMCP prompt registration to include role metadata

**Example**:
```python
def _create_prompt_function(
    self,
    template: PromptTemplate
) -> Any:
    """Create a prompt function for a template."""
    # Include role in metadata if FastMCP supports it
    # Role can be logged or included in response metadata
```

---

## Implementation Steps

### Phase 1: Core Implementation (3-4 hours)

1. **Modify PromptTemplate class** (1 hour)
   - Add `role: str | None` parameter to `__init__()`
   - Add role validation (non-empty if provided)
   - Update `from_markdown_file()` to extract role from frontmatter
   - Update `__repr__()` to include role
   - Update docstrings with role examples

2. **Update unit tests for PromptTemplate** (1.5 hours)
   - Add tests for role parsing from frontmatter
   - Test optional role (missing from frontmatter)
   - Test invalid role (empty string, non-string type)
   - Test `__repr__()` includes role
   - Test backward compatibility (prompts without role)
   - Test role in YAML frontmatter parsing

3. **Update PromptLoader tests** (0.5 hours)
   - Verify tests pass with new role field
   - Add test fixtures with role field
   - No code changes needed, just test updates

4. **Review PromptTemplate parsing logic** (0.5 hours)
   - Verify YAML frontmatter parsing handles role correctly
   - Ensure error messages are clear for malformed role fields

### Phase 2: Integration & Provider Updates (2-3 hours)

5. **Update McpPromptProvider** (1-1.5 hours)
   - Decide how role should be exposed via MCP
   - Update prompt registration to include role metadata
   - Log role information when prompts are loaded

6. **Add integration tests** (0.5 hours)
   - Test loading prompts with roles via PromptLoader
   - Test MCP registration includes role metadata
   - Test end-to-end: file → loader → provider → MCP

7. **Documentation** (0.5 hours)
   - Update prompt format documentation
   - Add role examples to existing prompts
   - Document role use cases in QUICK_START or guides

### Phase 3: Testing & Validation (1-2 hours)

8. **Run full test suite** (0.5 hours)
   - Ensure backward compatibility
   - Fix any regressions
   - Verify type checking passes

9. **Manual testing** (0.5-1.5 hours)
   - Load prompts with role field
   - Verify role is accessible via MCP
   - Test with various role values and edge cases

---

## Test Coverage Plan

### Unit Tests

**PromptTemplate Tests** (`test_prompt_template.py`):
- `test_init_with_role_stores_role()` - Store provided role
- `test_init_without_role_sets_none()` - Default to None
- `test_init_with_empty_role_raises_error()` - Reject empty strings
- `test_init_with_non_string_role_raises_error()` - Type validation
- `test_from_markdown_file_with_role()` - Parse from frontmatter
- `test_from_markdown_file_without_role()` - Role is optional
- `test_repr_includes_role()` - Representation includes role
- `test_backward_compatibility_without_role()` - Old format still works

### Integration Tests

**PromptLoader Tests** (`test_prompt_loader.py`):
- `test_load_prompts_with_roles()` - Load multiple prompts with roles
- `test_load_mixed_prompts_with_and_without_roles()` - Backward compatibility

**Provider Tests** (`test_prompt_provider.py` or integration tests):
- `test_prompt_provider_exposes_role_metadata()` - Role accessible via MCP
- `test_role_logged_on_template_load()` - Logging verification

---

## YAML Frontmatter Examples

**Example 1: Prompt with role**
```yaml
---
description: Review code for quality and best practices
role: code_reviewer
parameters:
  code: str
  language: str
---
Please review the following {language} code...
```

**Example 2: Prompt without role (backward compatible)**
```yaml
---
description: Explain a concept
parameters:
  topic: str
---
Can you explain {topic}?
```

**Example 3: Complex role with underscores/hyphens**
```yaml
---
description: Generate comprehensive tests for code
role: test_engineer
parameters:
  code: str
  language: str
---
Write comprehensive tests for this {language} code...
```

---

## Error Handling

### Scenarios to Handle

1. **Missing description** (existing error - unchanged)
   ```
   ValueError: Prompt file must have a 'description' field in frontmatter
   ```

2. **Invalid role (empty string)**
   ```
   ValueError: role cannot be an empty string
   ```

3. **Invalid role (non-string)**
   ```
   ValueError: role must be a string or None
   ```

4. **Missing role (allowed)**
   - Template loads successfully with `role = None`
   - No error raised

---

## Backward Compatibility

✅ **Breaking Changes**: None

- Existing prompts without `role` field continue to work unchanged
- Role defaults to `None` if not provided
- Render logic is unaffected by role presence
- MCP API remains backward compatible

**Migration Path**: Gradual adoption
- Authors can add role to existing prompts at their own pace
- Existing pipelines/tools require no changes
- New prompts should include role for clarity

---

## File Changes Summary

| File | Change Type | Impact |
|------|-------------|--------|
| `src/drunk_ai_proxy/proxies/prompt/prompt_template.py` | Enhance | Add role parameter and parsing |
| `tests/test_prompt_template.py` | Enhance | Add role-related tests |
| `tests/test_prompt_loader.py` | Enhance | Update fixtures with role |
| `tests/test_prompt_provider.py` | Enhance | Add role metadata tests (if needed) |
| Existing `.md` prompt files | Optional | Can optionally add role field |
| `docs/` guides | Enhancement | Document new role field |

---

## Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Breaking change in PromptTemplate API | High | Make role parameter optional with default None |
| Tests fail with new field | Medium | Add comprehensive test fixtures for role |
| Role field causes parsing errors | Medium | Validate role in __init__() with clear errors |
| MCP integration complexity | Medium | Start simple (just expose role in metadata), add complexity later |
| Role naming inconsistency | Low | Document role naming conventions (snake_case recommended) |

---

## Future Enhancements

After initial implementation, consider:

1. **Role Registry**: Maintain a registry of valid roles (optional)
2. **Role Inheritance**: Allow roles to extend other roles
3. **Role-Based Validation**: Validate role against known roles
4. **Role in Rendering**: Use role to modify template behavior
5. **Role Aliasing**: Map multiple role names to a single context

---

## Rollout Plan

### Stage 1: Implementation (Sprint 1)
- Implement core changes (PromptTemplate, tests)
- Internal review and testing

### Stage 2: Integration (Sprint 2)
- Update McpPromptProvider
- Add integration tests
- Update documentation

### Stage 3: Validation (Sprint 3)
- Full test suite passes
- Manual testing complete
- Deploy to development environment

### Stage 4: Adoption (Ongoing)
- Update existing prompts gradually
- Create examples for new prompts
- Gather feedback from users

---

## Success Criteria

✅ **Acceptance Tests**:
1. PromptTemplate accepts and stores role from YAML frontmatter
2. Role field is optional (backward compatible with existing prompts)
3. Role is validated (non-empty string if provided)
4. Type checking passes (no `Any` types, strict hints)
5. All existing tests pass without modification
6. New tests cover role functionality (>80% coverage)
7. Role metadata is accessible via MCP prompt descriptors
8. Invalid role values produce clear error messages
9. Logging includes role information when relevant
10. Documentation updated with examples

---

## Implementation Checklist

- [ ] Create/modify PromptTemplate `__init__()` with role parameter
- [ ] Update `from_markdown_file()` to parse role from frontmatter
- [ ] Update `__repr__()` to include role
- [ ] Add role validation (non-empty, string type)
- [ ] Update PromptTemplate docstrings with role examples
- [ ] Write unit tests for role parsing
- [ ] Write unit tests for role validation
- [ ] Write backward compatibility tests
- [ ] Update PromptLoader tests (if needed)
- [ ] Update McpPromptProvider to expose role metadata
- [ ] Add integration tests
- [ ] Run full test suite
- [ ] Update documentation/guides
- [ ] Add example prompts with role field
- [ ] Code review
- [ ] Deploy

---

## References & Notes

**Current Implementation Files**:
- [PromptTemplate](src/drunk_ai_proxy/proxies/prompt/prompt_template.py)
- [PromptLoader](src/drunk_ai_proxy/proxies/prompt/prompt_loader.py)
- [McpPromptProvider](src/drunk_ai_proxy/proxies/prompt/prompt_provider.py)
- [Tests](tests/test_prompt_*.py)

**Example Prompts**:
- `data/prompts/custom/code-review.md`
- `data/prompts/custom/explain-concept.md`
- `data/prompts/custom/generate-code.md`

---

## Approval & Sign-off

**Feature Owner**: [Steven]  
**Reviewers**: [TBD]  
**Approval Date**: [TBD]
