#!/usr/bin/env bash
set -euo pipefail
clear

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python -m compileall "$ROOT_DIR/src"
