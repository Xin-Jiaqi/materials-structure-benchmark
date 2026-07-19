#!/usr/bin/env python3
"""Compatibility wrapper for source-checkout catalog queries."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from materials_structure_benchmark.query import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
