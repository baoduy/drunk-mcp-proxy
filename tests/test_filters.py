#!/usr/bin/env python3
"""Test script for filters functionality in SpecConfig"""

import os

# Set required environment variables before importing SpecConfig
# These are needed when loading config.json with environment variable references
os.environ.setdefault('AZURE_CLIENT_ID', 'test-client-id')
os.environ.setdefault('AZURE_CLIENT_SECRET', 'test-secret')
os.environ.setdefault('AZURE_TENANT_ID', 'test-tenant')

from tools.spec_config import SpecConfig

# Test 1: Create a config with filters
print("Test 1: Creating config with filters...")
config_dict = {
    "path": "/test-api",
    "spec_file": "test.json",
    "spec_type": "openapi",
    "base_url": "https://api.example.com",
    "filters": {
        "methods": ["GET", "POST"],
        "tags": ["public", "v1"]
    }
}

config = SpecConfig.model_validate(config_dict)
print(f"✓ Path: {config.path}")
print(f"✓ Filters.methods: {config.filters.methods}")
print(f"✓ Filters.tags: {config.filters.tags}")
assert config.filters is not None
assert config.filters.methods == ["GET", "POST"]
assert config.filters.tags == ["public", "v1"]

# Test 2: Create a config without filters
print("\nTest 2: Creating config without filters...")
config_dict2 = {
    "path": "/test-api-2",
    "spec_file": "test2.json",
    "spec_type": "mcp"
}

config2 = SpecConfig.model_validate(config_dict2)
print(f"✓ Path: {config2.path}")
print(f"✓ Filters: {config2.filters}")
assert config2.filters is None

# Test 3: Filters with only methods
print("\nTest 3: Creating config with only methods filter...")
config_dict3 = {
    "path": "/test-api-3",
    "spec_file": "test3.json",
    "spec_type": "openapi",
    "base_url": "https://api.example.com",
    "filters": {
        "methods": ["DELETE"]
    }
}

config3 = SpecConfig.model_validate(config_dict3)
print(f"✓ Path: {config3.path}")
print(f"✓ Filters.methods: {config3.filters.methods}")
print(f"✓ Filters.tags: {config3.filters.tags}")
assert config3.filters is not None
assert config3.filters.methods == ["DELETE"]
assert config3.filters.tags is None

# Test 4: Filters with only tags
print("\nTest 4: Creating config with only tags filter...")
config_dict4 = {
    "path": "/test-api-4",
    "spec_file": "test4.json",
    "spec_type": "openapi",
    "base_url": "https://api.example.com",
    "filters": {
        "tags": ["internal"]
    }
}

config4 = SpecConfig.model_validate(config_dict4)
print(f"✓ Path: {config4.path}")
print(f"✓ Filters.methods: {config4.filters.methods}")
print(f"✓ Filters.tags: {config4.filters.tags}")
assert config4.filters is not None
assert config4.filters.methods is None
assert config4.filters.tags == ["internal"]

# Test 5: Load from actual config.json
print("\nTest 5: Loading from config.json...")
configs = SpecConfig.load_from_file("data/config.json")
deepsea_config = next((c for c in configs if c.path == "/deepsea"), None)
assert deepsea_config is not None
assert deepsea_config.filters is not None
assert deepsea_config.filters.methods == ["GET", "POST", "PUT"]
assert deepsea_config.filters.tags == ["CurrencyPairs"]
print(
    f"✓ Loaded deepsea config with filters: methods={deepsea_config.filters.methods}, tags={deepsea_config.filters.tags}")

print("\n=== All Filters Tests Passed! ===")
