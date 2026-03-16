#!/bin/bash
# Installation script for drunk-ai-proxy development environment

set -e

echo "📦 Building and installing all src pyproject packages..."
echo ""

# Upgrade pip, setuptools, wheel, and build first
echo "⬆️  Upgrading pip, setuptools, wheel, and build..."
pip install --upgrade pip setuptools wheel build

echo ""
echo "🔍 Discovering pyproject.toml files under src/..."

source .venv/bin/activate

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

	echo ""
	echo "🧹 Cleaning dist for ${project_name}..."
	rm -rf "${project_dir}/dist"

	# echo "🏗️  Building ${project_name}..."
	# python -m build "$project_dir"

	echo "📥 Installing ${project_name} in editable mode..."
	pip install -e "$project_dir" --upgrade --upgrade-strategy eager
done

echo ""
echo "✅ Install complete for all src packages!"
echo ""
echo "💡 You can now run tests with: ./run-test.sh"
echo ""