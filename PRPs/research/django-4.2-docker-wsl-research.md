# Django 4.2 Docker WSL Research Archive

## Research Date: 2025-01-25

### Search Queries Performed
1. "Django 4.2 project structure modular apps PostgreSQL Celery Redis setup 2024"
2. "Django 4.2 custom User model UUID primary key AbstractUser settings structure"
3. "Django 4.2 project settings structure base local production best practices 2024"
4. "Django 4.2 Celery 5.3 Redis configuration docker-compose.yml example 2024"
5. "Django Vertical Slice Architecture VSA modular apps feature-based structure 2024"
6. "Django Docker WSL2 development environment setup best practices 2024"

## Key Findings

### 1. Django 4.2 with Docker Best Practices (2025)

#### Docker Compose is Standard
- In 2025, containerizing with Docker Compose is the preferred approach
- Simplifies development by managing all services with single command
- Eliminates "works on my machine" issues

#### Recommended Docker Services Structure
```yaml
services:
  web: Django application
  db: PostgreSQL (15 or 16)
  redis: Redis 7 for caching and Celery broker
  celery_worker: Background tasks
  celery_beat: Scheduled tasks
  nginx: Reverse proxy
  flower: Celery monitoring (optional)
```

#### Key Docker Insights
- Use health checks to prevent race conditions
- Alpine images recommended for smaller size
- Volume management crucial for data persistence
- Network isolation improves security

### 2. Custom User Model with UUID

#### Critical Implementation Rules
1. **MUST be done before first migration** - Cannot be changed later without complex database work
2. **Use AbstractUser** - Maintains Django's user functionality
3. **UUID Configuration**:
   ```python
   import uuid
   from django.contrib.auth.models import AbstractUser
   
   class User(AbstractUser):
       id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
   ```
4. **Settings requirement**: `AUTH_USER_MODEL = 'accounts.User'`

#### Common Pitfalls
- Changing after migrations requires manual schema fixes
- Affects all foreign keys and many-to-many relationships
- Must be in first app created

### 3. Settings Structure Best Practices

#### Three-Tier Structure (Most Common)
```
settings/
├── __init__.py
├── base.py       # Shared settings
├── local.py      # Development
└── production.py # Production
```

#### Environment Management
- Use `DJANGO_SETTINGS_MODULE` environment variable
- Never commit sensitive data
- Use python-decouple or django-environ for env vars
- `.env` files for local development

#### Key Differences
- **local.py**: DEBUG=True, SQLite/local PostgreSQL, CORS_ORIGIN_ALLOW_ALL=True
- **production.py**: DEBUG=False, security headers, proper database config
- **base.py**: Common apps, middleware, templates

### 4. Celery 5.3 with Redis Configuration

#### Modern Configuration (2024)
```python
# settings.py
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
```

#### Redis vs RabbitMQ (2024 Consensus)
- **Redis**: Preferred for most Django projects
  - Simpler setup
  - Often already in stack for caching
  - Sufficient for most task queuing needs
- **RabbitMQ**: For complex routing or guaranteed delivery

#### Best Practices
- Design idempotent tasks
- Use task retries with exponential backoff
- Monitor with Flower in development
- Separate worker containers in Docker

### 5. Vertical Slice Architecture (VSA) for Django

#### Core Principles
1. **Feature-Centric**: Organize by feature, not technical layer
2. **Self-Contained**: Each slice has everything it needs
3. **High Cohesion**: Related code stays together
4. **Low Coupling**: Minimal dependencies between slices

#### Django Implementation
- Each Django app = one vertical slice/feature
- App contains: models, views, forms, templates, static, tests
- Aligns perfectly with Django's app philosophy
- Easier to scale teams (each team owns features)

#### VSA Benefits (2024 Reports)
- Reduced complexity
- Feature-focused changes
- Better scalability
- Easier maintenance
- Natural CQRS alignment

### 6. WSL2 Docker Development

#### Critical Performance Rule
**Store code in WSL2 filesystem**, not Windows filesystem
- Use: `\\wsl$\Ubuntu\home\username\projects\`
- NOT: `C:\Users\username\projects\`
- 10x+ performance difference

#### WSL2 Docker Best Practices
1. Enable WSL2 integration in Docker Desktop
2. Use VS Code with Remote-WSL extension
3. Run all commands inside WSL2
4. Use .devcontainer for consistency
5. Docker context should be default (not "wsl")

#### Development Benefits
- Native Linux performance
- Consistent with production
- Better file watching
- Proper permissions handling

## Technology Version Recommendations (2024)

Based on research, these versions are well-tested together:
- Django: 4.2.11 (LTS)
- PostgreSQL: 15 (16 also viable)
- Redis: 7-alpine
- Celery: 5.3.6
- Python: 3.11 or 3.12
- Psycopg: 3.1.x (not 2.x)
- Docker Compose: 3.8 or 3.9

## Architecture Insights

### Why These Choices Matter

1. **Django 4.2 LTS**: Supported until April 2026, stable, proven
2. **PostgreSQL + Psycopg3**: Better async support, modern Python features
3. **Redis**: Fast, simple, perfect for Django caching + Celery
4. **Docker**: Consistency across development, staging, production
5. **VSA**: Aligns with Django apps, reduces complexity

### Integration Patterns
- Use Django's ORM effectively (select_related, prefetch_related)
- Celery for ALL external API calls
- Redis for both caching and message broker
- PostgreSQL JSON fields for flexible data
- UUID primary keys for distributed systems

## Common Gotchas Discovered

1. **Custom User Model Timing**: #1 mistake is creating after migrations
2. **Settings Import Order**: Base must be imported before environment-specific
3. **Docker Build Context**: Use .dockerignore to speed builds
4. **WSL2 File Location**: Windows filesystem kills performance
5. **Health Checks**: Prevent "container started but service not ready"
6. **Celery in Docker**: Needs separate container, not in web container

## 2024 Trends in Django Development

1. **Docker-First Development**: Almost universal in professional teams
2. **Type Hints**: Increasingly common with mypy
3. **Async Views**: Growing adoption but not mandatory
4. **HTMX Integration**: Popular for dynamic UIs without heavy JS
5. **Tailwind CSS**: Replacing Bootstrap in many projects
6. **Factory Pattern Tests**: factory_boy is standard

## Recommended Learning Resources

From research, these were frequently cited:
1. TestDriven.io - Celery + Django course
2. Django Stars Blog - Configuration best practices
3. Simple is Better Than Complex - Production setup
4. Official Django 4.2 release notes
5. William Vincent's Django books/tutorials

## Final Architecture Recommendations

Based on all research, the optimal setup for Thesis Grey:
1. Docker Compose with 7 services
2. Django 4.2 with split settings
3. Custom User with UUID from start
4. PostgreSQL 15 with Psycopg 3
5. Redis for caching and Celery
6. VSA with 7 feature apps
7. Development in WSL2 filesystem
8. Environment-based configuration
9. Comprehensive testing from start
10. Security-first approach

This research forms the foundation for building a production-ready Django application that can scale with the project's needs.