from django.contrib import admin
from .models import SearchQuery, QueryTemplate


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ['session', 'population', 'is_primary', 'is_active', 'order', 'last_executed']
    list_filter = ['is_primary', 'is_active', 'created_at', 'last_executed']
    search_fields = ['population', 'interest', 'context', 'query_string']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_executed', 'execution_count']
    
    fieldsets = (
        ('Session', {
            'fields': ('id', 'session')
        }),
        ('PIC Framework', {
            'fields': ('population', 'interest', 'context')
        }),
        ('Query Details', {
            'fields': ('query_string', 'search_engines', 'include_keywords', 'exclude_keywords')
        }),
        ('Filters', {
            'fields': ('date_from', 'date_to', 'languages', 'document_types')
        }),
        ('Metadata', {
            'fields': ('is_primary', 'order', 'max_results', 'is_active')
        }),
        ('Execution', {
            'fields': ('last_executed', 'execution_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    actions = ['activate_queries', 'deactivate_queries', 'reset_execution_count']
    
    def activate_queries(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} queries")
    activate_queries.short_description = "Activate selected queries"
    
    def deactivate_queries(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} queries")
    deactivate_queries.short_description = "Deactivate selected queries"
    
    def reset_execution_count(self, request, queryset):
        updated = queryset.update(execution_count=0, last_executed=None)
        self.message_user(request, f"Reset execution count for {updated} queries")
    reset_execution_count.short_description = "Reset execution count"


@admin.register(QueryTemplate)
class QueryTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'created_by', 'is_public', 'usage_count']
    list_filter = ['is_public', 'category', 'created_at']
    search_fields = ['name', 'description', 'category']
    readonly_fields = ['id', 'usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'name', 'description', 'category')
        }),
        ('Template Fields', {
            'fields': ('population_template', 'interest_template', 'context_template')
        }),
        ('Default Parameters', {
            'fields': ('default_keywords', 'default_exclusions', 'default_engines')
        }),
        ('Metadata', {
            'fields': ('created_by', 'is_public', 'usage_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
