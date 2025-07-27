"""
Docker-compatible test settings for Results Manager testing.
Uses PostgreSQL from Docker container with local Django development server.
"""
from grey_lit_project.settings.base import *

# Use Docker PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'thesis_grey_db',
        'USER': 'thesis_grey_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',  # Since we're running Django locally but DB in Docker
        'PORT': '5432',
    }
}

# Enable debug for development testing
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# Use a simple password hasher for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Test-specific settings
SECRET_KEY = 'docker-test-secret-key-for-testing-only'

# Enable cache for development testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery settings for testing - make tasks run synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Redis connection for Docker
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# Add some logging for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'apps.results_manager': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}