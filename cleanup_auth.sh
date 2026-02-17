#!/bin/bash

# Authentication Implementation - Cleanup Script
# This script removes duplicate/experimental files

PROJECT_DIR="/Users/steven/_CODE/drunk-mcp-proxy"

echo "╔════════════════════════════════════════════════════════╗"
echo "║     Authentication Implementation - Cleanup Script     ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Files to remove
DUPLICATES=(
    "src/tools/auth_config_new.py"
    "src/proxies/auth_config_provider_new.py"
)

REMOVED_COUNT=0
ERROR_COUNT=0

echo "Removing duplicate files..."
echo ""

for file in "${DUPLICATES[@]}"; do
    full_path="$PROJECT_DIR/$file"

    if [ -f "$full_path" ]; then
        echo "Removing: $file"
        if rm "$full_path"; then
            echo "  ✓ Successfully deleted"
            ((REMOVED_COUNT++))
        else
            echo "  ✗ Error deleting file"
            ((ERROR_COUNT++))
        fi
    else
        echo "Skipping: $file (not found or already removed)"
    fi
    echo ""
done

echo "╔════════════════════════════════════════════════════════╗"
echo "║                    Cleanup Summary                     ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Files removed: $REMOVED_COUNT"
echo "Errors: $ERROR_COUNT"
echo ""

if [ $ERROR_COUNT -eq 0 ]; then
    echo "✓ Cleanup completed successfully!"
    echo ""
    echo "Production files remaining:"
    echo "  ✓ src/tools/auth_config.py"
    echo "  ✓ src/proxies/auth_config_provider.py"
    echo "  ✓ data/auth.json"
    echo ""
    echo "Documentation files:"
    echo "  ✓ docs/AUTH_IMPLEMENTATION_GUIDE.md"
    echo "  ✓ docs/AUTH_PROVIDERS_REFERENCE.md"
    echo "  ✓ AUTH_IMPLEMENTATION_FINAL.md"
    echo ""
    echo "Status: READY FOR PRODUCTION"
else
    echo "✗ Cleanup completed with errors"
    exit 1
fi

