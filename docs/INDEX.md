# drunk-mcp-proxy Documentation

Welcome to the comprehensive documentation for drunk-mcp-proxy - a powerful, production-ready dynamic proxy server for the Model Context Protocol (MCP), LLM APIs, and agent ecosystems.

## 📚 Documentation Structure

### Getting Started

Perfect for new users looking to get up and running quickly.

- [**Installation Guide**](getting-started/installation.md) - System requirements, installation methods
- [**Quick Start Guide**](getting-started/quick-start.md) - Get running in 5 minutes
- [**First Steps**](getting-started/first-steps.md) - Your first proxy configuration

### Configuration

Everything you need to know about configuring drunk-mcp-proxy.

- [**Configuration Files**](configuration/config-files.md) - Complete config.yaml reference
- [**Environment Variables**](configuration/environment-variables.md) - All environment variables explained
- [**Schema Validation**](configuration/schema-validation.md) - Configuration validation details

### Features

Deep dives into major features and capabilities.

#### MCP Features
- [**MCP Proxy Management**](features/mcp/proxy-management.md) - Managing MCP server proxies
- [**MCP Client (STDIO)**](features/mcp/drunk-mcp-client-stdio.md) - Local STDIO bridge to remote proxy
- [**Unified Resources Config**](features/mcp/unified-resources-config.md) - Skills, prompts, and agents config

#### Agent Ecosystem (New in v0.2.0)
- [**Agent Management**](features/agents-directory-implementation.md) - Agent provider and directory loading
- [**Remote Resource Sync**](features/mcp/unified-resources-config.md) - Background sync from remote sources

#### Prompt System (New in v0.2.0)
- [**Prompt Provider**](features/mcp-prompt-provider.md) - Markdown prompt templates with parameters
- [**Prompt Role Support**](features/prompt_role_support.md) - Role-based prompt configuration

#### LLM Proxy Features (New in v0.2.0)
- [**Anthropic Compatibility**](features/anthropic-provider.md) - Messages API conversion layer
- [**WebSocket Responses API**](features/websocket/plan-wsResponses.prompt.md) - Real-time WebSocket streaming

#### OpenAPI Features
- [**OpenAPI Integration**](features/openapi/README.md) - Converting OpenAPI specs to MCP tools
- [**OpenAPI Quick Reference**](features/openapi/QUICKREF_OPENAPI.md) - Quick start for OpenAPI
- [**OpenAPI Loader Guide**](features/openapi/OPENAPI_LOADER_GUIDE.md) - Complete guide

#### Authentication Features
- [**Authentication Overview**](features/authentication/overview.md) - 14+ auth providers
- [**Environment Variable Resolution**](features/ENV_VARIABLE_RESOLUTION.md) - `$VAR` / `${VAR}` resolution in config

### Architecture

Technical architecture and design documentation.

- [**System Architecture**](architecture/system-architecture.md) - Overall system design
- [**Component Overview**](architecture/components.md) - Core components explained
- [**Request Flow**](architecture/request-flow.md) - How requests are processed
- [**Module Structure**](architecture/module-structure.md) - Python module organization

### API Reference

Technical API documentation for developers.

- [**REST API Endpoints**](api-reference/endpoints.md) - HTTP API reference
- [**Python Modules**](api-reference/modules.md) - Python package reference
- [**Configuration Schema**](api-reference/config-schema.md) - JSON schema definitions

### Deployment

Production deployment guides and best practices.

- [**Docker Deployment**](deployment/docker.md) - Docker and Docker Compose setup
- [**Production Setup**](deployment/production.md) - Production best practices
- [**Health Checks & Monitoring**](deployment/monitoring.md) - Monitoring and observability
- [**Security Considerations**](deployment/security.md) - Security best practices

### Development

Resources for contributing to drunk-mcp-proxy.

- [**Development Guide**](development/guide.md) - Setting up dev environment
- [**Testing**](development/testing.md) - Running tests and coverage
- [**Troubleshooting**](development/troubleshooting.md) - Common issues and solutions
- [**Contributing**](development/contributing.md) - Contribution guidelines

### Examples

Practical examples and recipes.

- [**Example Configurations**](examples/configurations.md) - Sample config files
- [**Use Cases**](examples/use-cases.md) - Common deployment patterns
- [**Integration Examples**](examples/integrations.md) - Integrating with other systems

## 🔍 Quick Navigation

### By User Type

**New Users**
1. Start with [Quick Start Guide](getting-started/quick-start.md)
2. Follow [First Steps](getting-started/first-steps.md)
3. Explore [Example Configurations](examples/configurations.md)

**System Administrators**
1. Review [Production Setup](deployment/production.md)
2. Configure [Environment Variables](configuration/environment-variables.md)
3. Set up [Monitoring](deployment/monitoring.md)

**Security Teams**
1. Understand [Authentication Overview](features/authentication/overview.md)
2. Review [Security Considerations](deployment/security.md)
3. Configure appropriate auth providers

**Developers**
1. Study [System Architecture](architecture/system-architecture.md)
2. Review [Python Modules](api-reference/modules.md)
3. Check [Development Guide](development/guide.md)

### By Feature (v0.2.0)

**Agent Ecosystem**
- [Agent Management](features/agents-directory-implementation.md) - Agent provider and directory
- [Unified Resources](features/mcp/unified-resources-config.md) - Skills, prompts, agents config

**Prompt System**
- [Prompt Provider](features/mcp-prompt-provider.md) - Markdown templates with parameters
- [Role Support](features/prompt_role_support.md) - Role-based configuration

**LLM Proxy**
- [Anthropic Provider](features/anthropic-provider.md) - Messages API compatibility
- [WebSocket Responses](features/websocket/plan-wsResponses.prompt.md) - Real-time streaming

**Remote Resources**
- [Unified Config](features/mcp/unified-resources-config.md) - Remote resource sync configuration
- [Client Sync](features/mcp/drunk-mcp-client-stdio.md) - STDIO client with sync

### By Topic

**Configuration**
- [Configuration Files](configuration/config-files.md)
- [Environment Variables](configuration/environment-variables.md)
- [Schema Validation](configuration/schema-validation.md)
- [Env Variable Resolution](features/ENV_VARIABLE_RESOLUTION.md)

**Authentication**
- [Overview](features/authentication/overview.md)
- [Pass-Through](features/authentication/pass-through.md)

**Deployment**
- [Docker](deployment/docker.md)
- [Production](deployment/production.md)
- [Monitoring](deployment/monitoring.md)

**Troubleshooting**
- [Development Troubleshooting](development/troubleshooting.md)
- [Production Issues](deployment/production.md#troubleshooting)

## 🆕 What's New in v0.2.0

### Agent Ecosystem
- Markdown agent files with YAML frontmatter exposed as MCP resources (`agent://` URI)
- Flat and namespaced directory layouts
- Remote agent synchronization via background tasks

### Prompt System
- Markdown prompt templates with typed parameters (`str`, `int`, `float`, `bool`)
- Role support (`user`/`assistant`/`system`) in prompt frontmatter
- Dynamic MCP prompt registration with parameter metadata

### LLM Proxy
- Anthropic Messages API compatibility layer (bidirectional conversion)
- WebSocket Responses API with native and HTTP fallback modes
- Connection pooling per provider

### Remote Resources
- Background sync task with TTL-based cache freshness
- HTTPS-only downloads with extension allowlisting and size limits
- Configurable retry and parallel download support

### Client
- STDIO bridge with skill and agent synchronization
- Manifest-based and list-based resource downloading
- Built-in search transforms (Regex, BM25)

See the full [CHANGELOG](../CHANGELOG.md) for details.

## 📖 Additional Resources

### External Documentation
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Starlette Documentation](https://www.starlette.io/)

### Project Resources
- [GitHub Repository](https://github.com/baoduy/drunk-mcp-proxy)
- [Deep Wiki](https://deepwiki.com/baoduy/drunk-mcp-proxy)
- [Docker Hub](https://hub.docker.com/r/baoduy2412/mcp-proxy)
- [Issue Tracker](https://github.com/baoduy/drunk-mcp-proxy/issues)
- [Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)

## 🆘 Getting Help

If you can't find what you're looking for:

1. Check the [Troubleshooting Guide](development/troubleshooting.md)
2. Search [existing issues](https://github.com/baoduy/drunk-mcp-proxy/issues)
3. Ask in [Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)
4. [Open a new issue](https://github.com/baoduy/drunk-mcp-proxy/issues/new)

---

**Documentation Version**: 0.2.0
**Last Updated**: 2026-03-11
