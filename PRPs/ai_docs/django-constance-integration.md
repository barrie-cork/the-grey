# Django Constance Integration Guide

## Overview

Django Constance provides dynamic Django settings accessible via the admin interface. This guide covers integration with the Thesis Grey project for runtime configuration management.

## Installation

```bash
pip install django-constance[database]
```

## Configuration

### 1. Add to INSTALLED_APPS

```python
# grey_lit_project/settings/base.py
INSTALLED_APPS = [
    # ... existing apps
    'constance',
    'constance.backends.database',  # If using database backend
]
```

### 2. Configure Backend

```python
# grey_lit_project/settings/base.py

# Use database backend for persistence
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

# Optional: Redis backend for better performance
# CONSTANCE_BACKEND = 'constance.backends.redisd.RedisBackend'
# CONSTANCE_REDIS_CONNECTION = {
#     'host': 'redis',
#     'port': 6379,
#     'db': 0,
# }

# Prefix for database/cache keys
CONSTANCE_DATABASE_PREFIX = 'constance:thesis_grey:'
```

### 3. Define Configuration Schema

```python
# grey_lit_project/settings/base.py

CONSTANCE_CONFIG = {
    # Search Configuration
    'SEARCH_DEFAULT_NUM_RESULTS': (100, 'Default number of search results', int),
    'SEARCH_DEFAULT_LOCATION': ('', 'Default search location (empty for global)', str),
    'SEARCH_DEFAULT_LANGUAGE': ('en', 'Default search language', str),
    'SEARCH_DEFAULT_FILE_TYPES': ('pdf', 'Comma-separated file types', str),
    
    # API Configuration
    'API_SERPER_TIMEOUT': (30, 'Serper API timeout in seconds', int),
    'API_RATE_LIMIT_PER_MINUTE': (100, 'API rate limit per minute', int),
    'API_MAX_RETRIES': (3, 'Maximum API retry attempts', int),
    
    # Processing Configuration
    'PROCESSING_BATCH_SIZE': (50, 'Batch size for result processing', int),
    'PROCESSING_CACHE_TTL': (3600, 'Cache TTL in seconds', int),
    
    # Feature Flags
    'FEATURE_ADVANCED_SEARCH': (False, 'Enable advanced search features', bool),
    'FEATURE_AI_SUGGESTIONS': (False, 'Enable AI-powered suggestions', bool),
}

# Organize settings into fieldsets for better admin UI
CONSTANCE_CONFIG_FIELDSETS = {
    'Search Settings': (
        'SEARCH_DEFAULT_NUM_RESULTS',
        'SEARCH_DEFAULT_LOCATION', 
        'SEARCH_DEFAULT_LANGUAGE',
        'SEARCH_DEFAULT_FILE_TYPES',
    ),
    'API Settings': (
        'API_SERPER_TIMEOUT',
        'API_RATE_LIMIT_PER_MINUTE',
        'API_MAX_RETRIES',
    ),
    'Processing Settings': (
        'PROCESSING_BATCH_SIZE',
        'PROCESSING_CACHE_TTL',
    ),
    'Feature Flags': (
        'FEATURE_ADVANCED_SEARCH',
        'FEATURE_AI_SUGGESTIONS',
    ),
}
```

### 4. Run Migrations

```bash
python manage.py migrate constance
```

## Usage in Code

### Basic Usage

```python
from constance import config

# Read configuration values
num_results = config.SEARCH_DEFAULT_NUM_RESULTS
timeout = config.API_SERPER_TIMEOUT

# Use in your code
def perform_search(query):
    results = serper_api.search(
        query,
        num_results=config.SEARCH_DEFAULT_NUM_RESULTS,
        timeout=config.API_SERPER_TIMEOUT
    )
    return results
```

### Integration with Pydantic Config

```python
# apps/core/config.py
from constance import config as constance_config
from pydantic import BaseModel, Field

class SearchConfig(BaseModel):
    """Search configuration with Constance integration."""
    
    @classmethod
    def from_constance(cls):
        """Load configuration from Constance."""
        return cls(
            default_num_results=constance_config.SEARCH_DEFAULT_NUM_RESULTS,
            default_location=constance_config.SEARCH_DEFAULT_LOCATION or None,
            default_language=constance_config.SEARCH_DEFAULT_LANGUAGE,
            default_file_types=constance_config.SEARCH_DEFAULT_FILE_TYPES.split(',')
        )
```

### Dynamic Updates

```python
# Configuration changes are reflected immediately
from constance import config
from django.core.cache import cache

def get_cached_results(key):
    # TTL is dynamically configurable
    ttl = config.PROCESSING_CACHE_TTL
    return cache.get(key, timeout=ttl)
```

## Admin Interface

### Basic Admin Integration

Constance automatically adds a configuration section to Django admin at `/admin/constance/config/`.

### Custom Admin View

```python
# apps/core/admin.py
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def configuration_redirect(request):
    """Redirect to Constance config page."""
    return redirect('/admin/constance/config/')

# Add custom URL
admin.site.urlpatterns = [
    path('configuration/', configuration_redirect, name='configuration'),
] + admin.site.urlpatterns
```

### Enhanced Admin with Django Unfold

```python
# grey_lit_project/settings/base.py
INSTALLED_APPS = [
    'unfold',  # Before django.contrib.admin
    'unfold.contrib.filters',
    'django.contrib.admin',
    # ... other apps
    'constance',
]

# Unfold configuration
from django.utils.translation import gettext_lazy as _

UNFOLD = {
    "SITE_TITLE": "Thesis Grey Admin",
    "SITE_HEADER": "Thesis Grey",
    "TABS": [
        {
            "models": ["constance.Config"],
            "items": [
                {
                    "title": _("System Configuration"),
                    "icon": "settings",
                    "link": "/admin/constance/config/",
                }
            ],
        },
    ],
}
```

## Testing with Constance

### Override in Tests

```python
# apps/serp_execution/tests/test_services.py
from constance.test import override_config
from constance import config

class TestSerperClient(TestCase):
    
    @override_config(SEARCH_DEFAULT_NUM_RESULTS=50)
    def test_custom_num_results(self):
        """Test with overridden configuration."""
        self.assertEqual(config.SEARCH_DEFAULT_NUM_RESULTS, 50)
        # Your test code here
    
    @override_config(
        API_SERPER_TIMEOUT=10,
        API_RATE_LIMIT_PER_MINUTE=50
    )
    def test_api_limits(self):
        """Test with multiple overrides."""
        client = SerperClient()
        self.assertEqual(client.timeout, 10)
        self.assertEqual(client.rate_limit, 50)
```

### Test Settings

```python
# grey_lit_project/settings/test.py

# Use memory backend for tests
CONSTANCE_BACKEND = 'constance.backends.memory.MemoryBackend'

# Simplified config for testing
CONSTANCE_CONFIG = {
    'SEARCH_DEFAULT_NUM_RESULTS': (10, 'Test default', int),
    'API_SERPER_TIMEOUT': (5, 'Test timeout', int),
}
```

## Caching Considerations

### With Redis

```python
# Automatic caching with Redis backend
CONSTANCE_REDIS_CACHE_TIMEOUT = 60  # Cache for 60 seconds

# Manual cache invalidation
from constance import config
from constance.backends.database import DatabaseBackend

# Force reload from database
backend = DatabaseBackend()
backend._cache.clear()
```

### With Database Backend

```python
# Add caching layer
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
    }
}

# Cache timeout for Constance
CONSTANCE_DATABASE_CACHE_TIMEOUT = 60
```

## Best Practices

1. **Use Descriptive Names**: Prefix settings with their domain (SEARCH_, API_, etc.)

2. **Provide Help Text**: The second tuple element should explain the setting clearly

3. **Use Appropriate Types**: Constance supports int, float, bool, str, dict, list

4. **Set Sensible Defaults**: First tuple element should be a safe default

5. **Group Related Settings**: Use CONSTANCE_CONFIG_FIELDSETS for organization

6. **Cache Appropriately**: Balance between performance and configuration freshness

7. **Validate Input**: Add custom validators if needed:

```python
from django.core.exceptions import ValidationError

def validate_positive(value):
    if value <= 0:
        raise ValidationError('Value must be positive')

CONSTANCE_CONFIG = {
    'PROCESSING_BATCH_SIZE': (
        50, 
        'Batch size for processing', 
        int,
        {'validators': [validate_positive]}
    ),
}
```

## Migration from Hardcoded Values

### Before (Hardcoded)
```python
# apps/serp_execution/tasks.py
api_params = {
    "num": 100,  # Hardcoded
    "location": "United States",  # Hardcoded
    "language": "en",  # Hardcoded
}
```

### After (Constance)
```python
# apps/serp_execution/tasks.py
from constance import config

api_params = {
    "num": config.SEARCH_DEFAULT_NUM_RESULTS,
    "location": config.SEARCH_DEFAULT_LOCATION or None,
    "language": config.SEARCH_DEFAULT_LANGUAGE,
}
```

## Monitoring Configuration Changes

```python
# apps/core/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from constance.models import Constance
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Constance)
def log_config_change(sender, instance, **kwargs):
    """Log configuration changes for audit trail."""
    logger.info(
        f"Configuration changed: {instance.key} = {instance.value}",
        extra={
            'config_key': instance.key,
            'new_value': instance.value,
        }
    )
```

## Troubleshooting

### Common Issues

1. **Changes Not Reflected**: Clear cache or reduce CONSTANCE_DATABASE_CACHE_TIMEOUT

2. **Import Errors**: Ensure constance is in INSTALLED_APPS before importing config

3. **Admin Not Showing**: Run migrations and check INSTALLED_APPS order

4. **Type Errors**: Constance returns strings by default, specify type in config tuple

### Debug Helper

```python
# Check current configuration
from constance import config
from pprint import pprint

def debug_config():
    """Print all Constance settings."""
    settings = {}
    for key in dir(config):
        if key.isupper():
            settings[key] = getattr(config, key)
    pprint(settings)
```

## References

- Official Documentation: https://django-constance.readthedocs.io/
- GitHub Repository: https://github.com/jazzband/django-constance
- Django Packages Entry: https://djangopackages.org/packages/p/django-constance/