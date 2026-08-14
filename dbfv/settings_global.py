# Django settings for dbfv project.

# Standard Library
import os

# Secure by default. Local development must opt in via the local settings
# (root settings.py sets DEBUG = True).
DEBUG = False
TEMPLATE_DEBUG = DEBUG

# HTTPS/transport hardening. TLS is not guaranteed by this repository (the
# bundled Apache config listens on :80); it must be terminated by the operator's
# reverse proxy. The whole HTTPS posture is therefore opt-in via DJANGO_SECURE=1,
# to be set ONLY once TLS termination is confirmed. This keeps an HTTP-only
# deployment working (secure cookies over plain HTTP would break login) and,
# crucially, avoids trusting a spoofable X-Forwarded-Proto header when there is
# no trusted TLS proxy in front.
_SECURE = os.environ.get('DJANGO_SECURE') == '1'
if _SECURE:
    # Only honor the proxy's TLS header when we've declared a trusted TLS proxy.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = _SECURE
CSRF_COOKIE_SECURE = _SECURE
SECURE_SSL_REDIRECT = _SECURE
SECURE_HSTS_SECONDS = 31536000 if _SECURE else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = _SECURE
SECURE_HSTS_PRELOAD = _SECURE
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'de'

# Model used for the user profile
AUTH_PROFILE_MODULE = 'submission.UserProfile'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

LOGIN_URL = '/anmelden/'
LOGIN_REDIRECT_URL = '/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Primary keys are AutoFields
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        # 'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'submission.context_processor.processor',

                # Django
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',

                # Breadcrumbs
                'django.template.context_processors.request'
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'debug':
            False
        },
    },
]

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    # Outer: audits final API responses (incl. 429 from the limiter below).
    'api.middleware.ApiAuditMiddleware',
    # Runs before DRF permissions so invalid API keys are rate-limited too.
    'api.middleware.ApiPreAuthRateLimitMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # Clickjacking protection (X-Frame-Options: DENY)
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'dbfv.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'dbfv.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    # reCaptcha support, see https://github.com/praekelt/django-recaptcha
    #'captcha',

    # The dbfv submission app
    'submission',
    'core',

    # Django debug toolbar
    # 'debug_toolbar',

    # Email verification
    'django_email_verification',

    # Forms
    'crispy_forms',
    'crispy_bootstrap5',

    # REST API
    'rest_framework',
    'rest_framework_api_key',
    'django_filters',
    'drf_spectacular',
    'api',
)

REST_FRAMEWORK = {
    # Every endpoint requires a valid API key by default; write needs write_allowed.
    'DEFAULT_PERMISSION_CLASSES': ['api.permissions.ScopedAPIKeyPermission'],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # Throttle per API key (falls back to IP when no key is present).
    'DEFAULT_THROTTLE_CLASSES': ['api.throttling.APIKeyRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'apikey': '1000/hour'},
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# The IP limit runs before key validation; successful requests are additionally
# limited per API key by APIKeyRateThrottle.
API_PREAUTH_RATE_LIMIT = '120/minute'
API_KEY_REQUEST_RATE_LIMIT = '5/hour'

SPECTACULAR_SETTINGS = {
    'TITLE': 'DBFV API',
    'DESCRIPTION': 'REST-API des DBFV-Antragssystems (Lizenzverwaltung).',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = 'bootstrap5'

DEBUG_TOOLBAR_CONFIG = {'INTERCEPT_REDIRECTS': False}
INTERNAL_IPS = ('127.0.0.1', )


# Email verification
def verified_callback(user):
    user.userprofile.email_verified = True
    user.userprofile.save()


EMAIL_MAIL_CALLBACK = verified_callback
EMAIL_FROM_ADDRESS = 'noreply@dbfv.com'
EMAIL_MAIL_SUBJECT = 'Bestätige deine E-Mail-Adresse'
EMAIL_MAIL_HTML = 'email/verification/html_body.tpl'
EMAIL_MAIL_PLAIN = 'email/verification/txt_body.tpl'
EMAIL_MAIL_TOKEN_LIFE = 60 * 60
EMAIL_MAIL_PAGE_TEMPLATE = 'email/verification/confirm_template.html'
EMAIL_PAGE_DOMAIN = 'http://mydomain.com/'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        # API audit trail (usage, 403/429, key revocations). Ships to stdout;
        # route it to a file/collector in the deployment as needed.
        'dbfv.audit': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}
