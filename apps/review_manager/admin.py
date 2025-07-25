from django.contrib import admin
from .models import SearchSession, SessionActivity


@admin.register(SearchSession)
class SearchSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'owner', 'created_at', 'progress_percentage']
    list_filter = ['status', 'created_at', 'owner']
    search_fields = ['title', 'description', 'owner__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'progress_percentage', 'inclusion_rate']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'description', 'status', 'owner')
        }),
        ('Statistics', {
            'fields': ('total_queries', 'total_results', 'reviewed_results', 
                      'included_results', 'progress_percentage', 'inclusion_rate')
        }),
        ('Metadata', {
            'fields': ('notes', 'tags')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'started_at', 'completed_at')
        })
    )
    
    actions = ['set_status_draft', 'set_status_defining_search', 'set_status_ready_to_execute']
    
    def set_status_draft(self, request, queryset):
        for session in queryset:
            if session.can_transition_to('draft'):
                session.status = 'draft'
                session.save()
        self.message_user(request, f"Updated {queryset.count()} sessions to Draft status")
    set_status_draft.short_description = "Set status to Draft"
    
    def set_status_defining_search(self, request, queryset):
        for session in queryset:
            if session.can_transition_to('defining_search'):
                session.status = 'defining_search'
                session.save()
        self.message_user(request, f"Updated {queryset.count()} sessions to Defining Search status")
    set_status_defining_search.short_description = "Set status to Defining Search"
    
    def set_status_ready_to_execute(self, request, queryset):
        for session in queryset:
            if session.can_transition_to('ready_to_execute'):
                session.status = 'ready_to_execute'
                session.save()
        self.message_user(request, f"Updated {queryset.count()} sessions to Ready to Execute status")
    set_status_ready_to_execute.short_description = "Set status to Ready to Execute"


@admin.register(SessionActivity)
class SessionActivityAdmin(admin.ModelAdmin):
    list_display = ['activity_type', 'session', 'user', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['description', 'session__title', 'user__username']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = (
        (None, {
            'fields': ('id', 'session', 'user', 'activity_type')
        }),
        ('Details', {
            'fields': ('description', 'metadata')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
