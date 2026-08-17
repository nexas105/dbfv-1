#!/bin/sh
# Coolify container start: apply schema, publish static, then serve.
set -e

python manage.py migrate --no-input
python manage.py collectstatic --no-input

exec gunicorn dbfv.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-60}"
