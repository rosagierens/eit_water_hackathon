# Running the app with Docker

The image holds the web app (FastAPI backend and the static MapLibre/Plotly page) and the
application-ready data from `data/app_input/`. Nothing from the data pipeline is installed,
so the image stays small.

Run every command below from the **repository root**, not from `app/`: the build needs both
`app/` and `data/app_input/`.

## Quick start (Docker Compose)

```bash
docker compose up --build
```

Open http://localhost:8050. The API docs are at http://localhost:8050/docs.
The log line `Open http://0.0.0.0:8050` is the address inside the container; use `localhost` in
your browser.

Stop with `Ctrl+C`, or run in the background with `docker compose up --build -d` and stop with
`docker compose down`.

To use another port on your machine:

```bash
APP_PORT=8060 docker compose up --build      # then open http://localhost:8060
```

## Without Compose

```bash
docker build -f app/Dockerfile -t cooling-water-risk .
docker run --rm -p 8050:8050 cooling-water-risk
```

This uses the data copied into the image at build time. To use the data on your machine
instead, mount it:

```bash
docker run --rm -p 8050:8050 \
  -v "$(pwd)/data/app_input:/src/data/app_input:ro" \
  cooling-water-risk
```

## Updating the data

`compose.yaml` mounts `./data/app_input` into the container read-only, so the container
always reads the files on your machine. After rebuilding the data with the pipeline
(`data_processing/plants/run_pipeline.py`, `data_processing/environment/build_all.py`),
restart the app; no new image is needed:

```bash
docker compose restart
```

A restart is required because the app reads each table once and keeps it in memory.

If you run without the mount, rebuild the image (`docker compose build` or `docker build ...`)
to pick up new data.

## Updating the code

Changes in `app/` need a new image:

```bash
docker compose up --build
```

For day-to-day development, running locally with auto-reload is faster:
`python -m app --reload` (see `README.md`).

## Configuration

The settings that `app/api/.env` holds for local runs are set as environment variables in
`app/Dockerfile`. `.env` is never copied into the image. Override any of them at run time:

| Variable | Default in the image | Meaning |
| --- | --- | --- |
| `APP_NAME` | `EIT-Water-Hackathon` | Application name |
| `APP_ENV` | `production` | Environment name |
| `FACILITIES_CSV` | `data/app_input/facilities.csv` | Plant table |
| `RAW_DISCHARGE_DATA` | `data/app_input/environment/discharge.parquet` | River discharge table |
| `WATER_TEMPERATURE_DATA` | `data/app_input/environment/water_temperature.parquet` | Water temperature table |

Paths are relative to the repository root, which is `/srv` in the container. Example:

```bash
docker run --rm -p 8050:8050 -e APP_ENV=staging cooling-water-risk
```

With Compose, add them under `environment:` in `compose.yaml`.

The forecast window ("from two days before today") uses the container's clock, which is UTC.

## What is in the image

| Path in the container | From |
| --- | --- |
| `/src/app/` | `app/` (without `__pycache__` and `app/api/.env`) |
| `/src/data/app_input/` | `data/app_input/` |

- Base image: `python:3.12-slim`, matching `.python-version`.
- Python packages: `app/requirements.txt`, the app's runtime subset of the root
  `requirements.txt`. Keep shared version pins identical in both files.
- `.dockerignore` at the repository root excludes everything else (raw and interim data,
  the pipeline, virtual environments, git history).
- The app runs as an unprivileged user on port 8050. A health check calls `/api/plants`
  every 30 s; `docker ps` shows the container as `healthy` once the plant table loads.

## Internet access

The page loads MapLibre GL JS and Plotly from cdn.jsdelivr.net, and the basemap tiles from
tiles.openfreemap.org. The **browser** needs internet access for these; the container does not.

## Troubleshooting

- **Port already in use:** start with another port, `APP_PORT=8060 docker compose up`.
- **The map shows but there are no plants, or the container is `unhealthy`:** check the logs with
  `docker compose logs app`. A missing or renamed file in `data/app_input/` is the usual cause;
  the error names the path it looked for.
- **`permission denied` reading the mounted data:** the app runs as a non-root user and needs
  read access to the files in `data/app_input/` (`chmod -R a+rX data/app_input`).
- **Old page after an update:** hard-refresh the browser (Ctrl+Shift+R) to drop cached JS and CSS.
