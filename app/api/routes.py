from fastapi import HTTPException, APIRouter

from api.core import discharge, plants

router = APIRouter()

@router.get("/api/plants")
def list_plants():
    return plants.load_plants().to_dict(orient="records")


@router.get("/api/sources")
def list_sources():
    return discharge.available_sources()


@router.get("/api/plants/{id}/discharge", responses={404: {"description": "Unkown plant"}})
def plant_discharge(id: str, track: int | None = None):
    """Power plant discharge 
 
    Args:
        id: The plant id
        track: Future or current
 
    Returns:
        dict of the plants
    """
    plant = plants.get_plant(id)
    if plant is None:
        raise HTTPException(status_code=404, detail=f"Unknown plant {id}")
 
    return {
        "plant": plant,
        "sources": discharge.plant_sources(plant["id"], track),
    }
