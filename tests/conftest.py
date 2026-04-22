"""Shared test fixtures."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")
os.environ.setdefault("DISCORD_TOKEN", "test-token-do-not-use")

