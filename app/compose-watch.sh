#!/bin/sh
# Rebuild the image and restart the app whenever a file under app/ changes.
# For compose tools without `up --watch` support, such as podman-compose.
#
#   app/compose-watch.sh                        # uses `podman compose`
#   COMPOSE="docker compose" app/compose-watch.sh
#
# Run from the repository root. Stop with Ctrl+C (the container keeps running;
# stop it with `podman compose down`).

set -eu

COMPOSE=${COMPOSE:-podman compose}
INTERVAL=${INTERVAL:-2}

# Checksum of every watched file, so edits, new files and deletions all count.
snapshot() {
  find app -type f ! -path '*/__pycache__/*' ! -name '*.pyc' ! -path 'app/api/.env' \
    | sort | xargs cksum | cksum
}

rebuild() {
  echo "== $(date '+%H:%M:%S') rebuilding"
  $COMPOSE up --build -d || echo "== build failed; fix the error and save again"
}

rebuild
last=$(snapshot)
echo "== watching app/ (every ${INTERVAL}s), Ctrl+C to stop"
while sleep "$INTERVAL"; do
  now=$(snapshot)
  if [ "$now" != "$last" ]; then
    last=$now
    rebuild
  fi
done
