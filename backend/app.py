"""Compatibility entrypoint.

MAAT Web Core currently uses the standard-library HTTP server in `backend.server`
to avoid FastAPI/Pydantic version conflicts on local systems.
"""

from .server import run_server


if __name__ == "__main__":
    run_server()

