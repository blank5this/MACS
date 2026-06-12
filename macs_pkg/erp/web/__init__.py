"""ERP web UI: FastAPI app + static frontend."""

from .app import app, create_app

__all__ = ["app", "create_app"]
