# conftest.py — ensures the project root is on sys.path for all tests
import sys
from pathlib import Path

# Add repo root (parent of apps/, tests/) to sys.path so `from apps.` works
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
