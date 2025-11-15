
import sys
from pathlib import Path

# hack to allow importing from backend directory
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Now import
import search, ocr

if __name__ == "__main__":
    search.run_tests()
    ocr.run_tests()