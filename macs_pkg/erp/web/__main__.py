"""One-command launcher for the local ERP AI Copilot demo.

Usage::

    python -m macs_pkg.erp.web                       # → http://127.0.0.1:7860
    python -m macs_pkg.erp.web --port 8001           # custom port
    python -m macs_pkg.erp.web --host 0.0.0.0        # expose on LAN
    python -m macs_pkg.erp.web --no-access-log       # quieter

Equivalent Make target::

    make demo         # background
    make demo-stop    # kill the running instance
    make demo-check   # health probe
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
import time
import webbrowser
from pathlib import Path

# Make project root importable when run from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m macs_pkg.erp.web",
        description="Run the MACS ERP AI Copilot web demo locally (FastAPI + uvicorn).",
    )
    p.add_argument("--host", default=os.getenv("MACS_DEMO_HOST", "127.0.0.1"),
                   help="bind host (default 127.0.0.1; use 0.0.0.0 to expose on LAN)")
    p.add_argument("--port", type=int, default=int(os.getenv("MACS_DEMO_PORT", "7860")),
                   help="bind port (default 7860 — matches the Gradio entry for parity)")
    p.add_argument("--no-access-log", action="store_true",
                   help="silence uvicorn per-request logs (keeps startup banner only)")
    p.add_argument("--reload", action="store_true",
                   help="enable auto-reload on code change (dev only)")
    p.add_argument("--open", action="store_true",
                   help="open the demo URL in the default browser on startup")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    # Lazy import so --help stays instant and import errors are surfaced
    # with the real stack trace instead of a one-line argparse complaint.
    import uvicorn  # noqa: WPS433 — intentional deferred import

    config = uvicorn.Config(
        "macs_pkg.erp.web.app:app",
        host=args.host,
        port=args.port,
        log_level="info" if not args.no_access_log else "warning",
        access_log=not args.no_access_log,
        reload=args.reload,
    )
    server = uvicorn.Server(config)

    url = f"http://{args.host}:{args.port}/"
    print("─" * 72)
    print(f"  MACS · ERP AI Copilot — local demo")
    print(f"  → {url}")
    print(f"  → Swagger UI:  http://{args.host}:{args.port}/docs")
    print(f"  → Health:      http://{args.host}:{args.port}/healthz")
    print(f"  Press Ctrl+C to stop.")
    print("─" * 72)

    if args.open:
        # Open the browser on a short delay so the server is ready first.
        import threading
        def _open() -> None:
            time.sleep(1.2)
            try:
                webbrowser.open(url)
            except Exception:  # noqa: BLE001 — browser-less environments are fine
                pass
        threading.Thread(target=_open, daemon=True).start()

    # Graceful shutdown on Ctrl+C (Windows + POSIX compatible).
    def _sigint(_signum, _frame):  # noqa: ANN001
        server.should_exit = True
    try:
        signal.signal(signal.SIGINT, _sigint)
    except (ValueError, AttributeError):
        pass  # not on main thread / non-POSIX — uvicorn handles it itself

    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
