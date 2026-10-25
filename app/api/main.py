"""JSON API for the app, which also serves the web page.

  python -m app --reload        (from the repo root, port 8050; --port to change)

then open http://127.0.0.1:8050. API docs are at http://127.0.0.1:8050/docs.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routes import router
from api.logger import setup_logging

setup_logging()

app = FastAPI(title="Drought & heat impact on power plants")

app.include_router(router)

# Mounted last so the /api routes take precedence.
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[1] / "web", html=True), name="web")
