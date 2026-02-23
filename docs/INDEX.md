# drunk-mcp-proxy Documentation

Welcome to the comprehensive documentation for drunk-mcp-proxy - a powerful, production-ready dynamic proxy server for the Model Context Protocol (MCP).

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
- [**Namespace Isolation**](features/mcp/namespaces.md) - Preventing tool name conflicts
- [**MCP Transports**](features/mcp/transports.md) - HTTP, SSE, stdio transport support

#### OpenAPI Features
- [**OpenAPI Integration**](features/openapi/integration.md) - Converting OpenAPI to MCP tools
- [**OpenAPI Configuration**](features/openapi/configuration.md) - OpenAPI-specific settings
- [**Request Mapping**](features/openapi/request-mapping.md) - How requests are transformed

#### Authentication Features
- [**Authentication Overview**](features/authentication/overview.md) - Auth architecture and providers
- [**Pass-Through Authentication**](features/authentication/pass-through.md) - Token forwarding
- [**Azure OAuth**](features/authentication/azure-oauth.md) - Azure AD integration
- [**JWT Authentication**](features/authentication/jwt.md) - JWT validation
- [**OAuth Providers**](features/authentication/oauth-providers.md) - GitHub, Google, Discord, etc.

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

**👤 New Users**
1. Start with [Quick Start Guide](getting-started/quick-start.md)
2. Follow [First Steps](getting-started/first-steps.md)
3. Explore [Example Configurations](examples/configurations.md)

**🔧 System Administrators**
1. Review [Production Setup](deployment/production.md)
2. Configure [Environment Variables](configuration/environment-variables.md)
3. Set up [Monitoring](deployment/monitoring.md)

**🔐 Security Teams**
1. Understand [Authentication Overview](features/authentication/overview.md)
2. Review [Security Considerations](deployment/security.md)
3. Configure appropriate [Auth Providers](features/authentication/oauth-providers.md)

**👨‍💻 Developers**
1. Study [System Architecture](architecture/system-architecture.md)
2. Review [Python Modules](api-reference/modules.md)
3. Check [Development Guide](development/guide.md)

### By Topic

**Configuration**
- [Configuration Files](configuration/config-files.md)
- [Environment Variables](configuration/environment-variables.md)
- [Schema Validation](configuration/schema-validation.md)

**Authentication**
- [Overview](features/authentication/overview.md)
- [Azure OAuth](features/authentication/azure-oauth.md)
- [Pass-Through](features/authentication/pass-through.md)
- [JWT](features/authentication/jwt.md)

**Deployment**
- [Docker](deployment/docker.md)
- [Production](deployment/production.md)
- [Monitoring](deployment/monitoring.md)

**Troubleshooting**
- [Development Troubleshooting](development/troubleshooting.md)
- [Production Issues](deployment/production.md#troubleshooting)

## 📖 Additional Resources

### External Documentation
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Starlette Documentation](https://www.starlette.io/)

### Project Resources
- [GitHub Repository](https://github.com/baoduy/drunk-mcp-proxy)
- [Issue Tracker](https://github.com/baoduy/drunk-mcp-proxy/issues)
- [Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)

## 🆘 Getting Help

If you can't find what you're looking for:

1. Check the [Troubleshooting Guide](development/troubleshooting.md)
2. Search [existing issues](https://github.com/baoduy/drunk-mcp-proxy/issues)
3. Ask in [Discussions](https://github.com/baoduy/drunk-mcp-proxy/discussions)
4. [Open a new issue](https://github.com/baoduy/drunk-mcp-proxy/issues/new)

---

**Documentation Version**: 0.1.0  
**Last Updated**: 2026-02-22
