"""JSON API for the app, which also serves the web page.

  python -m app --reload        (from the repo root, port 8050; --port to change)

then open http://127.0.0.1:8050. API docs are at http://127.0.0.1:8050/docs.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.core import discharge, plants

app = FastAPI(title="Drought & heat impact on power plants")


@app.get("/api/plants")
def list_plants():
    return plants.load_plants().to_dict(orient="records")


@app.get("/api/sources")
def list_sources():
    return discharge.available_sources()


@app.get("/api/plants/{plant_id}/discharge")
def plant_discharge(plant_id: str, track: int | None = None):
    plant = plants.get_plant(plant_id)
    if plant is None:
        raise HTTPException(404, f"Unknown plant {plant_id}")
    keys = [k for k, s in discharge.SOURCES.items() if track is None or s["track"] == track]
    return dict(plant=plant, sources=[discharge.plant_series(k, plant["lat"], plant["lon"]) for k in keys])


# Mounted last so the /api routes take precedence.
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[1] / "web", html=True), name="web")
