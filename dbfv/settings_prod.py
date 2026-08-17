# Production settings, env-driven. Enable via DJANGO_SETTINGS_MODULE=dbfv.settings_prod.
# ponytail: all deployment-specific values come from the environment, no per-host file.
# Standard Library
import os

# dbfv
from dbfv.settings_global import *  # noqa: F401,F403


def _list(name):
    return [v.strip() for v in os.environ.get(name, '').split(',') if v.strip()]


SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # required; fail loud if missing
DEBUG = False
ALLOWED_HOSTS = _list('DJANGO_ALLOWED_HOSTS') or ['*']
CSRF_TRUSTED_ORIGINS = _list('DJANGO_CSRF_TRUSTED_ORIGINS')

# Static files served by WhiteNoise from the gunicorn process (Traefik in front).
STATIC_ROOT = os.environ.get('DJANGO_STATIC_ROOT', '/app/static')
MEDIA_ROOT = os.environ.get('DJANGO_MEDIA_ROOT', '/app/media')
MEDIA_URL = '/media/'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
# WhiteNoise directly after the security-relevant outer middleware.
MIDDLEWARE = (MIDDLEWARE[0], 'whitenoise.middleware.WhiteNoiseMiddleware') + MIDDLEWARE[1:]

# Database: sqlite on a persistent volume by default; set DB_ENGINE for MySQL/Postgres.
_db_engine = os.environ.get('DB_ENGINE')
if _db_engine:
    DATABASES = {'default': {
        'ENGINE': _db_engine,
        'NAME': os.environ['DB_NAME'],
        'USER': os.environ.get('DB_USER', ''),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', ''),
        'PORT': os.environ.get('DB_PORT', ''),
    }}
else:
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('SQLITE_PATH', '/app/data/db.sqlite3'),
    }}

EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
