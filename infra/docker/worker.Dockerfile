FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY backend /app/backend

RUN pip install --upgrade pip && pip install -e .

RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/data \
    && chown -R app:app /app

WORKDIR /app/backend

USER app

CMD ["celery", "-A", "app.workers.celery_app.celery_app", "worker", "--loglevel=info"]