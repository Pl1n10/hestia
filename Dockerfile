# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Deps first for layer caching.
COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
RUN pip install -U pip && pip install .

# Persist the SQLite db on a volume.
ENV HESTIA_DATABASE_URL=sqlite:////data/hestia.db
RUN mkdir -p /data && useradd -m hestia && chown -R hestia /data /app
USER hestia
VOLUME ["/data"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
