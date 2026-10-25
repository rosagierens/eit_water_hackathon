from pathlib import Path
from api.config import get_settings

_DEFAULT_REPO = Path(__file__).resolve().parents[2]


def get_path(name: str) -> Path:
    """Return the path stored in settings.<name>, resolved against the repo root.

    Absolute paths are used as-is. Raises AttributeError if the setting doesn't exist
    and ValueError if it's empty.
    """
    settings = get_settings()
    value = getattr(settings, name)
    if not value:
        raise ValueError(f"Setting {name!r} is not set")

    repo = Path(_DEFAULT_REPO)
    return repo / value