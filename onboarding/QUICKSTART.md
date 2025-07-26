# Thesis Grey - Quick Start Guide

Get up and running with Thesis Grey in under 10 minutes!

## What is Thesis Grey?
A Django web application for systematic grey literature review, helping researchers find and manage research outside traditional academic databases following PRISMA guidelines.

## Prerequisites
- Docker & Docker Compose
- Git

## 5-Minute Setup

### 1. Clone and Setup
```bash
git clone https://github.com/yourusername/thesis-grey.git
cd thesis-grey
cp .env.example .env
```

### 2. Start Services
```bash
docker-compose up -d
```

### 3. Initialize Database
```bash
docker-compose run --rm web python manage.py migrate
docker-compose run --rm web python manage.py createsuperuser
```

### 4. Access Application
- **Main App**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/
- **Task Monitor**: http://localhost:5555/

## Test Your Setup

### 1. Login & Create Session
1. Visit http://localhost:8000/
2. Login with your superuser account
3. Click "Create New Session"
4. Fill in title and description

### 2. Define Search Strategy
1. Click on your new session
2. Add Population, Interest, Context terms
3. Configure search domains
4. Preview generated queries

### 3. Run Tests
```bash
docker-compose run --rm web python manage.py test
```

## Project Structure Overview
```
agent-grey/
├── apps/                    # Django applications
│   ├── accounts/           # ✅ User authentication (UUID-based)
│   ├── review_manager/     # ✅ Session workflow management
│   ├── search_strategy/    # ✅ PIC framework search builder
│   ├── serp_execution/     # 🚧 API integration (in progress)
│   ├── results_manager/    # ✅ Result processing (90% complete)
│   ├── review_results/     # 📋 Manual review interface (planned)
│   └── reporting/          # 📋 PRISMA exports (planned)
├── docs/                   # Comprehensive documentation
├── PRPs/                   # AI-assisted development prompts
└── docker-compose.yml      # Multi-container setup
```

## Key Features Working Now
- ✅ **User Authentication**: Custom UUID-based user system
- ✅ **Session Management**: 9-state workflow with smart navigation
- ✅ **Search Strategy**: PIC framework with dynamic query building
- ✅ **Result Processing**: Deduplication and metadata extraction
- 🚧 **Search Execution**: API integration in progress

## Development Commands

### View Logs
```bash
docker-compose logs -f web        # Application logs
docker-compose logs -f celery_worker  # Background tasks
```

### Access Shell
```bash
docker-compose run --rm web python manage.py shell
```

### Run Specific Tests
```bash
docker-compose run --rm web python manage.py test apps.accounts
```

### Code Quality
```bash
docker-compose run --rm web flake8 apps/ --max-line-length=120
```

## Common URLs
- **Dashboard**: http://localhost:8000/
- **Admin**: http://localhost:8000/admin/
- **Sessions**: http://localhost:8000/sessions/
- **Celery Monitor**: http://localhost:5555/

## Need Help?
- 📖 **Full Documentation**: See `ONBOARDING.md`
- 🏗️ **Architecture Guide**: See `docs/PRD.md`
- 🔧 **Development Guide**: See `CLAUDE.md`
- 🚀 **AI Development**: See `PRPs/README.md`

## Next Steps
1. Read through `ONBOARDING.md` for comprehensive setup
2. Explore the Django admin to understand data models
3. Create your first test session through the UI
4. Review the existing code patterns in `apps/`
5. Choose an area to contribute (see implementation status above)

---

**🎉 You're ready to start developing!** The application follows standard Django patterns with a focus on systematic literature review workflows.