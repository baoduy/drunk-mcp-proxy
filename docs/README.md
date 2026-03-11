# MCP Proxy Server Documentation Hub

Welcome to the drunk-mcp-proxy documentation. This documentation covers all aspects of the MCP proxy server, including its enhanced features like agent management, remote resource synchronization, and enterprise authentication.

## 📋 Complete Documentation Structure

```
docs/
├── README.md                              (This file - Main Hub)
├── features/                              (Feature Documentation)
│   ├── INDEX.md                         (Feature Index)
│   ├── agent-management/                 (Agent ecosystem)
│   ├── authentication/                   (Auth providers)
│   ├── llm-proxy/                       (LLM gateway)
│   ├── openapi/                         (OpenAPI integration)
│   ├── websocket/                       (Real-time streaming)
│   └── mcp/                             (MCP orchestration)
├── architecture/                         (System Design)
│   ├── README.md
│   ├── SPECIFICATION.md
│   ├── ARCHITECTURE_DIAGRAMS.md
│   └── APPLIFESPANMANAGER_CREATION.md
├── development/                          (Development Guides)
│   ├── README.md
│   ├── IMPLEMENTATION_CHECKLIST.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── BUILD_MCP_SERVERS_QUICK_REF.md
│   ├── TYPE_HINTS_QUICK_REF.md
│   └── QUICKREF_MCPProxyServer.md
├── refactoring/                          (Code Improvements)
│   ├── README.md
│   ├── REFACTORING_COMPLETION.md
│   ├── REFACTORING_SUMMARY.md
│   └── REFACTORING_INDEX.md
├── analysis/                             (Reports & Metrics)
│   ├── README.md
│   ├── ANALYSIS_DETAILED_METRICS.md
│   ├── ANALYSIS_EXECUTIVE_SUMMARY.md
│   ├── ANALYSIS_README.md
│   ├── COMPLETION_SUMMARY.md
│   ├── FINAL_VERIFICATION_REPORT.md
│   ├── REMEDIATION_PLAN.md
│   ├── CHANGE_LOG.md
│   └── FINAL_IMPLEMENTATION_SUMMARY.md
├── guides/                               (Guidelines & Checklists)
│   ├── README.md
│   └── CHECKLIST_GUIDE.md
└── planning/                             (Project Planning)
    ├── README.md
    ├── TASK_BREAKDOWN.md
    ├── TASK_CHECKLIST.md
    ├── TASK_BREAKDOWN_INDEX.md
    ├── DOCUMENTATION_ORGANIZATION_PLAN.md
    ├── DOCUMENTATION_ORGANIZATION.md
    ├── IMPLEMENTATION_REPORT.md
    └── FINAL_COMPLETION_SUMMARY.md
```

## 🎯 Quick Navigation by Category

### 🚀 [Features](./features/)

Feature-specific documentation with guides, examples, and references

- **Agent Management** - Complete agent ecosystem with remote sync
- **Authentication** - 14+ enterprise auth providers
- **LLM Proxy** - Multi-provider LLM gateway
- **OpenAPI Integration** - Transform OpenAPI specs to MCP
- **WebSocket** - Real-time streaming support
- **MCP Proxy** - MCP server orchestration

### 🏗️ [Architecture](./architecture/)

System design, specifications, and technical architecture

- System specification and design patterns
- Architecture diagrams and components
- Request flow and component interactions

### 💻 [Development](./development/)

Development guides, references, and implementation details

- Implementation checklists and guides
- Code references and quick tips
- Testing and debugging procedures

### 🔧 [Refactoring](./refactoring/)

Code improvements, refactoring history, and quality enhancements

- Refactoring projects and improvements
- Code quality tracking
- Performance optimizations

### 📊 [Analysis](./analysis/)

Project metrics, reports, and analysis documentation

- Detailed metrics and measurements
- Verification and completion reports
- Quality assurance documentation

### ✅ [Guides](./guides/)

Guidelines, checklists, and best practices

- Master checklist and guidelines
- Best practices and standards
- Development workflows

### 📋 [Planning](./planning/)

Project planning, task breakdowns, and implementation documentation

- Task breakdown and checklists
- Implementation guides and reports
- Project timeline and milestones

## 📚 Features Documentation

### [Agent Management](./features/agent-management/)

Complete documentation for the new agent ecosystem with remote resource synchronization.

- **Quick Start**: [README](./features/agent-management/README.md) (5 min)
- **Quick Reference**: [Quick Ref](./features/agent-management/QUICKREF_AGENT.md) (10 min)
- **Complete Guide**: [Full Guide](./features/agent-management/AGENT_MANAGEMENT_GUIDE.md) (20 min)
- **Code Examples**: [Examples](./features/agent-management/EXAMPLES_AGENT.py) (15 min)
- **Technical Details**: [Implementation](./features/agent-management/AGENT_IMPLEMENTATION_SUMMARY.md) (30 min)

**Key Features:**

- Remote agent discovery and sync
- Local agent storage with version tracking
- Permission-based execution controls
- Agent lifecycle management

### [OpenAPI Integration](./features/openapi/)

Load OpenAPI specifications and transform them into MCP servers.

- **Quick Start**: [README](./features/openapi/README.md) (5 min)
- **Quick Reference**: [Quick Ref](./features/openapi/QUICKREF_OPENAPI.md) (10 min)
- **Complete Guide**: [Full Guide](./features/openapi/OPENAPI_LOADER_GUIDE.md) (20 min)
- **Code Examples**: [Examples](./features/openapi/EXAMPLES_OPENAPI_LOADER.py) (15 min)
- **Technical Details**: [Implementation](./features/openapi/OPENAPI_IMPLEMENTATION_SUMMARY.md) (30 min)

**Key Features:**

- Automatic discovery of `*.openapi.json` files
- FastMCP server creation from OpenAPI specs
- Namespace-based mounting and routing
- Full error handling and logging
- Memory-based caching for performance

## 🎯 Common Tasks

### Adding an OpenAPI API

```bash
# 1. Create file: data/myapi.openapi.json
# 2. Add OpenAPI specification with required fields
# 3. Restart server: python -m src.main
# 4. Access at: http://localhost:9123/myapi/mcp
```

See [OpenAPI Guide](./features/openapi/OPENAPI_LOADER_GUIDE.md) for details.

### Running the Server

```bash
python -m src.main
```

The server automatically loads:

- Static MCP proxies from `*.mcp.json` files
- OpenAPI servers from `*.openapi.json` files
- Agent sync if configured

### Debugging

Enable debug logging:

```bash
export FASTMCP_LOG_LEVEL=DEBUG
python -m src.main
```

## 📚 Documentation by Use Case

### I want to...

**...use the OpenAPI feature**
→ [OpenAPI README](./features/openapi/README.md)

**...get started quickly with OpenAPI**
→ [OpenAPI Quick Reference](./features/openapi/QUICKREF_OPENAPI.md)

**...understand how OpenAPI integration works**
→ [OpenAPI Implementation Details](./features/openapi/OPENAPI_IMPLEMENTATION_SUMMARY.md)

**...see code examples**
→ [OpenAPI Code Examples](./features/openapi/EXAMPLES_OPENAPI_LOADER.py)

**...learn about naming conventions**
→ [OpenAPI Naming Convention](./features/openapi/OPENAPI_NAMING_CONVENTION.md)

**...verify feature requirements**
→ [OpenAPI Requirements](./features/openapi/OPENAPI_REQUIREMENTS_VERIFICATION.md)

**...use the new agent features**
→ [Agent Management](./features/agent-management/)

**...sync remote resources**
→ [Remote Resources](./features/agent-management/remote-resources.md)

**...configure authentication**
→ [Authentication](./features/authentication/)

**...use LLM proxy**
→ [LLM Proxy](./features/llm-proxy/)

**...stream real-time responses**
→ [WebSocket](./features/websocket/)

## 🛠️ Development

### Code Structure

```
src/
├── proxies/
│   ├── openapi_proxies.py      (OpenAPI loader)
│   ├── static_proxies.py       (Static proxy loader)
│   ├── agent/                   (Agent management)
│   └── __init__.py
├── app/
│   ├── server.py               (Main server)
│   ├── auth.py
│   ├── lifespan.py
│   ├── middleware/
│   └── __init__.py
├── tools/
│   ├── file_utils.py           (File utilities - reusable)
│   ├── env.py
│   ├── logging_config.py
│   └── validation.py
└── __init__.py
```

### Key Components

- **OpenApiMcpProxyLoader**: Loads and creates MCP servers from OpenAPI specs
- **StaticProxyLoader**: Creates proxies to remote MCP servers
- **AgentProvider**: Manages agent lifecycle and sync
- **file_utils**: Reusable file handling utilities (namespace extraction, validation)
- **MCPProxyServer**: Main server orchestrator

### Reusable Utilities

The `src/tools/file_utils.py` module provides reusable functions:

```python
from src.tools.file_utils import extract_namespace_from_path, is_valid_namespace

# Extract namespace from filename
namespace = extract_namespace_from_path("data/petstore.openapi.json", ".openapi.json")
# Returns: "petstore"

# Validate namespace
is_valid = is_valid_namespace(namespace)
# Returns: True if namespace is not None and not empty
```

## 📚 Reference

### Configuration Files

- `data/*.mcp.json` - Static MCP proxy configurations
- `data/*.openapi.json` - OpenAPI specifications
- `data/agents.yaml` - Agent configuration
- `config.yaml` - Unified configuration

### Environment Variables

- `FASTMCP_CONFIG_DIR` - Configuration directory (default: `data`)
- `FASTMCP_LOG_LEVEL` - Logging level (default: `INFO`)
- `FASTMCP_SERVER_AUTH` - Authentication configuration (optional)
- `FASTMCP_AGENT_SYNC` - Enable agent synchronization

### Mount Points

```
/mcp                           Root MCP server
/stock/mcp                     Static proxy (stock.mcp.json)
/{namespace}/mcp               OpenAPI server (namespace.openapi.json)
/agent/{id}                    Agent endpoint (new!)
```

## 🎓 Learning Path

### Beginner (15 minutes)

1. Read [Project README](../README.md)
2. Read [OpenAPI README](./features/openapi/README.md)
3. Run `python -m src.main` and test example APIs
4. Try agent sync: `drunk-ai-client --sync`

### Intermediate (45 minutes)

1. Read [OpenAPI Quick Reference](./features/openapi/QUICKREF_OPENAPI.md)
2. Review [Code Examples](./features/openapi/EXAMPLES_OPENAPI_LOADER.py)
3. Create your own `data/yourapi.openapi.json`
4. Test with the running server
5. Configure agent sync from remote source

### Advanced (2+ hours)

1. Study [Implementation Details](./features/openapi/OPENAPI_IMPLEMENTATION_SUMMARY.md)
2. Review [Source Code](../src/proxies/openapi_proxies.py)
3. Understand [Naming Conventions](./features/openapi/OPENAPI_NAMING_CONVENTION.md)
4. Implement custom features or integrations
5. Configure enterprise authentication

## 🔍 Finding What You Need

### By Topic

- **Getting Started**: [Features Index](./features/INDEX.md)
- **OpenAPI Feature**: [OpenAPI Docs](./features/openapi/)
- **Code Examples**: [Examples](./features/openapi/EXAMPLES_OPENAPI_LOADER.py)
- **Technical Details**: [Implementation](./features/openapi/OPENAPI_IMPLEMENTATION_SUMMARY.md)
- **Agent Management**: [Agent Docs](./features/agent-management/)
- **Authentication**: [Auth Docs](./features/authentication/)

### By Reading Time

- **5 minutes**: [OpenAPI README](./features/openapi/README.md)
- **10 minutes**: [Quick Reference](./features/openapi/QUICKREF_OPENAPI.md)
- **15 minutes**: [Code Examples](./features/openapi/EXAMPLES_OPENAPI_LOADER.py)
- **20+ minutes**: [Complete Guide](./features/openapi/OPENAPI_LOADER_GUIDE.md)

## ✅ Documentation Quality

All documentation includes:

- ✅ Clear examples
- ✅ Quick start guides
- ✅ Comprehensive coverage
- ✅ Code examples
- ✅ Common issues and solutions
- ✅ Links to related topics

## 📞 Getting Help

1. **Quick questions**: Check [Quick Reference](./features/openapi/QUICKREF_OPENAPI.md)
2. **How-to guides**: Review [Code Examples](./features/openapi/EXAMPLES_OPENAPI_LOADER.py)
3. **Detailed info**: Read [Complete Guide](./features/openapi/OPENAPI_LOADER_GUIDE.md)
4. **Troubleshooting**: See [Naming Convention](./features/openapi/OPENAPI_NAMING_CONVENTION.md)
5. **Feature requests**: Open an issue with documentation suggestions

---

**Happy coding with the enhanced MCP Proxy!** 🚀