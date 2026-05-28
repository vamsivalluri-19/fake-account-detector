from pathlib import Path
import runpy
import sys

# Run the package app and expose `app` for WSGI servers
BASE_DIR = Path(__file__).resolve().parent / "fake-account-detector"
sys.path.insert(0, str(BASE_DIR))

ns = runpy.run_path(str(BASE_DIR / "app.py"))
app = ns.get("app")

if app is None:
    raise RuntimeError("WSGI entrypoint could not find `app` in fake-account-detector/app.py")
