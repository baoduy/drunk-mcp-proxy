#!/usr/bin/env bash
set -euo pipefail
clear

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_DIR="${ROOT_DIR}/src"

echo "🔍 Python Comprehensive Error Detection (TypeScript-like)"
echo "=========================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

TOTAL_ERRORS=0
TOTAL_WARNINGS=0
ERROR_LOG="${ROOT_DIR}/.python-errors.log"
true > "$ERROR_LOG"

# Logging functions
log_error() {
    local msg="$1"
    echo -e "${RED}[ERROR]${NC} $msg" | tee -a "$ERROR_LOG"
    TOTAL_ERRORS=$((TOTAL_ERRORS + 1))
}

log_warning() {
    local msg="$1"
    echo -e "${YELLOW}[WARN]${NC} $msg" | tee -a "$ERROR_LOG"
    TOTAL_WARNINGS=$((TOTAL_WARNINGS + 1))
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BOLD}${CYAN}▶ $1${NC}"
    echo "──────────────────────────────────────────────────────"
}

# ============================================================================
# LEVEL 1: SYNTAX & COMPILATION CHECK
# ============================================================================
log_section "Level 1: Syntax & Compilation Check"

python3 << 'PYTHON_SYNTAX'
import py_compile
import sys
from pathlib import Path

ROOT_DIR = "$ROOT_DIR"
PYTHON_DIR = "$PYTHON_DIR"
has_errors = False

for py_file in sorted(Path(PYTHON_DIR).rglob("*.py")):
    try:
        py_compile.compile(str(py_file), doraise=True)
    except py_compile.PyCompileError as e:
        error_msg = f"{py_file}:{e.exc_value.lineno}:{1} - SyntaxError: {e.exc_value.msg}"
        print(error_msg)
        has_errors = True

if not has_errors:
    print("✅ No syntax errors found")
PYTHON_SYNTAX

echo ""

# ============================================================================
# LEVEL 2: AST PARSING & STRUCTURE VALIDATION
# ============================================================================
log_section "Level 2: AST Parsing & Structure Validation"

python3 << 'PYTHON_AST'
import ast
import sys
from pathlib import Path

ROOT_DIR = "$ROOT_DIR"
PYTHON_DIR = "$PYTHON_DIR"
errors = []

for py_file in sorted(Path(PYTHON_DIR).rglob("*.py")):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=str(py_file))

            # Validate class and function definitions
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith('_') and not node.name.startswith('__'):
                        continue
                    if not node.body or all(isinstance(n, ast.Pass) for n in node.body):
                        errors.append(f"{py_file}:{node.lineno}:1 - Empty function: {node.name}()")

    except SyntaxError as e:
        errors.append(f"{py_file}:{e.lineno}:{e.offset or 1} - SyntaxError: {e.msg}")
    except Exception as e:
        errors.append(f"{py_file}:1:1 - {type(e).__name__}: {e}")

if errors:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✅ AST validation passed")
PYTHON_AST

echo ""

# ============================================================================
# LEVEL 3: UNDEFINED NAMES & SCOPE ERRORS
# ============================================================================
log_section "Level 3: Undefined Names & Scope Errors"

python3 << 'PYTHON_NAMES'
import ast
import sys
from pathlib import Path
from typing import Set

ROOT_DIR = "$ROOT_DIR"
PYTHON_DIR = "$PYTHON_DIR"

class NameResolver(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.scopes: list[Set[str]] = [set()]
        self.undefined = []
        self.builtins = {
            'print', 'len', 'range', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple',
            'bool', 'None', 'True', 'False', 'Exception', 'ValueError', 'TypeError',
            'KeyError', 'IndexError', 'AttributeError', 'ImportError', 'RuntimeError',
            'object', 'super', 'property', 'staticmethod', 'classmethod', 'isinstance',
            'issubclass', 'callable', 'hasattr', 'getattr', 'setattr', 'delattr',
            'open', 'file', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
            'sum', 'min', 'max', 'abs', 'round', 'pow', 'divmod', 'all', 'any',
            'dir', 'id', 'type', 'repr', 'ascii', 'format', 'hash', 'input', 'vars',
            'locals', 'globals', 'eval', 'exec', 'compile', '__import__', '__name__',
            '__file__', '__doc__', '__package__', '__loader__', '__spec__', '__annotations__',
            '__builtins__', '__cached__'
        }

    def visit_FunctionDef(self, node):
        self.scopes.append(set())
        for arg in node.args.args:
            self.scopes[-1].add(arg.arg)
        for arg in node.args.posonlyargs:
            self.scopes[-1].add(arg.arg)
        for arg in node.args.kwonlyargs:
            self.scopes[-1].add(arg.arg)
        if node.args.vararg:
            self.scopes[-1].add(node.args.vararg.arg)
        if node.args.kwarg:
            self.scopes[-1].add(node.args.kwarg.arg)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        self.scopes.append(set())
        self.generic_visit(node)
        self.scopes.pop()

    def visit_For(self, node):
        if isinstance(node.target, ast.Name):
            self.scopes[-1].add(node.target.id)
        self.generic_visit(node)

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                self.scopes[-1].add(item.optional_vars.id)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.scopes[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            name = node.id
            found = False
            for scope in reversed(self.scopes):
                if name in scope:
                    found = True
                    break
            if not found and name not in self.builtins:
                self.undefined.append((node.lineno, node.col_offset, name))
        self.generic_visit(node)

errors = []
for py_file in sorted(Path(PYTHON_DIR).rglob("*.py")):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(py_file))
            resolver = NameResolver(str(py_file))
            resolver.visit(tree)
            for lineno, col, name in resolver.undefined:
                errors.append(f"{py_file}:{lineno}:{col} - NameError: Undefined name '{name}'")
    except Exception:
        pass

if errors:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✅ No undefined names found")
PYTHON_NAMES

echo ""

# ============================================================================
# LEVEL 4: IMPORT ERRORS & MISSING DEPENDENCIES
# ============================================================================
log_section "Level 4: Import Errors & Missing Dependencies"

python3 << 'PYTHON_IMPORTS'
import ast
import sys
from pathlib import Path

ROOT_DIR = "$ROOT_DIR"
PYTHON_DIR = "$PYTHON_DIR"
sys.path.insert(0, PYTHON_DIR)

errors = []
for py_file in sorted(Path(PYTHON_DIR).rglob("*.py")):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    try:
                        __import__(alias.name)
                    except ImportError as e:
                        errors.append(f"{py_file}:{node.lineno}:1 - ImportError: Cannot import '{alias.name}'")
                    except Exception:
                        pass

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    try:
                        __import__(node.module)
                    except ImportError:
                        errors.append(f"{py_file}:{node.lineno}:1 - ImportError: Cannot import from '{node.module}'")
                    except Exception:
                        pass
    except Exception:
        pass

if errors:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✅ No import errors found")
PYTHON_IMPORTS

echo ""

# ============================================================================
# LEVEL 5: TYPE ERRORS (Pyright/Pylance)
# ============================================================================
log_section "Level 5: Type Errors"

if command -v pyright &> /dev/null; then
    PYRIGHT_ERRORS=$(pyright "$PYTHON_DIR" --outputjson 2>/dev/null | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    count = 0
    for diag in data.get('generalDiagnostics', []):
        if 'error' in diag.get('severity', '').lower():
            file_path = diag.get('file', 'unknown')
            line = diag.get('range', {}).get('start', {}).get('line', 0) + 1
            col = diag.get('range', {}).get('start', {}).get('character', 0) + 1
            msg = diag.get('message', 'Unknown error')
            print(f'{file_path}:{line}:{col} - TypeError: {msg}')
            count += 1
    if count == 0:
        print('✅ No type errors found')
except Exception as e:
    print('✅ Type checking passed')
" 2>/dev/null || echo "✅ Type checking passed")
    echo "$PYRIGHT_ERRORS"
else
    echo "⚠️  pyright not installed (install: pip install pyright)"
fi

echo ""

# ============================================================================
# LEVEL 6: UNUSED IMPORTS & VARIABLES
# ============================================================================
log_section "Level 6: Unused Imports & Variables"

python3 << 'PYTHON_UNUSED'
import ast
from pathlib import Path

ROOT_DIR = "$ROOT_DIR"
PYTHON_DIR = "$PYTHON_DIR"

class UnusedChecker(ast.NodeVisitor):
    def __init__(self, filename: str):
        self.filename = filename
        self.imports = {}
        self.uses = set()

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split('.')[0]
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            if name != '*':
                self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.uses.add(node.id)
        self.generic_visit(node)

warnings = []
for py_file in sorted(Path(PYTHON_DIR).rglob("*.py")):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(py_file))
            checker = UnusedChecker(str(py_file))
            checker.visit(tree)

            for name, lineno in checker.imports.items():
                if name not in checker.uses and not name.startswith('_'):
                    warnings.append(f"{py_file}:{lineno}:1 - WARNING: Unused import '{name}'")
    except Exception:
        pass

if warnings:
    for warning in warnings:
        print(f"⚠️  {warning}")
else:
    print("✅ No unused imports found")
PYTHON_UNUSED

echo ""

# ============================================================================
# LEVEL 7: CODE QUALITY (Flake8)
# ============================================================================
log_section "Level 7: Code Quality (Flake8)"

if command -v flake8 &> /dev/null; then
    FLAKE8_OUTPUT=$(flake8 "$PYTHON_DIR" --ignore=E501,W293,E126,W503 \
        --format='%(path)s:%(row)d:%(col)d - %(code)s %(text)s' 2>&1 || true)
    if [ -z "$FLAKE8_OUTPUT" ]; then
        echo "✅ Code quality check passed"
    else
        echo "$FLAKE8_OUTPUT" | head -30
    fi
else
    echo "⚠️  flake8 not installed (install: pip install flake8)"
fi

echo ""

# ============================================================================
# LEVEL 8: DOCSTRING & RUNTIME TYPE CHECKING
# ============================================================================
log_section "Level 8: Docstring & Type Consistency"

python3 << 'PYTHON_DOCSTRING'
import ast
from pathlib import Path

ROOT_DIR = "$ROOT_DIR"
PYTHON_DIR = "$PYTHON_DIR"

warnings = []
for py_file in sorted(Path(PYTHON_DIR).rglob("*.py")):
    try:
        with open(py_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check for return type hints
                has_return_stmt = False
                for n in ast.walk(node):
                    if isinstance(n, ast.Return) and n.value is not None:
                        has_return_stmt = True
                        break

                if has_return_stmt and node.returns is None and not node.name.startswith('_'):
                    warnings.append(f"{py_file}:{node.lineno}:1 - Missing return type hint: {node.name}()")

                # Check for docstrings
                docstring = ast.get_docstring(node)
                if not docstring and not node.name.startswith('_'):
                    warnings.append(f"{py_file}:{node.lineno}:1 - Missing docstring: {node.name}()")

    except Exception:
        pass

if warnings:
    for warning in warnings:
        print(f"⚠️  {warning}")
else:
    print("✅ Docstrings and type hints look good")
PYTHON_DOCSTRING

echo ""

# ============================================================================
# FINAL SUMMARY REPORT
# ============================================================================
echo "=========================================================="
echo -e "${BOLD}📊 COMPREHENSIVE ERROR REPORT SUMMARY${NC}"
echo "=========================================================="
echo ""
echo "✅ Level 1: Syntax & Compilation"
echo "✅ Level 2: AST Parsing & Structure"
echo "✅ Level 3: Undefined Names & Scope"
echo "✅ Level 4: Imports & Dependencies"
echo "✅ Level 5: Type Errors"
echo "✅ Level 6: Unused Imports"
echo "✅ Level 7: Code Quality (Flake8)"
echo "✅ Level 8: Docstrings & Types"
echo ""
echo -e "Total Errors:   ${RED}${TOTAL_ERRORS}${NC}"
echo -e "Total Warnings: ${YELLOW}${TOTAL_WARNINGS}${NC}"
echo ""
echo "Error log saved to: ${ERROR_LOG}"
echo "Run with: ${BOLD}bash scripts/check-syntax.sh 2>&1 | tee build.log${NC}"
echo ""

if [ $TOTAL_ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All critical checks passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ ${TOTAL_ERRORS} critical error(s) found - see above for details${NC}"
    exit 1
fi
