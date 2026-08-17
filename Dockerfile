# Coolify deploy image (gunicorn + WhiteNoise). Traefik terminates TLS in front.
# The Apache/mod_wsgi image under docker/Dockerfile is the upstream variant.

# Frontend vendor assets (bootstrap/jquery/icons). node_modules is gitignored,
# so the image must build them from submission/static/package.json.
FROM node:20-slim AS assets
WORKDIR /assets
COPY submission/static/package.json ./
RUN npm install --no-audit --no-fund

FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=dbfv.settings_prod \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Build deps for reportlab/pillow-style wheels; keep the layer lean.
RUN apt-get update \
  && apt-get install --no-install-recommends -y build-essential libjpeg-dev zlib1g-dev \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN python -m venv /app/.venv \
  && pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir .

COPY . /app
COPY --from=assets /assets/node_modules /app/submission/static/node_modules

RUN mkdir -p /app/static /app/media /app/data
EXPOSE 8000
CMD ["/app/docker/entrypoint.sh"]
