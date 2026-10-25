"""Start the app:  python -m app [--port 8050] [--reload]   (from the repo root)."""

import argparse
import os
from pathlib import Path

import uvicorn

DEFAULT_PORT = int(os.environ.get("APP_PORT", 8050))

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"default {DEFAULT_PORT} (or set APP_PORT)")
parser.add_argument("--reload", action="store_true", help="restart automatically when code changes")
args = parser.parse_args()

print(f"Open http://{args.host}:{args.port}  (API docs: /docs)")
uvicorn.run(
    "api.main:app",
    app_dir=str(Path(__file__).resolve().parent),
    host=args.host,
    port=args.port,
    reload=args.reload,
)
