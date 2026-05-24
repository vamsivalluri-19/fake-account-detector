from pathlib import Path
import runpy
import sys


BASE_DIR = Path(__file__).resolve().parent / "fake-account-detector"
sys.path.insert(0, str(BASE_DIR))

runpy.run_path(str(BASE_DIR / "model.py"), run_name="__main__")