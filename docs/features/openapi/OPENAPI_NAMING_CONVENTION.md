# OpenAPI File Loading - Naming Convention Enforcement

## Overview

The `OpenApiMcpProxyLoader` strictly enforces the `*.openapi.json` naming convention. **Only files matching this pattern
will be loaded from the data folder.**

## File Discovery Rules

### Strict Naming Convention

```
Pattern: {name}.openapi.json
```

### What Gets Loaded ✅

- `petstore.openapi.json` → namespace: `petstore`
- `api.openapi.json` → namespace: `api`
- `v2-users.openapi.json` → namespace: `v2-users`
- `jsonplaceholder.openapi.json` → namespace: `jsonplaceholder`
- `my-custom-api.openapi.json` → namespace: `my-custom-api`

### What Gets Ignored ❌

- `openapi.json` → (no namespace prefix - ignored)
- `config.json` → (wrong extension - ignored)
- `api.json` → (missing `.openapi` - ignored)
- `petstore-api.spec.json` → (wrong extension - ignored)
- `openapi.yaml` → (wrong format - ignored)
- `.openapi.json` → (no name prefix - ignored)

## Implementation Details

### File Discovery Process

```python
# Step 1: Scan for *.openapi.json files
pattern = os.path.join(self.config_dir, "*.openapi.json")
files = sorted(glob.glob(pattern))

# Step 2: Extract namespace from filename
namespace = self.extract_namespace_from_path(file_path)

# Step 3: Validate namespace (must exist)
if namespace is None:
    self.logger.warning("Skipping file with invalid naming convention: %s", file_path)
    continue

# Step 4: Load the file
spec = self.load_config_file(file_path)
```

### Namespace Extraction

```python
@staticmethod
def extract_namespace_from_path(path: str) -> str | None:
    """Extract namespace by removing .openapi.json suffix."""
    filename = Path(path).name
    if filename.endswith(".openapi.json"):
        # Remove the .openapi.json suffix to get the namespace
        return filename[: -len(".openapi.json")]
    return None
```

## Behavior Examples

### Example 1: Valid File

```
File: data/petstore.openapi.json
Action: ✅ LOADED
Namespace: "petstore"
Mount Point: /petstore/mcp
Server Name: petstore-openapi-mcp
```

### Example 2: Invalid Extension

```
File: data/petstore.json
Action: ❌ IGNORED
Reason: Does not match *.openapi.json pattern
```

### Example 3: Root Config (Not Supported)

```
File: data/openapi.json
Action: ❌ IGNORED
Reason: No namespace prefix (empty name)
```

### Example 4: Mixed Directory

```
Directory Contents:
  - stock.mcp.yaml              ← StaticProxyLoader loads this
  - wiki.mcp.yaml               ← StaticProxyLoader loads this
  - petstore.openapi.json       ← OpenApiMcpProxyLoader loads this ✅
  - jsonplaceholder.openapi.json ← OpenApiMcpProxyLoader loads this ✅
  - config.yaml                 ← Both loaders ignore this ❌
  - api.json                    ← Both loaders ignore this ❌

Result:
  - 2 static proxies mounted
  - 2 OpenAPI servers mounted
  - 2 files ignored
```

## Logging Output

When loading files from the data directory:

```
INFO: Found 2 OpenAPI configuration file(s) in data
DEBUG: Loaded OpenAPI specification file: data/petstore.openapi.json
DEBUG: Loaded OpenAPI spec (version=3.0.0, title=Swagger Petstore, api_version=1.0.0)
INFO: Loaded OpenAPI specification (namespace=petstore) from data/petstore.openapi.json
DEBUG: Loaded OpenAPI specification file: data/jsonplaceholder.openapi.json
DEBUG: Loaded OpenAPI spec (version=3.0.0, title=JSONPlaceholder API, api_version=1.0.0)
INFO: Loaded OpenAPI specification (namespace=jsonplaceholder) from data/jsonplaceholder.openapi.json
INFO: Creating FastMCP servers from 2 OpenAPI specification(s)
INFO: Created FastMCP server (namespace=petstore, name=petstore-openapi-mcp, base_url=...)
INFO: Created FastMCP server (namespace=jsonplaceholder, name=jsonplaceholder-openapi-mcp, base_url=...)
```

## Configuration Location

All OpenAPI files must be placed in the data directory:

```
drunk-mcp-proxy/
└── data/
    ├── mcp.yaml                     (StaticProxyLoader)
    ├── stock.mcp.yaml              (StaticProxyLoader)
    ├── wiki.mcp.yaml               (StaticProxyLoader)
    ├── petstore.openapi.json       ✅ OpenApiMcpProxyLoader
    ├── jsonplaceholder.openapi.json ✅ OpenApiMcpProxyLoader
    └── api.openapi.json            ✅ OpenApiMcpProxyLoader
```

## Directory Configuration

The config directory is controlled by environment variable:

```bash
export FASTMCP_CONFIG_DIR=data
python -m src.main
```

Default: `data/`

## Source Code

### File Discovery

Located in: `src/proxies/openapi_proxies.py`

**Line 249-260**: File discovery with glob pattern

```python
pattern = os.path.join(self.config_dir, "*.openapi.json")
files = sorted(glob.glob(pattern))
```

**Line 152-158**: Namespace extraction validation

```python
if filename.endswith(".openapi.json"):
    return filename[: -len(".openapi.json")]
return None
```

**Line 263-268**: Invalid file rejection

```python
namespace = self.extract_namespace_from_path(file_path)
if namespace is None:
    self.logger.warning("Skipping file with invalid naming convention: %s", file_path)
    continue
```

## Common Questions

### Q: Can I use `openapi.json` as root config?

**A:** No. There is no root OpenAPI config. All files must have a namespace prefix (e.g., `api.openapi.json`).

### Q: What if I have files in subdirectories?

**A:** Only files directly in the config directory are loaded. Subdirectories are ignored.

### Q: Can I customize the file extension?

**A:** No. Only `*.openapi.json` files are recognized. This is intentional to avoid conflicts with other JSON files.

### Q: What if a file matches the pattern but has invalid content?

**A:** The loader validates the OpenAPI specification. If it's invalid:

- The error is logged
- The file is skipped
- Processing continues with other files

### Q: Are files loaded in any specific order?

**A:** Yes. Files are sorted alphabetically by filename:

```python
files = sorted(glob.glob(pattern))
```

### Q: Can I have both `.mcp.yaml` and `.openapi.json` files?

**A:** Yes! They are loaded by different loaders:

- `StaticProxyLoader` loads `*.mcp.yaml` files
- `OpenApiMcpProxyLoader` loads `*.openapi.json` files
- Both are automatically mounted by `MCPProxyServer`

## Testing the Naming Convention

### Test Case 1: Valid Files Only

```bash
# Create valid OpenAPI files
echo '{"openapi":"3.0.0","info":{"title":"API1","version":"1.0"},"servers":[{"url":"https://api1.com"}],"paths":{}}' > data/api1.openapi.json
echo '{"openapi":"3.0.0","info":{"title":"API2","version":"1.0"},"servers":[{"url":"https://api2.com"}],"paths":{}}' > data/api2.openapi.json

# Start server
python -m src.main

# Expected: Both files loaded
# Output: "Found 2 OpenAPI configuration file(s)"
```

### Test Case 2: Mixed Valid and Invalid

```bash
# Create files
echo '...' > data/valid.openapi.json
echo '...' > data/invalid.json
echo '...' > data/openapi.json

# Start server
python -m src.main

# Expected: Only valid.openapi.json loaded
# Others ignored
```

## Implementation Guarantee

✅ **Guarantee**: Only files matching the `*.openapi.json` pattern will be loaded.

- Glob pattern enforces exact matching: `*.openapi.json`
- Namespace validation ensures no empty namespaces
- Invalid files are logged and skipped
- Processing continues with valid files

## Related Documentation

- `OPENAPI_LOADER_GUIDE.md` - Full documentation
- `QUICKREF_OPENAPI.md` - Quick reference
- `EXAMPLES_OPENAPI_LOADER.py` - Code examples
- `OPENAPI_IMPLEMENTATION_SUMMARY.md` - Implementation details

