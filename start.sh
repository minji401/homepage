#!/usr/bin/env bash
set -o errexit
python manage.py migrate --noinput
python manage.py init_cms
if [ -n "${DATABASE_URL:-}" ] || [ -n "${SHARED_DATABASE_URL:-}" ]; then
  python manage.py sync_shared_users || true
fi
exec gunicorn herium.wsgi:application --bind 0.0.0.0:"${PORT:-8000}" --workers 1 --timeout 120
