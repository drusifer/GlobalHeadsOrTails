# game_server container image (flip.globalheadsortails.com on pi-patch).
# Build context is the workspace root: game_server installs the sibling `shared`
# and `tag_validator_service` packages. Only those paths are sent to the build
# (see game_server/Dockerfile.dockerignore). Build with `make export-game-server-image`.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build
COPY shared/ shared/
COPY tag_validator_service/pyproject.toml tag_validator_service/README.md tag_validator_service/
COPY tag_validator_service/src/ tag_validator_service/src/
COPY game_server/pyproject.toml game_server/
COPY game_server/src/ game_server/src/

RUN pip install --no-cache-dir ./shared ./tag_validator_service ./game_server "gunicorn>=21.0.0" \
    && pip check \
    && rm -rf /build

# uid 1000 matches the owner of the existing app.db on darius.
RUN useradd -u 1000 -m appuser && mkdir -p /app/data && chown -R appuser:appuser /app
WORKDIR /app
USER appuser

EXPOSE 8000

# One worker: the game state lives in a single SQLite file (data/app.db, relative to /app).
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--worker-tmp-dir", "/tmp", "--access-logfile", "-", "game_server.app:app"]
