from pathlib import Path
import runpy
import sys
import traceback

# Run the package app and expose `app` for WSGI servers
BASE_DIR = Path(__file__).resolve().parent / "fake-account-detector"
sys.path.insert(0, str(BASE_DIR))

try:
    ns = runpy.run_path(str(BASE_DIR / "app.py"))
    app = ns.get("app")
    if app is None:
        raise RuntimeError("WSGI entrypoint could not find `app` in fake-account-detector/app.py")
except Exception:
    # Print traceback to stdout/stderr so Render/Gunicorn logs capture the error.
    traceback.print_exc()
    # Re-raise to ensure the process exits (so the deployment shows failure),
    # but the traceback will be visible in the logs for debugging.
    raise
