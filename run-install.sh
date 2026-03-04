#!/bin/bash
# Installation script for drunk-ai-proxy development environment

set -e

echo "📦 Installing drunk-ai-proxy in editable mode..."
echo ""

# Upgrade pip, setuptools, and wheel first
echo "⬆️  Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

echo ""
echo "📥 Installing drunk-ai-proxy with dev dependencies..."
pip install -e '.[dev]' --upgrade --upgrade-strategy eager

echo ""
echo "✅ Installation complete!"
echo ""
echo "💡 You can now:"
echo "   • Run the server: drunk-ai-proxy"
echo "   • Run via module: python -m drunk_ai_proxy"
echo "   • Run tests: ./run-test.sh"
echo "   • Build package: ./run-build.sh"
echo ""