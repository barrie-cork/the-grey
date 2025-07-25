import uuid
from typing import Any, Dict, List, Optional
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()


class SearchQuery(models.Model):
    """
    Represents a search query following the PIC framework.
    PIC: Population, Interest/Intervention, Context
    """
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationship to SearchSession
    session = models.ForeignKey(
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='search_queries',
        help_text="The search session this query belongs to"
    )
    
    # PIC Framework fields
    population = models.TextField(
        help_text="Target population for the search (e.g., 'elderly adults', 'software developers')"
    )
    interest = models.TextField(
        help_text="The intervention, exposure, or phenomenon of interest"
    )
    context = models.TextField(
        help_text="The context or setting (e.g., 'healthcare', 'education', 'workplace')"
    )
    
    # Query construction
    query_string = models.TextField(
        help_text="The final constructed search query"
    )
    search_engines = models.JSONField(
        default=list,
        help_text="List of search engines to use (e.g., ['google', 'bing'])"
    )
    
    # Query parameters
    include_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Additional keywords to include"
    )
    exclude_keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Keywords to exclude from results"
    )
    
    # Search filters
    date_from = models.DateField(
        null=True,
        blank=True,
        help_text="Start date for results filter"
    )
    date_to = models.DateField(
        null=True,
        blank=True,
        help_text="End date for results filter"
    )
    languages = models.JSONField(
        default=list,
        blank=True,
        help_text="List of language codes to filter by (e.g., ['en', 'es'])"
    )
    document_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Types of documents to include (e.g., ['pdf', 'report', 'thesis'])"
    )
    
    # Query metadata
    is_primary = models.BooleanField(
        default=True,
        help_text="Whether this is a primary query (vs. supplementary)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Order of execution for multiple queries"
    )
    max_results = models.IntegerField(
        default=100,
        help_text="Maximum number of results to retrieve"
    )
    
    # Status tracking
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this query should be executed"
    )
    last_executed = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this query was last executed"
    )
    execution_count = models.IntegerField(
        default=0,
        help_text="Number of times this query has been executed"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'search_queries'
        ordering = ['session', 'order', 'created_at']
        indexes = [
            models.Index(fields=['session', 'is_active']),
            models.Index(fields=['is_primary']),
        ]
        verbose_name_plural = 'Search queries'
    
    def __str__(self) -> str:
        return f"Query for {self.session.title}: {self.query_string[:50]}..."
    
    def clean(self) -> None:
        """Validate query fields."""
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValidationError("Start date must be before end date")
        
        if self.max_results < 1:
            raise ValidationError("Max results must be at least 1")
        
        if not self.population and not self.interest and not self.context:
            raise ValidationError("At least one PIC field must be filled")
    
    def generate_query_string(self) -> str:
        """
        Generate the search query string based on PIC fields and keywords.
        This is a basic implementation that can be enhanced.
        """
        components = []
        
        # Add PIC components
        if self.population:
            components.append(f'("{self.population}")')
        if self.interest:
            components.append(f'("{self.interest}")')
        if self.context:
            components.append(f'("{self.context}")')
        
        # Add include keywords
        for keyword in self.include_keywords:
            components.append(keyword)
        
        # Build base query
        base_query = " AND ".join(components)
        
        # Add exclusions
        if self.exclude_keywords:
            exclusions = " ".join([f"-{keyword}" for keyword in self.exclude_keywords])
            base_query = f"{base_query} {exclusions}"
        
        return base_query.strip()
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-generate query string if not provided."""
        if not self.query_string:
            self.query_string = self.generate_query_string()
        super().save(*args, **kwargs)


class QueryTemplate(models.Model):
    """
    Reusable search query templates for common search patterns.
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
    
    def create_query(self, session: 'SearchSession', **kwargs: Any) -> 'SearchQuery':
        """
        Create a new SearchQuery from this template.
        
        Args:
            session: The SearchSession to attach the query to
            **kwargs: Values to substitute in template placeholders
        
        Returns:
            SearchQuery instance
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
        
        # Create the query
        query = SearchQuery.objects.create(
            session=session,
            population=population,
            interest=interest,
            context=context,
            include_keywords=self.default_keywords,
            exclude_keywords=self.default_exclusions,
            search_engines=self.default_engines or ['google']
        )
        
        # Increment usage count
        self.usage_count += 1
        self.save(update_fields=['usage_count'])
        
        return query
