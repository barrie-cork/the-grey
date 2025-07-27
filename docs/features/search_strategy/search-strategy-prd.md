# Search Strategy: App-Specific Product Requirements Document

**Project Title:** Thesis Grey - Search Strategy App  
**Version:** 1.0  
**Date:** 2025-01-25  
**App Path:** `apps/search_strategy/`  
**Master PRD:** [docs/PRD.md](../PRD.md)  
**Dependencies:** `review_manager` (SearchSession), `accounts` (User model)  
**Status:** Production Ready

## 1. Executive Summary

The Search Strategy app empowers researchers to define systematic search queries using the PIC framework (Population, Interest, Context). It provides an intuitive interface for building complex Boolean queries, managing multiple search domains, and configuring file type filters. This app transforms researcher intent into executable search strategies that drive the subsequent search execution phase.

### Key Responsibilities

- **PIC Framework Implementation**: Capture Population, Interest, and Context terms systematically
- **Query Generation**: Build complex Boolean queries with proper operator precedence
- **Domain Management**: Support multi-domain searches with organization-specific sites
- **File Type Configuration**: Filter results by document types (PDF, Word documents)
- **Strategy Validation**: Ensure completeness before allowing workflow progression

### Integration Points

- **Depends on**: `review_manager` (SearchSession model), `accounts` (User authentication)
- **Used by**: `serp_execution` (consumes generated queries)
- **Coordinates with**: Dashboard navigation and session workflow transitions

## 2. Technical Architecture

### 2.1 Technology Stack

- **Framework**: Django 4.2 with Class-Based Views
- **Database**: PostgreSQL with ArrayField and JSONField
- **Frontend**: Django Templates with dynamic JavaScript
- **JavaScript**: Real-time query preview and tag-based input
- **Testing**: Django TestCase with comprehensive coverage
- **Validation**: Server-side validation with XSS prevention

### 2.2 App Structure

```
apps/search_strategy/
├── __init__.py
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── forms.py              # SearchStrategyForm with validation
├── models.py             # SearchStrategy, SearchQuery models
├── views.py              # Create, Update, Detail views
├── urls.py               # URL patterns
├── api.py                # AJAX endpoints for preview
├── validators.py         # Custom validation logic
├── templates/
│   └── search_strategy/
│       ├── strategy_form.html
│       ├── strategy_detail.html
│       └── components/
│           ├── pic_input.html
│           └── query_preview.html
├── static/
│   └── search_strategy/
│       ├── css/
│       │   └── strategy.css
│       └── js/
│           ├── strategy_form.js
│           └── strategy_detail.js
├── tests/
│   ├── test_models.py
│   ├── test_forms.py
│   ├── test_views.py
│   ├── test_api.py
│   └── test_integration.py
└── migrations/
```

### 2.3 Database Models

#### SearchStrategy Model

```python
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import get_user_model
from apps.review_manager.models import SearchSession
import uuid

User = get_user_model()

class SearchStrategy(models.Model):
    """
    Represents a search strategy using the PIC framework.
    Generates Boolean queries for multiple domains and file types.
    """
    
    # Primary key and relationships
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(
        SearchSession, 
        on_delete=models.CASCADE, 
        related_name='search_strategy'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='search_strategies'
    )
    
    # PIC Framework fields using PostgreSQL ArrayField
    population_terms = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True,
        help_text="Terms describing the population (e.g., 'elderly', 'children with autism')"
    )
    interest_terms = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True,
        help_text="Terms describing the intervention/interest (e.g., 'telehealth', 'cognitive therapy')"
    )
    context_terms = ArrayField(
        models.CharField(max_length=200),
        default=list,
        blank=True,
        help_text="Terms describing the context/setting (e.g., 'rural', 'low-income countries')"
    )
    
    # Search configuration
    search_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configuration for domains, file types, and search parameters"
    )
    # Structure: {
    #     "domains": ["nice.org.uk", "who.int", "custom-domain.com"],
    #     "include_general_search": true,
    #     "file_types": ["pdf", "doc"],
    #     "search_type": "google"  # or "scholar"
    # }
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_complete = models.BooleanField(default=False)
    validation_errors = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'search_strategies'
        verbose_name = 'Search Strategy'
        verbose_name_plural = 'Search Strategies'
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['user']),
            models.Index(fields=['is_complete']),
        ]
    
    def __str__(self):
        return f"Strategy for {self.session.title}"
    
    def validate_completeness(self):
        """Validate that the strategy has all required components."""
        errors = {}
        
        # At least one PIC category must have terms
        if not any([self.population_terms, self.interest_terms, self.context_terms]):
            errors['pic_terms'] = 'At least one PIC category must have terms'
        
        # Must have at least one domain or general search enabled
        domains = self.search_config.get('domains', [])
        include_general = self.search_config.get('include_general_search', False)
        if not domains and not include_general:
            errors['domains'] = 'At least one domain or general search must be selected'
        
        # Must have at least one file type
        if not self.search_config.get('file_types'):
            errors['file_types'] = 'At least one file type must be selected'
        
        self.validation_errors = errors
        self.is_complete = len(errors) == 0
        return self.is_complete
    
    def generate_base_query(self):
        """Generate the base Boolean query from PIC terms."""
        query_parts = []
        
        # Build query parts for each PIC category
        if self.population_terms:
            pop_query = ' OR '.join(f'"{term}"' for term in self.population_terms)
            query_parts.append(f'({pop_query})')
        
        if self.interest_terms:
            int_query = ' OR '.join(f'"{term}"' for term in self.interest_terms)
            query_parts.append(f'({int_query})')
        
        if self.context_terms:
            ctx_query = ' OR '.join(f'"{term}"' for term in self.context_terms)
            query_parts.append(f'({ctx_query})')
        
        # Combine with AND operators
        return ' AND '.join(query_parts) if query_parts else ''
    
    def generate_queries(self):
        """Generate all search queries based on domains and file types."""
        base_query = self.generate_base_query()
        if not base_query:
            return []
        
        queries = []
        file_types = self.search_config.get('file_types', [])
        domains = self.search_config.get('domains', [])
        include_general = self.search_config.get('include_general_search', False)
        
        # Build file type filter
        file_type_parts = []
        for ft in file_types:
            if ft == 'pdf':
                file_type_parts.append('filetype:pdf')
            elif ft == 'doc':
                # Include both .doc and .docx
                file_type_parts.append('(filetype:doc OR filetype:docx)')
        
        file_type_filter = ' OR '.join(file_type_parts) if file_type_parts else ''
        
        # Generate domain-specific queries
        for domain in domains:
            domain_query = f'site:{domain} {base_query}'
            if file_type_filter:
                domain_query += f' ({file_type_filter})'
            queries.append({
                'query': domain_query,
                'domain': domain,
                'type': 'domain-specific'
            })
        
        # Generate general search query if enabled
        if include_general:
            general_query = base_query
            if file_type_filter:
                general_query += f' ({file_type_filter})'
            queries.append({
                'query': general_query,
                'domain': None,
                'type': 'general'
            })
        
        return queries
    
    def get_stats(self):
        """Get statistics about the search strategy."""
        return {
            'population_count': len(self.population_terms),
            'interest_count': len(self.interest_terms),
            'context_count': len(self.context_terms),
            'total_terms': sum([
                len(self.population_terms),
                len(self.interest_terms),
                len(self.context_terms)
            ]),
            'domain_count': len(self.search_config.get('domains', [])),
            'query_count': len(self.generate_queries()),
            'is_complete': self.is_complete
        }


class SearchQuery(models.Model):
    """
    Represents an individual search query generated from the strategy.
    Tracks execution and results for each query.
    """
    
    # Primary key and relationships
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    strategy = models.ForeignKey(
        SearchStrategy,
        on_delete=models.CASCADE,
        related_name='search_queries'
    )
    
    # Query details
    query_text = models.TextField(help_text="The complete search query string")
    query_type = models.CharField(
        max_length=50,
        choices=[
            ('domain-specific', 'Domain Specific'),
            ('general', 'General Search')
        ]
    )
    target_domain = models.CharField(
        max_length=200, 
        blank=True, 
        null=True,
        help_text="Domain for site-specific searches"
    )
    
    # Execution tracking
    execution_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    estimated_results = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'search_queries'
        verbose_name = 'Search Query'
        verbose_name_plural = 'Search Queries'
        ordering = ['execution_order', 'created_at']
        indexes = [
            models.Index(fields=['strategy']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.query_type}: {self.query_text[:50]}..."
```

## 3. API Endpoints

### Phase 1 - AJAX Endpoints (Current)

| Endpoint | Method | Purpose | Authentication |
|----------|---------|---------|----------------|
| `/api/search-strategy/preview/` | POST | Generate query preview | Login required |
| `/api/search-strategy/validate/` | POST | Validate strategy completeness | Login required |
| `/api/search-strategy/export/` | GET | Export strategy as JSON/CSV | Login + ownership |

### Phase 2 - REST API (Future)

Full REST API implementation using Django REST Framework for mobile and third-party integrations.

## 4. User Interface

### 4.1 Views

#### SearchStrategyCreateView
- **Purpose**: Create new search strategy for a session
- **URL**: `/review/session/{session_id}/strategy/create/`
- **Template**: `search_strategy/strategy_form.html`
- **Permissions**: Login required, session ownership, draft status only
- **Features**:
  - Tag-based input for PIC terms
  - Dynamic domain management
  - Real-time query preview
  - Validation feedback

#### SearchStrategyUpdateView
- **Purpose**: Edit existing search strategy
- **URL**: `/review/session/{session_id}/strategy/edit/`
- **Template**: `search_strategy/strategy_form.html`
- **Permissions**: Login required, session ownership, draft status only
- **Features**:
  - Pre-populated form with existing data
  - Change tracking
  - Activity logging

#### SearchStrategyDetailView
- **Purpose**: View strategy and generated queries
- **URL**: `/review/session/{session_id}/strategy/`
- **Template**: `search_strategy/strategy_detail.html`
- **Permissions**: Login required, session ownership
- **Features**:
  - PIC term display with statistics
  - Generated query preview
  - Export options
  - Navigation to next steps

### 4.2 Forms

#### SearchStrategyForm
```python
class SearchStrategyForm(forms.ModelForm):
    """Form for creating and editing search strategies."""
    
    # Override fields for better widgets
    population_terms = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control tag-input',
            'placeholder': 'Enter population terms separated by commas',
            'rows': 3
        }),
        required=False
    )
    
    # Custom domain input
    custom_domains = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control domain-input',
            'placeholder': 'Enter organization domains (e.g., nice.org.uk)',
            'rows': 2
        }),
        required=False
    )
    
    class Meta:
        model = SearchStrategy
        fields = ['population_terms', 'interest_terms', 'context_terms']
    
    def clean(self):
        """Validate PIC framework completeness."""
        cleaned_data = super().clean()
        # Validation logic here
        return cleaned_data
```

### 4.3 URL Configuration

```python
app_name = 'search_strategy'

urlpatterns = [
    # Strategy management
    path('session/<uuid:session_id>/strategy/create/', 
         views.SearchStrategyCreateView.as_view(), 
         name='create'),
    path('session/<uuid:session_id>/strategy/edit/', 
         views.SearchStrategyUpdateView.as_view(), 
         name='edit'),
    path('session/<uuid:session_id>/strategy/', 
         views.SearchStrategyDetailView.as_view(), 
         name='detail'),
    
    # API endpoints
    path('api/preview/', 
         views.query_preview_api, 
         name='api_preview'),
    path('api/validate/', 
         views.validate_strategy_api, 
         name='api_validate'),
]
```

## 5. Business Logic

### 5.1 Services

#### QueryBuilder Service
- Constructs Boolean queries from PIC terms
- Handles operator precedence and escaping
- Manages file type filters
- Optimizes query length for search engines

#### StrategyValidator Service
- Validates PIC framework completeness
- Checks domain validity
- Ensures file type compatibility
- Provides detailed error messages

### 5.2 Managers

#### SearchStrategyManager
```python
class SearchStrategyManager(models.Manager):
    """Custom manager for SearchStrategy model."""
    
    def complete_strategies(self):
        """Get all complete strategies."""
        return self.filter(is_complete=True)
    
    def for_user(self, user):
        """Get strategies for a specific user."""
        return self.filter(user=user)
    
    def with_stats(self):
        """Annotate strategies with statistics."""
        return self.annotate(
            total_terms=Count('population_terms') + 
                       Count('interest_terms') + 
                       Count('context_terms')
        )
```

### 5.3 Utilities

#### Term Processing
- Clean and normalize input terms
- Remove duplicates within categories
- Handle special characters and quotes
- Validate term length and content

#### Export Utilities
- Export strategy as JSON
- Generate CSV for documentation
- Create plain text query list
- Support for PRISMA reporting

## 6. Testing Requirements

### 6.1 Unit Tests

#### Model Tests (`test_models.py`)
- SearchStrategy creation and validation
- Query generation with various configurations
- PIC framework validation
- Domain and file type handling
- Stats calculation accuracy

#### Form Tests (`test_forms.py`)
- Form validation with valid/invalid data
- XSS prevention and input sanitization
- Term processing and normalization
- Custom domain validation
- Error message accuracy

#### View Tests (`test_views.py`)
- Authentication and authorization
- Session ownership validation
- Status-based access control
- Form submission handling
- AJAX endpoint responses

### 6.2 Integration Tests

#### Workflow Integration (`test_integration.py`)
- Session status transitions after strategy creation
- Navigation flow from dashboard to strategy
- Query generation and storage
- Activity logging integration
- Cross-app data consistency

### 6.3 Security Tests

- CSRF protection on all forms
- XSS prevention in term inputs
- SQL injection prevention (ORM usage)
- Session ownership enforcement
- Rate limiting on API endpoints

## 7. Performance Optimization

### 7.1 Database Optimization
- Indexes on foreign keys and lookup fields
- Efficient query generation without N+1 problems
- Bulk operations for query creation
- Prepared statements for repeated queries

### 7.2 Frontend Optimization
- Debounced input for real-time preview
- Lazy loading of query previews
- Minimized JavaScript and CSS
- Efficient DOM manipulation

### 7.3 Caching Strategy
- Cache generated queries for repeated views
- Session-based caching for form data
- API response caching with invalidation

## 8. Security Considerations

### 8.1 Authentication & Authorization
- All views require authentication
- Session ownership validation on all operations
- Status-based permissions (edit only in draft)
- Audit trail for all modifications

### 8.2 Input Validation
- Server-side validation for all inputs
- XSS prevention through template escaping
- Term content validation (alphanumeric + safe chars)
- Domain format validation

### 8.3 Data Protection
- No sensitive data in search terms
- Activity logging with user association
- Secure session handling
- HTTPS enforcement in production

## 9. Phase Implementation

### Phase 1 - Current Implementation ✅
- Complete PIC framework model
- Tag-based input interface
- Multi-domain support
- Query generation engine
- Basic file type filtering (PDF + Word)
- AJAX preview functionality
- Integration with session workflow

### Phase 2 - Future Enhancements
- Advanced search operators (proximity, wildcards)
- Query templates and saved searches
- Machine learning query suggestions
- Integration with reference databases
- Bulk import from bibliography files
- Advanced file type filters
- Search history and versioning

## 10. Development Checklist

### Initial Setup ✅
- [x] Create app structure
- [x] Configure in INSTALLED_APPS
- [x] Set up URL routing
- [x] Create base templates

### Models & Database ✅
- [x] Implement SearchStrategy model
- [x] Implement SearchQuery model
- [x] Create and run migrations
- [x] Set up admin interface

### Forms & Validation ✅
- [x] Create SearchStrategyForm
- [x] Implement validation logic
- [x] Add security measures
- [x] Test form processing

### Views & Templates ✅
- [x] Implement CRUD views
- [x] Create form templates
- [x] Build detail view
- [x] Add navigation elements

### Business Logic ✅
- [x] Query generation engine
- [x] Validation services
- [x] Export utilities
- [x] Activity logging

### Testing ✅
- [x] Unit tests for models
- [x] Form validation tests
- [x] View permission tests
- [x] Integration tests

### Documentation
- [x] Code documentation
- [x] API documentation
- [ ] User guide
- [ ] Developer notes

## 11. Success Metrics

### Functional Metrics
- All PIC framework categories supported
- Multi-domain query generation working
- File type filtering operational
- Real-time preview responsive (<500ms)

### Quality Metrics
- 95%+ test coverage
- No critical security vulnerabilities
- Page load time <2 seconds
- Form validation feedback <100ms

### User Experience Metrics
- Intuitive tag-based input
- Clear validation messages
- Smooth workflow progression
- Helpful query preview

## 12. References

- Master PRD: [docs/PRD.md](../PRD.md)
- Review Manager PRD: [docs/review-manager/review-manager-prd.md](../review-manager/review-manager-prd.md)
- Implementation Tasks: [docs/search-strategy/tasks-search-strategy-implementation.md](tasks-search-strategy-implementation.md)
- Django ArrayField Documentation
- PostgreSQL Full-Text Search Documentation
- PRISMA Guidelines for Systematic Reviews