"""Manual QA-only, local read probe. Credentials must come from the environment."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.qa_http import certificate_probe

if __name__ == '__main__':
    certificate_probe()
