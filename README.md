# Thesis Grey - Systematic Grey Literature Review Platform

[![Django](https://img.shields.io/badge/Django-4.2.11-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

Thesis Grey is a Django-based web application designed to help researchers systematically find, manage, and review grey literature following PRISMA guidelines. It automates search execution through Google Search API via Serper and provides a comprehensive workflow for literature review.

## Key Features

- **9-State Workflow Management**: Systematic progression from draft to completion
- **PIC Framework**: Population, Interest, Context-based search query builder
- **Automated Search Execution**: Serper API integration with Celery task management
- **Result Deduplication**: Intelligent duplicate detection and grouping
- **PRISMA Compliance**: Export reports following systematic review standards
- **Collaborative Review**: Tagging system and review comments
- **Enterprise Security**: UUID primary keys, comprehensive auth system

## Project Status

**Current Phase**: Advanced Feature Development
- ✅ **accounts**: Custom UUID authentication system (100% complete)
- ✅ **review_manager**: 9-state session workflow with dashboard (100% complete)
- ✅ **search_strategy**: PIC framework with dynamic UI (100% complete)
- 🚧 **serp_execution**: API integration and background tasks (in progress)
- ✅ **results_manager**: Processing pipeline with deduplication (90% complete)
- 📋 **review_results**: Manual review interface (planned)
- 📋 **reporting**: PRISMA-compliant exports (planned)

**Test Coverage**: 364+ tests with 95.8% coverage  
**Current Branch**: `feature/major-refactor-api-tests`

[See detailed status](PROJECT_STATUS.md)

## Quick Start

**New Developer?** Check out our comprehensive onboarding resources in the [`onboarding/`](onboarding/) directory:
- 📖 [Full Developer Guide](onboarding/ONBOARDING.md) - Complete setup and architecture overview  
- ⚡ [Quick Setup Guide](onboarding/QUICKSTART.md) - Get running in 5 minutes

### Prerequisites

- Docker and Docker Compose
- Git
- Python 3.12+ (for local development)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/thesis-grey.git
cd thesis-grey
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env file with required values (see Environment Variables section)
```

### Required Environment Variables

The following environment variables must be configured in your `.env` file:

```bash
# Django Core
SECRET_KEY=your-django-secret-key-here

# Database Configuration  
POSTGRES_DB=thesis_grey_db
POSTGRES_USER=thesis_grey_user
POSTGRES_PASSWORD=secure_password
DB_HOST=db
DB_PORT=5432

# External APIs
SERPER_API_KEY=your-serper-api-key-here  # Required for search execution

# Optional: Redis/Celery (defaults provided)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

**⚠️ Important**: Without `SERPER_API_KEY`, search execution functionality will not work.

3. Start Docker services:
```bash
docker-compose up -d
```

4. Run migrations:
```bash
docker-compose run --rm web python manage.py migrate
```

5. Create a superuser:
```bash
docker-compose run --rm web python manage.py createsuperuser
```

### Access Points

- **Application**: http://localhost:8000/
- **Django Admin**: http://localhost:8000/admin/
- **Flower (Celery)**: http://localhost:5555/

### Test Credentials

- **Username**: testadmin
- **Password**: admin123

## Architecture

### Django Apps

1. **accounts**: Custom User model with UUID primary keys
2. **review_manager**: Core 9-state session workflow management
3. **search_strategy**: PIC framework search query builder
4. **serp_execution**: Serper API integration and execution
5. **results_manager**: Result processing and deduplication
6. **review_results**: Manual review interface with tagging
7. **reporting**: PRISMA-compliant export functionality

### Technology Stack

- **Backend**: Django 4.2 LTS with PostgreSQL 15
- **Task Queue**: Celery with Redis broker
- **Cache**: Redis
- **Web Server**: Nginx (reverse proxy)
- **Container**: Docker with Docker Compose
- **Testing**: Django TestCase with 90%+ coverage goal

## Development

### Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements/local.txt
```

### Common Commands

```bash
# Run tests
python manage.py test

# Run specific app tests
python manage.py test apps.accounts

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Run development server
python manage.py runserver

# Start Celery worker
celery -A grey_lit_project worker -l info

# Code quality checks
flake8 apps/ --max-line-length=120
mypy apps/
```

### Docker Commands

```bash
# View logs
docker-compose logs -f

# Shell access
docker-compose run --rm web python manage.py shell

# Database shell
docker-compose run --rm web python manage.py dbshell

# Rebuild containers
docker-compose build

# Stop all services
docker-compose down
```

## PRP Development Methodology

This project uses Product Requirement Prompts (PRPs) for AI-assisted development:

```bash
# Create a new PRP
/create-base-prp implement [feature description]

# Execute a PRP
python PRPs/scripts/prp_runner.py --prp feature-name --interactive

# Review code
/review-general
```

[Learn more about PRPs](PRPs/README.md)

## Project Structure

```
thesis-grey/
├── apps/                    # Django applications
│   ├── accounts/           # Authentication system
│   ├── review_manager/     # Core workflow management
│   ├── search_strategy/    # Search query builder
│   ├── serp_execution/     # API execution
│   ├── results_manager/    # Result processing
│   ├── review_results/     # Review interface
│   └── reporting/          # Export functionality
├── grey_lit_project/       # Django project settings
├── templates/              # Global templates
├── static/                 # Static files
├── docs/                   # Documentation
├── PRPs/                   # Product Requirement Prompts
├── docker-compose.yml      # Docker configuration
└── requirements/           # Python dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards

- Follow PEP 8 with 120 character line limit
- Add type hints to all functions
- Write comprehensive docstrings
- Maintain 90%+ test coverage
- Use Django best practices

## Documentation

### Core Documentation
- [Project Status](PROJECT_STATUS.md)  
- [Product Requirements Document](docs/PRD.md)
- [UI Guidelines](docs/ui-guidelines.md)
- [Developer Onboarding](onboarding/) - **Start here for new developers**

### App-Specific Implementation Guides
- [Authentication System](docs/features/accounts/PRD-auth.md)
- [Review Manager](docs/features/review_manager/review-manager-prd.md)
- [Search Strategy](docs/features/search_strategy/search-strategy-prd.md)
- [Results Manager](docs/features/results_manager/results-manager-prd.md)
- [Review Results](docs/features/review_results/review-results-prd.md)
- [Reporting](docs/features/reporting/reporting-prd.md)

### Development Resources
- [PRP Development Methodology](PRPs/README.md)
- [API Documentation](docs/api/) (coming soon)

## Security

- UUID primary keys for all models
- CSRF protection enabled
- Secure password validation
- Environment-based configuration
- No secrets in code repository

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- PRISMA guidelines for systematic reviews
- Django Software Foundation
- Serper.dev for search API
- All contributors and testers