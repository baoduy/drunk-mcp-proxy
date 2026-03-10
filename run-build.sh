#!/bin/bash
# Build script for drunk-ai-proxy package

set -e

echo "🔨 Building drunk-ai-proxy package..."
echo ""

# Install the build tool
echo "📦 Installing build dependencies..."
pip install --upgrade build pip setuptools wheel

echo ""
echo "✅ Build dependencies installed"
echo ""

# Clean previous build artifacts
echo "🧹 Cleaning dist folder..."
rm -rf src/drunk_ai_proxy/dist

echo ""
echo "✅ Dist folder cleaned"
echo ""

# Run the build
echo "🏗️  Building package..."
python -m build src/drunk_ai_proxy

echo ""
echo "✅ Build complete!"
echo ""
echo "📦 Built packages:"
ls -lh src/drunk_ai_proxy/dist/
echo ""
echo "💡 Install locally: pip install src/drunk_ai_proxy/dist/drunk_ai_proxy-*.whl"
echo "💡 Test with uvx: uvx --from src/drunk_ai_proxy/dist/drunk_ai_proxy-*.whl drunk-ai-proxy"