#!/bin/bash
# Build script for drunk-ai-proxy package

set -e

echo "🔨 Building all src pyproject packages..."
echo ""

# Install the build tool
echo "📦 Installing build dependencies..."
pip install --upgrade build pip setuptools wheel

echo ""
echo "✅ Build dependencies installed"
echo ""

ROOT_DIST="./dist"
echo "🧹 Cleaning root dist folder..."
rm -rf "$ROOT_DIST"

echo ""
echo "✅ Root dist folder cleaned"
echo ""

echo "🔍 Discovering pyproject.toml files under src/..."
PYPROJECTS=()
tmpfile=$(mktemp)
find ./src -maxdepth 3 -name pyproject.toml -print | sort > "$tmpfile"
while IFS= read -r pyproject; do
	[ -n "$pyproject" ] && PYPROJECTS+=("$pyproject")
done < "$tmpfile"
rm -f "$tmpfile"

if [ ${#PYPROJECTS[@]} -eq 0 ]; then
	echo "❌ No pyproject.toml files found under src/"
	exit 1
fi

for pyproject in "${PYPROJECTS[@]}"; do
	project_dir=$(dirname "$pyproject")
	project_name=$(basename "$project_dir")
	project_dist="${ROOT_DIST}/${project_name}"

	echo ""
	echo "🧹 Cleaning build artifacts for ${project_name}..."
	rm -rf "$project_dist"
	rm -rf "${project_dir}/build"
	rm -rf "${project_dir}/dist"
	rm -rf "${project_dir}"/*.egg-info

	echo "🏗️  Building ${project_name}..."
	python -m build "$project_dir" --outdir "$project_dist"

	echo "📦 Built packages for ${project_name}:"
	ls -lh "$project_dist/"
done

echo ""
echo "✅ Build complete for all src packages!"