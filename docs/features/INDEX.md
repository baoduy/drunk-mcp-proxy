# MCP Proxy Features Documentation

This directory contains documentation for all features of the drunk-mcp-proxy server.

## Available Features

### [OpenAPI Integration](./openapi/)

Complete documentation for loading and transforming OpenAPI specifications into MCP servers.

**Quick Links:**

- [README](./openapi/README.md) - Start here for overview
- [Quick Reference](./openapi/QUICKREF_OPENAPI.md) - Quick start guide (5 min read)
- [Complete Guide](./openapi/OPENAPI_LOADER_GUIDE.md) - Full documentation (20 min read)
- [Implementation Details](./openapi/OPENAPI_IMPLEMENTATION_SUMMARY.md) - Technical deep-dive
- [Code Examples](./openapi/EXAMPLES_OPENAPI_LOADER.py) - 11 runnable examples
- [Naming Convention](./openapi/OPENAPI_NAMING_CONVENTION.md) - File naming rules
- [Requirements Verification](./openapi/OPENAPI_REQUIREMENTS_VERIFICATION.md) - Feature checklist

## Directory Structure

```
docs/features/
├── INDEX.md                    (This file)
└── openapi/                    (Feature directory)
    ├── README.md               (Main entry point)
    ├── QUICKREF_OPENAPI.md     (Quick reference)
    ├── OPENAPI_LOADER_GUIDE.md (Complete guide)
    ├── EXAMPLES_OPENAPI_LOADER.py (Code examples)
    ├── OPENAPI_*.md            (Additional guides)
    └── ...
```

## Adding New Features

When adding a new feature to the MCP proxy server:

1. **Create feature directory**: `docs/features/{feature_name}/`
2. **Create main documentation**: `docs/features/{feature_name}/README.md`
3. **Add supporting docs**: All related guides, examples, and references
4. **Update this index**: Add a link and description in this INDEX.md

### Feature Documentation Template

```markdown
# {Feature Name} Documentation

Brief description of the feature.

## Quick Start

- Link to quick reference or main README
- Basic usage instructions

## Files

- README.md - Overview
- QUICKREF_{FEATURE_NAME}.md - Quick reference
- {FEATURE_NAME}_GUIDE.md - Complete documentation
- EXAMPLES_{FEATURE_NAME}.py - Code examples
```

## Navigation

- **New to this feature?** → Start with [README](./openapi/README.md)
- **Need quick answers?** → Check [Quick Reference](./openapi/QUICKREF_OPENAPI.md)
- **Want complete details?** → Read [Complete Guide](./openapi/OPENAPI_LOADER_GUIDE.md)
- **Learning by example?** → Review [Code Examples](./openapi/EXAMPLES_OPENAPI_LOADER.py)
- **Implementing feature?** → See [Implementation Details](./openapi/OPENAPI_IMPLEMENTATION_SUMMARY.md)

## Documentation Standards

Each feature documentation should include:

- **README.md** - Main overview and entry point
- **QUICKREF_*.md** - Quick reference guide (5-10 min read)
- **{FEATURE}_GUIDE.md** - Complete documentation (20+ min read)
- **EXAMPLES_*.py** - Practical code examples
- **{FEATURE}_*.md** - Additional guides as needed (naming, requirements, etc.)

## Contributing Documentation

When documenting a feature:

1. Start with a clear README.md
2. Include quick reference for common tasks
3. Provide complete technical details
4. Add practical code examples
5. Document naming conventions and requirements
6. Keep files organized in feature subdirectories

