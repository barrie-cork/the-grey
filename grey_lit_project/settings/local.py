from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1,0.0.0.0",
    cast=lambda v: [s.strip() for s in v.split(",")],
)

# Development apps
# TODO: Uncomment these once installed
# INSTALLED_APPS += [
#     "django_debug_toolbar",
#     "django_querycount",
# ]

# Development middleware
# TODO: Uncomment once django_debug_toolbar is installed
# MIDDLEWARE = [
#     "django_debug_toolbar.middleware.DebugToolbarMiddleware",
# ] + MIDDLEWARE

# Django Debug Toolbar
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# Show SQL queries in console
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": config("DJANGO_LOG_LEVEL", default="INFO"),
            "propagate": False,
        },
    },
}

# Email backend for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = 'Thesis Grey <noreply@localhost>'

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Celery - Use eager mode for development/testing
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = True

# Static files
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"