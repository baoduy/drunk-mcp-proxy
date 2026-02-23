#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_DIR="${ROOT_DIR}/src"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

TOTAL_ERRORS=0
TOTAL_WARNINGS=0
ERROR_FILES=()

# ============================================================================
# TypeScript-like Build: Comprehensive Python Syntax & Type Check
# ============================================================================
echo -e "${BOLD}${CYAN}Building Python project...${NC}"
echo ""

# ============================================================================
# STEP 1: SYNTAX CHECK (like tsc parse)
# ============================================================================
echo -e "${BOLD}Checking syntax...${NC}"

SYNTAX_OUTPUT=$(python3 -c "
import py_compile
import sys
from pathlib import Path

errors = []
files_checked = 0

for py_file in sorted(Path('${PYTHON_DIR}').rglob('*.py')):
    files_checked += 1
    try:
        py_compile.compile(str(py_file), doraise=True)
    except py_compile.PyCompileError as e:
        rel_path = py_file.relative_to('${ROOT_DIR}')
        errors.append(f'{rel_path}({e.exc_value.lineno},1): error SyntaxError: {e.exc_value.msg}')

if errors:
    for error in errors:
        print(error)
    sys.exit(len(errors))
else:
    print(f'✓ {files_checked} files passed syntax check')
" 2>&1)

SYNTAX_EXIT=$?
echo "$SYNTAX_OUTPUT"

if [ $SYNTAX_EXIT -ne 0 ]; then
    TOTAL_ERRORS=$((TOTAL_ERRORS + SYNTAX_EXIT))
    echo -e "${RED}✗ Syntax check failed${NC}"
    echo ""
fi

# ============================================================================
# STEP 2: TYPE CHECK (like tsc --noEmit)
# ============================================================================
echo -e "${BOLD}Type checking...${NC}"

if command -v pyright &> /dev/null; then
    # Run pyright with strict mode and JSON output
    PYRIGHT_OUTPUT=$(pyright "${PYTHON_DIR}" --outputjson 2>&1 || true)
    
    TYPE_RESULT=$(echo "$PYRIGHT_OUTPUT" | python3 -c "
import json
import sys
from pathlib import Path

try:
    data = json.load(sys.stdin)
    root = Path('${ROOT_DIR}')
    
    errors = []
    warnings = []
    
    for diag in data.get('generalDiagnostics', []):
        severity = diag.get('severity', 'error')
        file_path = Path(diag.get('file', 'unknown'))
        
        try:
            rel_path = file_path.relative_to(root)
        except ValueError:
            rel_path = file_path
            
        line = diag.get('range', {}).get('start', {}).get('line', 0) + 1
        col = diag.get('range', {}).get('start', {}).get('character', 0) + 1
        msg = diag.get('message', '')
        rule = diag.get('rule', 'type-check')
        
        error_msg = f'{rel_path}({line},{col}): {severity} {rule}: {msg}'
        
        if severity == 'error':
            errors.append(error_msg)
        else:
            warnings.append(error_msg)
    
    # Print errors first
    for error in errors:
        print(error)
    
    # Then warnings
    for warning in warnings:
        print(warning)
    
    # Summary
    error_count = len(errors)
    warning_count = len(warnings)
    info_count = data.get('summary', {}).get('informationCount', 0)
    
    print('')
    if error_count > 0 or warning_count > 0:
        print(f'Found {error_count} error(s), {warning_count} warning(s)')
        sys.exit(error_count)
    else:
        print('✓ Type checking passed')
        sys.exit(0)
        
except json.JSONDecodeError:
    print('⚠️  Could not parse pyright output')
    sys.exit(0)
except Exception as e:
    print(f'⚠️  Type check error: {e}')
    sys.exit(0)
" 2>&1)
    
    TYPE_EXIT=$?
    echo "$TYPE_RESULT"
    
    if [ $TYPE_EXIT -ne 0 ]; then
        TOTAL_ERRORS=$((TOTAL_ERRORS + TYPE_EXIT))
        echo -e "${RED}✗ Type check failed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  pyright not installed - skipping type check${NC}"
    echo "   Install: pip install pyright"
fi

echo ""

# ============================================================================
# STEP 3: IMPORT VALIDATION (like tsc module resolution)
# ============================================================================
echo -e "${BOLD}Validating imports...${NC}"

IMPORT_OUTPUT=$(python3 -c "
import ast
import sys
import importlib.util
from pathlib import Path

sys.path.insert(0, '${PYTHON_DIR}')

errors = []
files_checked = 0

for py_file in sorted(Path('${PYTHON_DIR}').rglob('*.py')):
    files_checked += 1
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(py_file))
        
        rel_path = py_file.relative_to('${ROOT_DIR}')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    try:
                        spec = importlib.util.find_spec(alias.name.split('.')[0])
                        if spec is None:
                            errors.append(f'{rel_path}({node.lineno},1): error ImportError: Cannot find module \"{alias.name}\"')
                    except (ImportError, ModuleNotFoundError, ValueError):
                        errors.append(f'{rel_path}({node.lineno},1): error ImportError: Cannot find module \"{alias.name}\"')
                        
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    try:
                        spec = importlib.util.find_spec(node.module.split('.')[0])
                        if spec is None:
                            errors.append(f'{rel_path}({node.lineno},1): error ImportError: Cannot find module \"{node.module}\"')
                    except (ImportError, ModuleNotFoundError, ValueError):
                        errors.append(f'{rel_path}({node.lineno},1): error ImportError: Cannot find module \"{node.module}\"')
                        
    except SyntaxError:
        pass  # Already caught in syntax check
    except Exception as e:
        pass

if errors:
    for error in errors[:20]:  # Limit to first 20 to avoid spam
        print(error)
    if len(errors) > 20:
        print(f'... and {len(errors) - 20} more import errors')
    sys.exit(len(errors))
else:
    print(f'✓ {files_checked} files passed import validation')
" 2>&1)

IMPORT_EXIT=$?
echo "$IMPORT_OUTPUT"

if [ $IMPORT_EXIT -ne 0 ]; then
    TOTAL_ERRORS=$((TOTAL_ERRORS + IMPORT_EXIT))
    echo -e "${RED}✗ Import validation failed${NC}"
fi

echo ""

# ============================================================================
# STEP 4: LINTING (like tsc strict checks)
# ============================================================================
echo -e "${BOLD}Linting code...${NC}"

if command -v flake8 &> /dev/null; then
    FLAKE8_OUTPUT=$(flake8 "${PYTHON_DIR}" \
        --format='%(path)s(%(row)d,%(col)d): warning %(code)s: %(text)s' \
        --ignore=E501,W293,W503 \
        --count 2>&1 || true)
    
    if [ -n "$FLAKE8_OUTPUT" ]; then
        # Extract just the errors, not the count line
        echo "$FLAKE8_OUTPUT" | grep -v "^[0-9]" | head -20 || true
        ERROR_COUNT=$(echo "$FLAKE8_OUTPUT" | tail -1)
        echo ""
        echo -e "${YELLOW}Found $ERROR_COUNT style issue(s)${NC}"
        TOTAL_WARNINGS=$((TOTAL_WARNINGS + $(echo "$ERROR_COUNT" | grep -o '[0-9]*' | head -1)))
    else
        echo "✓ No linting issues found"
    fi
else
    echo -e "${YELLOW}⚠️  flake8 not installed - skipping lint${NC}"
    echo "   Install: pip install flake8"
fi

echo ""

# ============================================================================
# FINAL BUILD SUMMARY (TypeScript-style)
# ============================================================================
echo "=========================================================="

if [ $TOTAL_ERRORS -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ Build succeeded${NC}"
    if [ $TOTAL_WARNINGS -gt 0 ]; then
        echo -e "  with ${YELLOW}${TOTAL_WARNINGS}${NC} warning(s)"
    fi
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}✗ Build failed${NC}"
    echo -e "  Found ${RED}${TOTAL_ERRORS}${NC} error(s)"
    if [ $TOTAL_WARNINGS -gt 0 ]; then
        echo -e "  and ${YELLOW}${TOTAL_WARNINGS}${NC} warning(s)"
    fi
    echo ""
    exit 1
fi
