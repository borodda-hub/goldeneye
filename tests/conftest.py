import sys
from pathlib import Path

# Add repo root so `apps.api.*` imports resolve in all test suites under tests/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
