# Implementation Plan: Agents Directory MCP Provider

## Overview
Implement an agents directory loader similar to the existing prompts directory loader. This feature will allow loading markdown files from `data/agents/` (or configured directory) and exposing them as MCP resources with the `agent://` URI prefix.

## Current Context
The codebase already has an established pattern for resource loading via the **PromptLoader** and **McpPromptProvider**. Agents will follow a similar structure but simpler:
- Scans a directory recursively for `*.md` files
- Extracts basic metadata from YAML frontmatter (`description`, `enabled`)
- Serves entire markdown content as static resources via MCP
- Supports subdirectory namespacing (e.g., `category/agent.md` → `category_agent`)
- Handles missing directories and malformed files gracefully

## Architecture

### 1. Directory Structure
```
data/
  agents/
    core/
      reasoning.md
      planning.md
    tools/
      code-analysis.md
      testing.md
    custom/
      specialized-agent.md
```

### 2. File Format (Markdown with YAML Frontmatter)
Each agent markdown file is a static resource with minimal frontmatter:

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
- Best practices: ...
```

**Frontmatter fields:**
- `description` (string): Brief description of the agent's purpose
- `enabled` (boolean, default: true): Whether the agent is active

**Content:** The entire markdown file (after frontmatter) is returned as-is to the client without any transformation

### 3. Module Architecture

#### 3.1 AgentProvider Class
Exposes a single agent markdown file as an MCP resource.

**Location:** `src/drunk_ai_proxy/proxies/agent/agent_provider.py`

**Extends:** `Provider` (FastMCP base class)

**Responsibilities:**
- Load and parse a single agent markdown file
- Extract description and enabled status from YAML frontmatter
- Expose agent as resource with `agent://` URI scheme
- Serve raw markdown content without transformation
- Respect the `enabled` field (disabled agents not listed/accessible)

**Key methods:**
- `__init__(agent_path, agent_name, description, enabled)` - Initialize with agent metadata
- `_list_resources()` - Return agent resource if enabled
- `_get_resource(uri)` - Retrieve resource by URI
- `_read_resource(uri)` - Read and return raw markdown content

**AgentResource subclass:**
- Pydantic model storing agent metadata
- `enabled` field to track active status
- `file_path` field pointing to markdown file
- `read()` method returns raw markdown content

#### 3.2 CustomAgentsDirectoryProvider Class
Discovers agents from directory structure and aggregates them via AggregateProvider.

**Location:** `src/drunk_ai_proxy/proxies/agent/custom_agents_directory_provider.py`

**Extends:** `AggregateProvider` (FastMCP base class for multi-provider aggregation)

**Responsibilities:**
- Recursively scan directory for `*.md` files
- Parse YAML frontmatter from each file
- Extract description and enabled status
- Create AgentProvider instances for each agent
- Support namespace paths (subdirectories)
- Handle discovery, duplicate detection, and error logging
- Optionally reload agents on each request

**Key methods:**
- `__init__(roots, reload=False)` - Initialize with root directory/directories
- `_discover_agents()` - Scan and load all agents
- `_parse_frontmatter(content)` - Extract YAML fields from markdown
- `_sanitize_agent_name(name)` - Normalize agent names
- `_iter_agent_files(root)` - Get all agent files in directory
- `_ensure_discovered()` - Lazy load agents on first access
- `_list_resources()`, `_get_resource()` - Aggregate provider methods

**Directory Structure Support:**
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

#### 3.3 Configuration Updates

**Location:** `src/drunk_ai_proxy/utils/config_yaml.py`

Update `McpConfig` class:
```python
class McpConfig(ConfigBaseModel):
    # ... existing fields ...
    agents_dir: Optional[str] = Field(
        default=None, 
        description="Directory containing markdown agent definitions (optional)"
    )
```

**Config YAML example:**
```yaml
mcp:
  - path: /agents
    spec_type: mcp
    agents_dir: agents
```

#### 3.4 Module Organization
```
src/drunk_ai_proxy/proxies/agent/
  __init__.py                            # Export AgentProvider, CustomAgentsDirectoryProvider
  agent_provider.py                      # AgentProvider and AgentResource classes
  custom_agents_directory_provider.py    # CustomAgentsDirectoryProvider class
```

### 4. Integration Points

#### 4.1 Update Server/Provider Initialization
In `src/app/server.py` or provider initialization:
```python
# When agents_dir is configured, instantiate and mount CustomAgentsDirectoryProvider
if config.agents_dir:
    agents_provider = CustomAgentsDirectoryProvider(
        roots=config.agents_dir,
        reload=False
    )
    # Mount the provider to the MCP instance
    app.add_provider(agents_provider)  # or mcp.add_provider()
```

#### 4.2 Update __init__ Exports
Add to `src/drunk_ai_proxy/proxies/agent/__init__.py`:
```python
from .agent_provider import AgentProvider, AgentResource
from .custom_agents_directory_provider import CustomAgentsDirectoryProvider

__all__ = ["AgentProvider", "AgentResource", "CustomAgentsDirectoryProvider"]
```

And optionally update `src/drunk_ai_proxy/proxies/__init__.py` to include agent module imports.

### 5. Features & Validation

#### 5.1 Agent Discovery
- Recursive directory scan via `glob()` patterns
- Support both flat and nested directory structures:
  - Flat: `root/*.md` → `agent://agent_name`
  - Namespaced: `root/namespace/*.md` → `agent://namespace/agent_name`
- Normalize agent names: lowercase, replace spaces/special chars with underscores
- Example: `tools/code-refactor.md` → `agent://tools/code_refactor`

#### 5.2 Frontmatter Parsing
- Extract `description` field (required, used for resource metadata)
- Extract `enabled` field (optional, defaults to true)
- Simple key-value YAML parsing (not full YAML library)
- Graceful handling of missing or malformed frontmatter

#### 5.3 Configuration Validation
- In `McpConfig._validate_fields()`: Accept agents_dir as valid MCP spec
- Path resolution: relative paths resolved against `CONFIG_DIR`
- Validate directory exists and is accessible

#### 5.4 Error Handling
- Log-and-continue pattern for malformed files
- Deduplicate agent names (warn on collision, skip duplicate)
- Skip files missing `description` field with warning
- Graceful behavior if agents_dir is empty or missing
- Proper logging of all errors (type names only, not full messages)

#### 5.5 Logging
Follow codebase convention:
```python
self._logger: Logger = setup_logging(__name__)
# Log errors as type names: type(e).__name__
self._logger.error("Failed to load agent: %s", type(e).__name__)
```

## Implementation Steps

### Phase 1: Core Provider Classes (✅ COMPLETED)
1. ✅ Create `agent_provider.py` with AgentProvider class
   - Extend FastMCP Provider base class
   - Load single agent from markdown file
   - Parse YAML frontmatter
   
2. ✅ Create `custom_agents_directory_provider.py` with CustomAgentsDirectoryProvider class
   - Extend FastMCP AggregateProvider
   - Discover agents from directory
   - Create AgentProvider instances
   - Support namespace paths

3. ✅ Create `__init__.py` for agent module
   - Export AgentProvider, AgentResource, CustomAgentsDirectoryProvider

### Phase 2: Configuration Integration (⏳ TODO)
4. Update `config_yaml.py`
   - Add `agents_dir` field to McpConfig
   - Update validation to accept agents_dir

5. Update server files (`app/server.py` or proxies initialization)
   - Instantiate CustomAgentsDirectoryProvider when agents_dir configured
   - Mount provider to application

6. **Tests:** Create `tests/test_agent_provider.py`
   - Agent file loading
   - Frontmatter parsing
   - Resource URI generation
   - Enabled/disabled agent handling
   
7. **Tests:** Create `tests/test_custom_agents_directory_provider.py`
   - Directory scanning
   - Namespace path support
   - Duplicate detection
   - Name sanitization

### Phase 3: Data & Documentation (⏳ TODO)
8. Create example agents in `data/agents/`
    ```
    data/agents/
      reasoning-engine.md       # Flat: agent://reasoning_engine
      
      core/
        planning.md             # Namespaced: agent://core/planning
        analysis.md             # Namespaced: agent://core/analysis
      
      tools/
        code-refactor.md        # Namespaced: agent://tools/code_refactor
        test-generator.md       # Namespaced: agent://tools/test_generator
    ```

9. Document agent format and usage
    - Create `docs/guides/agents.md` 
    - Example agent markdown with frontmatter
    - URI reference format
    - How to organize agents by category

5. Create `__init__.py` for agent module
   - Export public classes

6. **Tests:** Create `tests/test_agent_provider.py`
   - Provider initialization
   - Agent loading via provider
   - FastMCP resource registration
   - Error handling

### Phase 3: Configuration & Mounting
7. Update `config_yaml.py`
   - Add `agents_dir` field to McpConfig
   - Update validation logic

8. Update server files (app/server.py or proxies init)
   - Mount agents provider when agents_dir configured
   - Handle optional configuration

9. **Tests:** Integration tests
   - Config loading with agents_dir
   - Full end-to-end provider mounting

### Phase 4: Documentation & Examples
10. Create example agents in `data/agents/`
    ```
    data/agents/
      core/
        reasoning-engine.md     # System agent for reasoning
        planning-agent.md       # System agent for planning
      tools/
        code-refactor.md        # Tool-using agent
        test-generator.md       # Test generation agent
    ```

11. Document agent format and usage
    - Add to `docs/guides/agents.md` 
    - Example frontmatter fields
    - URI reference format

## Testing Strategy

### Unit Tests

**test_agent_template.py**
- Parse YAML frontmatter correctly
- Both `description` and `enabled` fields handled
- Store raw markdown content without transformation
- Error on malformed YAML
- Preserve exact markdown content including whitespace

**test_agent_loader.py**
- Load single agent file
- Recursively discover agents in subdirectories
- Normalize agent names correctly
- Skip disabled agents (enabled: false)
- Log warnings on malformed files
- Deduplicate conflicting names
- Handle missing/inaccessible directories
- Empty directory handling

**test_agent_provider.py**
- Initialize with valid config
- Raise error if agents_dir not configured
- Load agents via create_proxy()
- Register agents as MCP resources
- Resource URIs match `agent://` pattern
- Caching behavior
- Auth provider injection

### Integration Tests
- Config YAML with agents_dir section
- Full provider mounting in application
- Resource endpoint accessibility via MCP

## Risk Analysis

### Low Risk
- Follows existing PromptLoader pattern (proven approach)
- Reuses validation and error handling patterns
- Isolated module with clear dependencies

### Medium Risk
- MCP resource registration API differences
  - **Mitigation**: Check FastMCP documentation for current resource API
  - Use same pattern as existing providers

### No Major Risks Identified
- Simple, single-responsibility modules
- Backward compatible (agents_dir optional)
- No breaking changes to existing code

## Success Criteria

✅ Agents can be loaded from configurable directory
✅ Markdown files with YAML frontmatter parsed correctly
✅ Agents exposed as MCP resources with `agent://` URI prefix
✅ Subdirectory nesting supported with namespace prefixes
✅ Disabled agents skipped
✅ Duplicate names handled gracefully
✅ Error logging follows security guidelines (no sensitive data)
✅ >90% test coverage for new modules
✅ Configuration documented with examples
✅ Example agents provided in data/agents/

## Dependencies
- FastMCP (already available)
- Pydantic (already available)
- YAML parsing (already available via config_yaml)
- Logging (already available)

## Performance Considerations
- Agent discovery happens on initialization/mount
- Caching prevents repeated file I/O
- No significant performance impact
- Lazy loading optional if needed later

## Future Extensions
1. Agent composition/chaining support via metadata
2. Agent versioning support in frontmatter
3. Conditional agent loading based on environment/config
4. Agent tagging/categorization metadata
5. Agent lifecycle hooks (if needed)

## References
- [PromptLoader](src/drunk_ai_proxy/proxies/prompt/prompt_loader.py) - Template pattern
- [McpPromptProvider](src/drunk_ai_proxy/proxies/prompt/prompt_provider.py) - Provider pattern
- [McpBaseProvider](src/drunk_ai_proxy/proxies/mcp/base_provider.py) - Base class
- [CustomSkillsDirectoryProvider](src/drunk_ai_proxy/proxies/mcp/custom_skills_directory_provider.py) - Resource registration pattern
- [McpConfig](src/drunk_ai_proxy/utils/config_yaml.py) - Configuration model

