#!/usr/bin/env python3
"""Simple test runner to verify all tests pass."""

import subprocess
import sys


def run_tests():
    """Run all tests using pytest."""
    print("=" * 70)
    print("Running Unit Tests for OauthAsyncClient")
    print("=" * 70)

    # Run tests with verbose output
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd="/Users/steven/_CODE/drunk-mcp-proxy"
    )

    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
