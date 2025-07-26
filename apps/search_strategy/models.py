import uuid
from typing import Any, Dict, List, Optional
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.review_manager.models import SearchSession

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


# Keep QueryTemplate for backward compatibility but mark as deprecated
class QueryTemplate(models.Model):
    """
    DEPRECATED: Reusable search query templates for common search patterns.
    This model is kept for backward compatibility. New implementations should use SearchStrategy.
    """
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template metadata
    name = models.CharField(
        max_length=255,
        help_text="Name of the template"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of when to use this template"
    )
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Category for organizing templates"
    )
    
    # Template owner
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='query_templates',
        help_text="User who created this template"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this template is available to all users"
    )
    
    # Template fields (with placeholders)
    population_template = models.TextField(
        blank=True,
        help_text="Population template with placeholders (e.g., '{age_group} with {condition}')"
    )
    interest_template = models.TextField(
        blank=True,
        help_text="Interest/Intervention template"
    )
    context_template = models.TextField(
        blank=True,
        help_text="Context template"
    )
    
    # Default parameters
    default_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Default keywords to include"
    )
    default_exclusions = models.JSONField(
        default=list,
        blank=True,
        help_text="Default keywords to exclude"
    )
    default_engines = models.JSONField(
        default=list,
        blank=True,
        help_text="Default search engines"
    )
    
    # Usage tracking
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this template has been used"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'query_templates'
        ordering = ['-usage_count', 'name']
        indexes = [
            models.Index(fields=['is_public', 'category']),
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.category or 'Uncategorized'})"
    
    def create_query_from_template(self, session: SearchSession, **kwargs: Any) -> SearchStrategy:
        """
        DEPRECATED: Create a new SearchStrategy from this template.
        This method is kept for backward compatibility.
        """
        # Simple template substitution
        population = self.population_template
        interest = self.interest_template
        context = self.context_template
        
        # Replace placeholders with provided values
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            population = population.replace(placeholder, str(value))
            interest = interest.replace(placeholder, str(value))
            context = context.replace(placeholder, str(value))
        
        # Create the strategy with basic terms
        strategy = SearchStrategy.objects.create(
            session=session,
            user=session.owner,
            population_terms=[population] if population else [],
            interest_terms=[interest] if interest else [],
            context_terms=[context] if context else [],
            search_config={
                'domains': [],
                'include_general_search': True,
                'file_types': ['pdf'],
                'search_type': 'google'
            }
        )
        
        # Increment usage count
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
        
        return strategy
