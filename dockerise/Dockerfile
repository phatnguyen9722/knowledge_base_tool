# Knowledge Base Tool — web server image.
# Build context MUST be the project root (so app/, templates/, static/ are visible):
#   docker build -f dockerise/Dockerfile -t kb-tool .
FROM python:3.12-slim

# Faster, cleaner Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first (better layer caching).
COPY dockerise/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App code + assets.
COPY app/ /app/app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Container config (data dirs point at /data).
COPY dockerise/config.docker.yaml /app/config.yaml

# Persist all user content here.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 5050

# Run the FastAPI app directly with Uvicorn (no tray launcher in the container).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5050"]
