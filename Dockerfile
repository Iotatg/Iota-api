FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    WEB_CONCURRENCY=4 \
    WEB_TIMEOUT=120 \
    WEB_MAX_REQUESTS=100000 \
    WEB_MAX_REQUESTS_JITTER=1000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates gcc libpq-dev ffmpeg nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip install --no-cache-dir "uvicorn[standard]" gunicorn

COPY app/ ./app/
COPY scripts/ ./scripts/
# The whole data directory is needed: songs.json holds the curated catalog the
# public routes serve, cached_tracks.json the offline fallback renditions.
COPY data/ ./data/

RUN mkdir -p /app/storage/audio \
    && python3 scripts/seed_demo.py /app/storage/audio \
    && useradd --create-home --uid 10001 iota \
    && chown -R iota:iota /app

USER iota

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Production worker configuration:
#   --proxy-headers / --forwarded-allow-ips  correct client IP behind nginx
#   --workers                             one process per CPU (WEB_CONCURRENCY)
#   --limit-max-requests                  recycle workers to bound memory
#   --timeout-graceful-shutdown           let in-flight streams finish
#   --no-server-header                    do not advertise the server version
CMD ["sh", "-c", "exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${WEB_CONCURRENCY} \
    --loop uvloop \
    --http httptools \
    --proxy-headers \
    --forwarded-allow-ips '*' \
    --timeout-keep-alive 75 \
    --timeout-graceful-shutdown ${WEB_TIMEOUT} \
    --limit-max-requests ${WEB_MAX_REQUESTS} \
    --limit-max-requests-jitter ${WEB_MAX_REQUESTS_JITTER} \
    --no-server-header \
    --log-level warning"]
