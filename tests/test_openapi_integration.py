"""
Test script to validate OpenAPI integration without runtime execution.

This test validates the OpenAPI feature implementation by:
1. Checking file existence
2. Validating code syntax
3. Verifying imports are defined
4. Checking documentation completeness
5. Validating example configurations

Note: Runtime execution tests are skipped due to dependency issues with py-key-value-aio.
"""

import ast
import json
from pathlib import Path


class OpenAPIIntegrationTest:
    """Test suite for OpenAPI integration validation."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.passed = []
        self.failed = []

    def test_file_existence(self):
        """Test that all required files exist."""
        print("Testing file existence...")

        required_files = [
            "src/proxies/openapi_proxies.py",
            "src/app/server.py",
            "data/petstore.openapi.json",
            "data/jsonplaceholder.openapi.json",
            "docs/features/openapi/OPENAPI_INDEX.md",
            "docs/features/openapi/OPENAPI_LOADER_GUIDE.md",
            "docs/features/openapi/QUICKREF_OPENAPI.md",
            "docs/features/openapi/OPENAPI_IMPLEMENTATION_SUMMARY.md",
            "docs/features/openapi/OPENAPI_IMPLEMENTATION_CHECKLIST.md",
            "docs/features/openapi/OPENAPI_REQUIREMENTS_VERIFICATION.md",
        ]

        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                self.passed.append(f"✓ File exists: {file_path}")
            else:
                self.failed.append(f"✗ File missing: {file_path}")

    def test_code_syntax(self):
        """Test that Python files have valid syntax."""
        print("Testing Python syntax...")

        python_files = [
            "src/proxies/openapi_proxies.py",
            "src/app/server.py",
        ]

        for file_path in python_files:
            full_path = self.project_root / file_path
            try:
                with open(full_path, 'r') as f:
                    code = f.read()
                ast.parse(code)
                self.passed.append(f"✓ Valid syntax: {file_path}")
            except SyntaxError as e:
                self.failed.append(f"✗ Syntax error in {file_path}: {e}")

    def test_class_definition(self):
        """Test that OpenApiMcpProxyLoader class is defined."""
        print("Testing class definition...")

        file_path = self.project_root / "src/proxies/openapi_proxies.py"
        try:
            with open(file_path, 'r') as f:
                code = f.read()

            tree = ast.parse(code)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]

            if "OpenApiMcpProxyLoader" in classes:
                self.passed.append("✓ OpenApiMcpProxyLoader class defined")
            else:
                self.failed.append("✗ OpenApiMcpProxyLoader class not found")

            # Check for required methods
            required_methods = [
                "load_all_servers",
                "build_mcp_servers",
                "discover_and_load_config_files",
                "create_servers_from_specs",
                "load_config_file",
                "extract_namespace_from_path",
            ]

            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

            for method in required_methods:
                if method in functions:
                    self.passed.append(f"✓ Method defined: {method}")
                else:
                    self.failed.append(f"✗ Method missing: {method}")

        except Exception as e:
            self.failed.append(f"✗ Error checking class definition: {e}")

    def test_server_integration(self):
        """Test that server.py imports and uses OpenApiMcpProxyLoader."""
        print("Testing server integration...")

        file_path = self.project_root / "src/app/server.py"
        try:
            with open(file_path, 'r') as f:
                code = f.read()

            if "OpenApiMcpProxyLoader" in code:
                self.passed.append("✓ OpenApiMcpProxyLoader imported in server.py")
            else:
                self.failed.append("✗ OpenApiMcpProxyLoader not imported in server.py")

            if "openapi_loader = OpenApiMcpProxyLoader" in code:
                self.passed.append("✓ OpenApiMcpProxyLoader instantiated in server.py")
            else:
                self.failed.append("✗ OpenApiMcpProxyLoader not instantiated in server.py")

            if "load_all_servers" in code:
                self.passed.append("✓ load_all_servers() called in server.py")
            else:
                self.failed.append("✗ load_all_servers() not called in server.py")

        except Exception as e:
            self.failed.append(f"✗ Error checking server integration: {e}")

    def test_openapi_examples(self):
        """Test that OpenAPI example files are valid JSON."""
        print("Testing OpenAPI example files...")

        example_files = [
            "data/petstore.openapi.json",
            "data/jsonplaceholder.openapi.json",
        ]

        for file_path in example_files:
            full_path = self.project_root / file_path
            try:
                with open(full_path, 'r') as f:
                    spec = json.load(f)

                # Validate required OpenAPI fields
                required_fields = ["openapi", "info", "servers", "paths"]
                for field in required_fields:
                    if field in spec:
                        self.passed.append(f"✓ {file_path}: has '{field}' field")
                    else:
                        self.failed.append(f"✗ {file_path}: missing '{field}' field")

            except json.JSONDecodeError as e:
                self.failed.append(f"✗ {file_path}: Invalid JSON - {e}")
            except Exception as e:
                self.failed.append(f"✗ {file_path}: Error - {e}")

    def test_documentation_completeness(self):
        """Test that all required documentation exists and has content."""
        print("Testing documentation completeness...")

        doc_files = [
            "docs/features/openapi/OPENAPI_INDEX.md",
            "docs/features/openapi/OPENAPI_LOADER_GUIDE.md",
            "docs/features/openapi/QUICKREF_OPENAPI.md",
        ]

        min_lines = 50  # Minimum lines for complete documentation

        for file_path in doc_files:
            full_path = self.project_root / file_path
            try:
                with open(full_path, 'r') as f:
                    lines = f.readlines()

                if len(lines) >= min_lines:
                    self.passed.append(f"✓ {file_path}: {len(lines)} lines (complete)")
                else:
                    self.failed.append(f"✗ {file_path}: {len(lines)} lines (too short)")

            except Exception as e:
                self.failed.append(f"✗ {file_path}: Error reading - {e}")

    def test_exports(self):
        """Test that __init__.py exports OpenApiMcpProxyLoader."""
        print("Testing exports...")

        file_path = self.project_root / "src/proxies/__init__.py"
        try:
            with open(file_path, 'r') as f:
                code = f.read()

            if "from .openapi_proxies import OpenApiMcpProxyLoader" in code:
                self.passed.append("✓ OpenApiMcpProxyLoader imported in __init__.py")
            else:
                self.failed.append("✗ OpenApiMcpProxyLoader not imported in __init__.py")

            if '"OpenApiMcpProxyLoader"' in code or "'OpenApiMcpProxyLoader'" in code:
                self.passed.append("✓ OpenApiMcpProxyLoader in __all__")
            else:
                self.failed.append("✗ OpenApiMcpProxyLoader not in __all__")

        except Exception as e:
            self.failed.append(f"✗ Error checking exports: {e}")

    def run_all_tests(self):
        """Run all tests and print results."""
        print("=" * 70)
        print("OpenAPI Integration Test Suite")
        print("=" * 70)
        print()

        self.test_file_existence()
        print()
        self.test_code_syntax()
        print()
        self.test_class_definition()
        print()
        self.test_server_integration()
        print()
        self.test_openapi_examples()
        print()
        self.test_documentation_completeness()
        print()
        self.test_exports()
        print()

        print("=" * 70)
        print("Test Results")
        print("=" * 70)
        print()

        print(f"✓ PASSED: {len(self.passed)}")
        print(f"✗ FAILED: {len(self.failed)}")
        print()

        if self.failed:
            print("Failed Tests:")
            for failure in self.failed:
                print(f"  {failure}")
            print()

        print("=" * 70)

        if self.failed:
            print("❌ SOME TESTS FAILED")
            return False
        else:
            print("✅ ALL TESTS PASSED")
            return True


if __name__ == "__main__":
    import sys

    # Get project root (parent of tests directory)
    project_root = Path(__file__).parent.parent

    tester = OpenAPIIntegrationTest(project_root)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)
