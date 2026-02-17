"""Pytest configuration ensuring project imports resolve in tests."""

from __future__ import annotations

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

project_src = project_root / "src"
if str(project_src) not in sys.path:
    sys.path.insert(0, str(project_src))
