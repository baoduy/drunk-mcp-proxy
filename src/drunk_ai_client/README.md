# Drunk MCP Client (STDIO)

A stdio MCP client that connects to the Drunk MCP Proxy server, enabling remote MCP services with **agent synchronization** and **remote resource management**.

## Features
- **Remote Agent Sync**: Automatically sync agents from remote sources
- **Skill Management**: Local skill directory synchronization
- **Resource Downloader**: Fetch and cache remote MCP resources
- **Agent Execution**: Execute agents with permission controls
- **Offline Support**: Cached agents for offline use

## Installation & Usage

### Local Development (from repo root)
```bash
uvx --from ./src/drunk_ai_client drunk_ai_client
```

### Published Package
```bash
uvx drunk_ai_client
```

### Direct Installation
```bash
pip install -e ./src/drunk_ai_client
drunk-ai-client
```

## Configuration

The client supports multiple configuration sources:

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `DRUNK_API_URL` | Yes | Drunk MCP Proxy server URL (e.g., `http://localhost:9123`) |
| `DRUNK_API_KEY` | No | Bearer token for authentication |
| `DRUNK_SKILL_DIR` | No | Local directory for synced skills (default: `./skills`) |
| `DRUNK_AGENTS_DIR` | No | Local directory for synced agents (default: `./agents`) |
| `DRUNK_SYNC_INTERVAL` | No | Sync interval in seconds (default: `300`) |
| `DRUNK_ALLOW_OVERWRITE` | No | Overwrite local files during sync (`true/false`) |

### Command Line Options
```bash
drunk-ai-client --sync --agent-source https://remote.repo/agents.yaml
```

## New Agent Sync Feature

### Sync Remote Agents
```bash
# Sync from a remote source (new!)
DRUNK_API_URL=http://localhost:9123 \
DRUNK_AGENTS_DIR=./my-agents \
drunk-ai-client --sync-agents --source https://your-agent-repo.com/agents.yaml
```

### Agent Directory Structure
```
agents/
├── agent1/
│   ├── config.yaml
│   ├── skills/
│   └── resources/
└── agent2/
    └── ...
```

### Skills Sync
```bash
# Sync skills from proxy
DRUNK_SKILL_DIR=./skills drunk-ai-client --sync-skills
```

## Usage Examples

### Connect to Proxy with Agent Sync
```bash
# Start the client with agent sync enabled
DRUNK_API_URL=http://localhost:9123 \
DRUNK_AGENTS_DIR=./agents \
drunk-ai-client --sync --agent-source https://repo.com/agents.yaml
```

### Execute a Remote Agent
Once agents are synced locally, they can be used as standard MCP tools:
```javascript
// Claude Code or any MCP client can use these tools
{
  "name": "agent_search",
  "description": "Search through synced agents",
  "inputSchema": { ... }
}
```

## Development

### Run Tests
```bash
python -m pytest tests/
```

### Build and Install Locally
```bash
pip install -e ".[dev]"
```

## Notes
- The stdio bridge logs to stderr by default (FastMCP behavior)
- Agent sync runs in background if `--sync` flag is enabled
- Remote resources are cached locally with automatic refresh
- Authentication tokens are validated on each request
- Agents execute with sandboxed permissions

## See Also
- [Drunk MCP Proxy Server](../README.md)
- [Agent Provider Documentation](../docs/features/agent-management/)
- [Configuration Guide](../docs/configuration/config-files.md)
