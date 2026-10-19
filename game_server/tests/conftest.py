import sys
from pathlib import Path
import pytest

# Ensure tests root and src are on sys.path
_tests_dir = Path(__file__).parent
_root_dir = _tests_dir.parent
for p in [str(_tests_dir), str(_root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)
