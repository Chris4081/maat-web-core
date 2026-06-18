import os

from backend.server import run_server


if __name__ == "__main__":
    host = os.environ.get("MAAT_WEB_HOST", "127.0.0.1").strip() or "127.0.0.1"
    try:
        port = int(os.environ.get("MAAT_WEB_PORT", "8787"))
    except ValueError:
        port = 8787
    run_server(host=host, port=port)
