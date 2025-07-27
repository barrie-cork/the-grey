# Reporting Product Requirements Document

**Project:** Thesis Grey - Systematic Grey Literature Review Tool  
**App:** Reporting  
**Version:** 1.0  
**Date:** 2025-01-25  
**App Path:** `apps/reporting/`  
**Master PRD:** [docs/PRD.md](../PRD.md)  
**Dependencies:** review_results, results_manager, review_manager, accounts  
**Status:** Planned

## 1. Executive Summary

### 1.1 Key Responsibilities
The Reporting app provides comprehensive PRISMA-compliant reporting and data export capabilities for systematic grey literature reviews. It generates flow diagrams, statistical summaries, and exports in multiple formats to support academic publishing, regulatory submissions, and research documentation requirements. The app serves as the final output stage, transforming reviewed results into publication-ready materials.

### 1.2 Integration Points
- **Review Results**: Consumes review tag assignments and notes for inclusion/exclusion statistics
- **Results Manager**: Accesses processed search results and deduplication data
- **Review Manager**: Uses session metadata and workflow information
- **Accounts**: Associates all reports with authenticated users for access control

## 2. Technical Architecture

### 2.1 Technology Stack
- **Framework**: Django 4.2 with Class-Based Views (CBVs)
- **Database**: PostgreSQL with UUID primary keys
- **Export Libraries**: 
  - **PDF**: WeasyPrint for PRISMA flow diagrams
  - **Excel**: openpyxl for structured data exports
  - **Word**: python-docx for document generation
  - **Charts**: matplotlib/plotly for visualization
- **File Storage**: Django FileField with organized directory structure
- **Background Tasks**: Celery for large report generation
- **Caching**: Redis for expensive statistical calculations

### 2.2 App Structure
```
apps/reporting/
├── __init__.py
├── apps.py
├── models.py           # ExportReport model (already implemented)
├── views.py            # Report generation and download views
├── forms.py            # Report configuration forms
├── urls.py             # URL patterns for reporting interface
├── admin.py            # Django admin configuration
├── services.py         # Report generation business logic
├── managers.py         # Custom model managers
├── generators/         # Report generation modules
│   ├── __init__.py
│   ├── prisma_flow.py     # PRISMA flow diagram generator
│   ├── statistics.py      # Statistical analysis
│   ├── exports.py         # Data export utilities
│   └── templates/         # Report templates
│       ├── prisma_flow.html
│       ├── full_report.html
│       └── study_list.html
├── tasks.py            # Celery background tasks
├── utils.py            # Helper functions
├── signals.py          # Django signals for cleanup
├── templates/
│   └── reporting/
│       ├── base.html
│       ├── dashboard.html
│       ├── report_detail.html
│       ├── generate_report.html
│       └── partials/
│           ├── statistics_card.html
│           ├── export_options.html
│           └── download_links.html
├── static/
│   └── reporting/
│       ├── css/
│       │   └── reports.css
│       └── js/
│           ├── report_generation.js
│           └── statistics.js
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_services.py
│   ├── test_generators.py
│   └── factories.py
└── migrations/
```

### 2.3 Database Models

#### ExportReport Model (Already Implemented)
```python
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ExportReport(models.Model):
    """
    Tracks generated reports and exports for PRISMA compliance.
    Provides audit trail and file management for all report types.
    """
    
    REPORT_TYPES = [
        ('prisma_flow', 'PRISMA Flow Diagram'),
        ('full_report', 'Full PRISMA Report'),
        ('included_studies', 'Included Studies List'),
        ('excluded_studies', 'Excluded Studies with Reasons'),
        ('search_strategy', 'Search Strategy Documentation'),
        ('data_export', 'Raw Data Export'),
    ]
    
    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
        ('xlsx', 'Excel Spreadsheet'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('bibtex', 'BibTeX'),
    ]
    
    # Primary key and relationships
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='export_reports'
    )
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    
    # Report configuration
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    export_format = models.CharField(max_length=10, choices=EXPORT_FORMATS)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parameters = models.JSONField(default=dict)
    
    # File information
    file_name = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='reports/%Y/%m/')
    file_size_bytes = models.BigIntegerField()
    
    # Statistics
    total_results = models.IntegerField(default=0)
    included_results = models.IntegerField(default=0)
    excluded_results = models.IntegerField(default=0)
    
    # Lifecycle management
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'export_reports'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['session', 'report_type']),
            models.Index(fields=['generated_by', '-generated_at']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"
    
    @property
    def is_expired(self):
        """Check if report file has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def file_size_human(self):
        """Return human-readable file size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size_bytes < 1024.0:
                return f"{self.file_size_bytes:.1f} {unit}"
            self.file_size_bytes /= 1024.0
        return f"{self.file_size_bytes:.1f} TB"
```

## 3. API Endpoints

### 3.1 Phase 1 Endpoints (Current Implementation)
While the Reporting app primarily uses server-side rendering in Phase 1, these endpoints support report generation and download:

#### Report Generation Endpoints
```python
# Report generation status
GET /api/reporting/session/{session_id}/generate/{report_type}/
    Response: {
        "task_id": "uuid",
        "status": "pending|in_progress|completed|failed",
        "progress": 85,
        "estimated_time_remaining": 30
    }

# Report download
GET /api/reporting/download/{report_id}/
    Response: File download with proper headers

# Session statistics
GET /api/reporting/session/{session_id}/statistics/
    Response: {
        "total_results": 150,
        "included_results": 45,
        "excluded_results": 95,
        "maybe_results": 10,
        "prisma_flow_data": {
            "identification": 150,
            "screening": 150,
            "eligibility": 55,
            "included": 45
        },
        "domain_breakdown": {
            "pubmed.ncbi.nlm.nih.gov": 30,
            "scholar.google.com": 25,
            "researchgate.net": 15
        },
        "file_type_breakdown": {
            "pdf": 80,
            "html": 50,
            "doc": 20
        }
    }
```

### 3.2 Phase 2 API Endpoints (Future RESTful API)
```python
# Full RESTful API implementation
GET    /api/v1/reporting/sessions/{session_id}/reports/
POST   /api/v1/reporting/sessions/{session_id}/reports/
GET    /api/v1/reporting/reports/{report_id}/
DELETE /api/v1/reporting/reports/{report_id}/
POST   /api/v1/reporting/bulk-export/
```

## 4. User Interface

### 4.1 Views

#### ReportingDashboardView
```python
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from apps.reporting.models import ExportReport
from apps.review_manager.models import SearchSession

class ReportingDashboardView(LoginRequiredMixin, ListView):
    """
    Main dashboard showing available reports and generation options.
    """
    model = ExportReport
    template_name = 'reporting/dashboard.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        return ExportReport.objects.filter(
            session__created_by=self.request.user
        ).select_related('session', 'generated_by').order_by('-generated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get sessions ready for reporting
        ready_sessions = SearchSession.objects.filter(
            created_by=self.request.user,
            status__in=['completed', 'under_review']
        ).annotate(
            result_count=Count('processed_results'),
            tagged_count=Count(
                'review_tag_assignments',
                filter=Q(review_tag_assignments__user=self.request.user)
            )
        )
        
        context['ready_sessions'] = ready_sessions
        context['total_reports'] = self.get_queryset().count()
        
        return context
```

#### ReportGenerationView
```python
from django.views.generic import FormView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from apps.reporting.forms import ReportGenerationForm
from apps.reporting.tasks import generate_report_task

class ReportGenerationView(LoginRequiredMixin, SuccessMessageMixin, FormView):
    """
    View for configuring and initiating report generation.
    """
    form_class = ReportGenerationForm
    template_name = 'reporting/generate_report.html'
    success_message = 'Report generation started. You will be notified when complete.'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['session_id'] = self.kwargs['session_id']
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        session_id = self.kwargs['session_id']
        
        # Initiate background task
        task = generate_report_task.delay(
            session_id=session_id,
            report_type=form.cleaned_data['report_type'],
            export_format=form.cleaned_data['export_format'],
            parameters=form.cleaned_data,
            user_id=self.request.user.id
        )
        
        # Store task ID for progress tracking
        self.request.session[f'report_task_{session_id}'] = str(task.id)
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('reporting:dashboard')
```

#### SessionStatisticsView
```python
from django.views.generic import DetailView
from django.http import JsonResponse
from apps.reporting.services import StatisticsService

class SessionStatisticsView(LoginRequiredMixin, DetailView):
    """
    AJAX view providing session statistics for report generation.
    """
    model = SearchSession
    pk_url_kwarg = 'session_id'
    
    def get_queryset(self):
        return SearchSession.objects.filter(created_by=self.request.user)
    
    def get(self, request, *args, **kwargs):
        session = self.get_object()
        stats_service = StatisticsService()
        
        statistics = {
            'basic_stats': stats_service.get_basic_statistics(session, request.user),
            'prisma_flow': stats_service.get_prisma_flow_data(session, request.user),
            'domain_breakdown': stats_service.get_domain_breakdown(session),
            'file_type_breakdown': stats_service.get_file_type_breakdown(session),
            'quality_distribution': stats_service.get_quality_distribution(session),
            'temporal_analysis': stats_service.get_temporal_analysis(session),
        }
        
        return JsonResponse(statistics)
```

### 4.2 Forms

#### ReportGenerationForm
```python
from django import forms
from apps.reporting.models import ExportReport
from apps.review_manager.models import SearchSession

class ReportGenerationForm(forms.Form):
    """
    Form for configuring report generation parameters.
    """
    report_type = forms.ChoiceField(
        choices=ExportReport.REPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    export_format = forms.ChoiceField(
        choices=ExportReport.EXPORT_FORMATS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Report customization options
    include_search_strategy = forms.BooleanField(
        required=False,
        initial=True,
        label='Include search strategy details'
    )
    include_quality_scores = forms.BooleanField(
        required=False,
        initial=True,
        label='Include quality assessment scores'
    )
    include_notes = forms.BooleanField(
        required=False,
        initial=True,
        label='Include reviewer notes'
    )
    include_duplicates = forms.BooleanField(
        required=False,
        initial=False,
        label='Include duplicate results'
    )
    
    # PRISMA flow diagram options
    flow_diagram_style = forms.ChoiceField(
        choices=[
            ('standard', 'Standard PRISMA 2020'),
            ('detailed', 'Detailed with sub-categories'),
            ('minimal', 'Minimal version'),
        ],
        initial='standard',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Export filtering
    min_quality_score = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=1,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': '0.0'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.session_id = kwargs.pop('session_id')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        
        # Customize form based on session data
        self._customize_for_session()
    
    def _customize_for_session(self):
        """Customize form options based on session data."""
        try:
            session = SearchSession.objects.get(pk=self.session_id)
            
            # Disable certain options if no data available
            if not session.review_tag_assignments.filter(user=self.user).exists():
                self.fields['include_notes'].widget.attrs['disabled'] = True
                self.fields['include_quality_scores'].widget.attrs['disabled'] = True
        
        except SearchSession.DoesNotExist:
            pass
    
    def clean(self):
        cleaned_data = super().clean()
        report_type = cleaned_data.get('report_type')
        export_format = cleaned_data.get('export_format')
        
        # Validate format compatibility
        incompatible_combinations = [
            ('prisma_flow', 'csv'),
            ('prisma_flow', 'json'),
            ('full_report', 'csv'),
        ]
        
        if (report_type, export_format) in incompatible_combinations:
            raise forms.ValidationError(
                f"{report_type} reports cannot be exported as {export_format}"
            )
        
        return cleaned_data
```

### 4.3 URLs
```python
# apps/reporting/urls.py
from django.urls import path
from apps.reporting import views

app_name = 'reporting'

urlpatterns = [
    # Main reporting interface
    path('', views.ReportingDashboardView.as_view(), name='dashboard'),
    
    # Report generation
    path(
        'session/<uuid:session_id>/generate/',
        views.ReportGenerationView.as_view(),
        name='generate_report'
    ),
    path(
        'session/<uuid:session_id>/summary/',
        views.SessionSummaryView.as_view(),
        name='session_summary'
    ),
    
    # Report management
    path(
        'report/<uuid:report_id>/',
        views.ReportDetailView.as_view(),
        name='report_detail'
    ),
    path(
        'report/<uuid:report_id>/download/',
        views.ReportDownloadView.as_view(),
        name='report_download'
    ),
    path(
        'report/<uuid:report_id>/delete/',
        views.ReportDeleteView.as_view(),
        name='report_delete'
    ),
    
    # AJAX endpoints
    path(
        'api/session/<uuid:session_id>/statistics/',
        views.SessionStatisticsView.as_view(),
        name='session_statistics'
    ),
    path(
        'api/report/<uuid:report_id>/status/',
        views.ReportStatusView.as_view(),
        name='report_status'
    ),
    path(
        'api/session/<uuid:session_id>/preview/',
        views.ReportPreviewView.as_view(),
        name='report_preview'
    ),
]
```

## 5. Business Logic

### 5.1 Services Layer

#### StatisticsService
```python
# apps/reporting/services.py
from django.db.models import Count, Q, Avg
from django.utils import timezone
from apps.review_results.models import ReviewTagAssignment
from apps.results_manager.models import ProcessedResult
from apps.review_manager.models import SearchSession

class StatisticsService:
    """
    Core business logic for generating report statistics.
    """
    
    def get_basic_statistics(self, session, user):
        """Get basic review statistics."""
        total_results = session.processed_results.count()
        
        tag_counts = ReviewTagAssignment.objects.filter(
            session=session,
            user=user
        ).values('tag__name').annotate(count=Count('id'))
        
        tag_breakdown = {item['tag__name']: item['count'] for item in tag_counts}
        
        return {
            'total_results': total_results,
            'tagged_results': sum(tag_breakdown.values()),
            'untagged_results': total_results - sum(tag_breakdown.values()),
            'included_results': tag_breakdown.get('Include', 0),
            'excluded_results': tag_breakdown.get('Exclude', 0),
            'maybe_results': tag_breakdown.get('Maybe', 0),
            'tag_breakdown': tag_breakdown,
        }
    
    def get_prisma_flow_data(self, session, user):
        """Generate PRISMA flow diagram data."""
        stats = self.get_basic_statistics(session, user)
        
        # Calculate PRISMA flow stages
        identification = stats['total_results']
        screening = identification - session.processed_results.filter(
            is_duplicate=True
        ).count()
        
        eligibility = stats['included_results'] + stats['maybe_results']
        included = stats['included_results']
        
        excluded_screening = stats['excluded_results']
        excluded_eligibility = stats['maybe_results']  # Assuming maybe becomes excluded
        
        return {
            'identification': {
                'total': identification,
                'databases': self._get_database_counts(session),
            },
            'screening': {
                'total': screening,
                'duplicates_removed': identification - screening,
                'excluded': excluded_screening,
            },
            'eligibility': {
                'assessed': eligibility,
                'excluded': excluded_eligibility,
                'excluded_reasons': self._get_exclusion_reasons(session, user),
            },
            'included': {
                'total': included,
                'qualitative': included,
                'quantitative': included,  # Phase 2: distinguish if needed
            }
        }
    
    def get_domain_breakdown(self, session):
        """Analyze results by domain."""
        return session.processed_results.values(
            'raw_result__domain'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
    
    def get_file_type_breakdown(self, session):
        """Analyze results by file type."""
        return session.processed_results.values(
            'file_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
    
    def get_quality_distribution(self, session):
        """Analyze quality score distribution."""
        return {
            'average_quality': session.processed_results.aggregate(
                avg=Avg('processing_quality_score')
            )['avg'] or 0,
            'distribution': session.processed_results.extra(
                select={
                    'quality_range': '''
                        CASE 
                            WHEN processing_quality_score >= 0.8 THEN 'High (0.8-1.0)'
                            WHEN processing_quality_score >= 0.6 THEN 'Medium (0.6-0.8)'
                            WHEN processing_quality_score >= 0.4 THEN 'Low (0.4-0.6)'
                            ELSE 'Very Low (0.0-0.4)'
                        END
                    '''
                }
            ).values('quality_range').annotate(count=Count('id'))
        }
    
    def get_temporal_analysis(self, session):
        """Analyze when results were processed/reviewed."""
        return {
            'processing_timeline': session.processed_results.extra(
                select={'date': 'DATE(processed_at)'}
            ).values('date').annotate(count=Count('id')).order_by('date'),
            
            'review_timeline': ReviewTagAssignment.objects.filter(
                session=session
            ).extra(
                select={'date': 'DATE(created_at)'}
            ).values('date').annotate(count=Count('id')).order_by('date')
        }
    
    def _get_database_counts(self, session):
        """Get count of results by database/source."""
        return session.processed_results.values(
            'raw_result__search_execution__search_query__query_type'
        ).annotate(count=Count('id'))
    
    def _get_exclusion_reasons(self, session, user):
        """Get breakdown of exclusion reasons."""
        return ReviewTagAssignment.objects.filter(
            session=session,
            user=user,
            tag__name='Exclude'
        ).values('reason').annotate(count=Count('id')).order_by('-count')
```

#### ReportGenerationService
```python
class ReportGenerationService:
    """
    Handles the generation of different report types.
    """
    
    def __init__(self, session, user, parameters=None):
        self.session = session
        self.user = user
        self.parameters = parameters or {}
        self.stats_service = StatisticsService()
    
    def generate_prisma_flow(self, format='pdf'):
        """Generate PRISMA flow diagram."""
        flow_data = self.stats_service.get_prisma_flow_data(self.session, self.user)
        
        if format == 'pdf':
            return self._generate_prisma_pdf(flow_data)
        elif format == 'docx':
            return self._generate_prisma_docx(flow_data)
        else:
            raise ValueError(f"Unsupported format for PRISMA flow: {format}")
    
    def generate_full_report(self, format='pdf'):
        """Generate comprehensive PRISMA report."""
        context = {
            'session': self.session,
            'statistics': self.stats_service.get_basic_statistics(self.session, self.user),
            'prisma_flow': self.stats_service.get_prisma_flow_data(self.session, self.user),
            'domain_breakdown': self.stats_service.get_domain_breakdown(self.session),
            'quality_analysis': self.stats_service.get_quality_distribution(self.session),
            'generated_at': timezone.now(),
            'generated_by': self.user,
        }
        
        if format == 'pdf':
            return self._generate_full_report_pdf(context)
        elif format == 'docx':
            return self._generate_full_report_docx(context)
        else:
            raise ValueError(f"Unsupported format for full report: {format}")
    
    def generate_study_list(self, list_type='included', format='xlsx'):
        """Generate list of included/excluded studies."""
        if list_type == 'included':
            assignments = ReviewTagAssignment.objects.filter(
                session=self.session,
                user=self.user,
                tag__name='Include'
            ).select_related('processed_result', 'tag')
        elif list_type == 'excluded':
            assignments = ReviewTagAssignment.objects.filter(
                session=self.session,
                user=self.user,
                tag__name='Exclude'
            ).select_related('processed_result', 'tag')
        else:
            assignments = ReviewTagAssignment.objects.filter(
                session=self.session,
                user=self.user
            ).select_related('processed_result', 'tag')
        
        if format == 'xlsx':
            return self._generate_excel_study_list(assignments, list_type)
        elif format == 'csv':
            return self._generate_csv_study_list(assignments, list_type)
        elif format == 'bibtex':
            return self._generate_bibtex_study_list(assignments, list_type)
        else:
            raise ValueError(f"Unsupported format for study list: {format}")
    
    def _generate_prisma_pdf(self, flow_data):
        """Generate PRISMA flow diagram as PDF using WeasyPrint."""
        from weasyprint import HTML, CSS
        from django.template.loader import render_to_string
        
        html_content = render_to_string(
            'reporting/generators/prisma_flow.html',
            {
                'flow_data': flow_data,
                'session': self.session,
                'style': self.parameters.get('flow_diagram_style', 'standard')
            }
        )
        
        css_content = CSS(filename='apps/reporting/static/reporting/css/prisma_flow.css')
        
        pdf_file = HTML(string=html_content).write_pdf(stylesheets=[css_content])
        return pdf_file
    
    def _generate_excel_study_list(self, assignments, list_type):
        """Generate Excel file with study details."""
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        from io import BytesIO
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{list_type.title()} Studies"
        
        # Headers
        headers = [
            'Title', 'URL', 'Domain', 'File Type', 'Quality Score',
            'Tag', 'Reason', 'Review Date', 'Notes'
        ]
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        
        # Data rows
        for row_num, assignment in enumerate(assignments, 2):
            result = assignment.processed_result
            
            ws.cell(row=row_num, column=1, value=result.title)
            ws.cell(row=row_num, column=2, value=result.normalized_url)
            ws.cell(row=row_num, column=3, value=result.raw_result.domain if result.raw_result else '')
            ws.cell(row=row_num, column=4, value=result.file_type)
            ws.cell(row=row_num, column=5, value=result.processing_quality_score)
            ws.cell(row=row_num, column=6, value=assignment.tag.name)
            ws.cell(row=row_num, column=7, value=assignment.reason or '')
            ws.cell(row=row_num, column=8, value=assignment.updated_at.strftime('%Y-%m-%d'))
            
            # Get notes
            notes = result.notes.filter(
                user=self.user,
                session=self.session
            ).values_list('text', flat=True)
            ws.cell(row=row_num, column=9, value='; '.join(notes))
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        output = BytesIO()
        wb.save(output)
        return output.getvalue()
```

### 5.2 Background Tasks

#### Celery Tasks
```python
# apps/reporting/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.utils import timezone
from apps.reporting.models import ExportReport
from apps.reporting.services import ReportGenerationService
from apps.review_manager.models import SearchSession
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@shared_task(bind=True)
def generate_report_task(self, session_id, report_type, export_format, parameters, user_id):
    """
    Background task for generating reports.
    """
    try:
        # Update task status
        self.update_state(state='IN_PROGRESS', meta={'progress': 10})
        
        # Get session and user
        session = SearchSession.objects.get(pk=session_id)
        user = User.objects.get(pk=user_id)
        
        self.update_state(state='IN_PROGRESS', meta={'progress': 20})
        
        # Initialize report generation service
        generator = ReportGenerationService(session, user, parameters)
        
        self.update_state(state='IN_PROGRESS', meta={'progress': 30})
        
        # Generate report based on type
        if report_type == 'prisma_flow':
            content = generator.generate_prisma_flow(export_format)
            title = f"PRISMA Flow Diagram - {session.title}"
        elif report_type == 'full_report':
            content = generator.generate_full_report(export_format)
            title = f"Full PRISMA Report - {session.title}"
        elif report_type == 'included_studies':
            content = generator.generate_study_list('included', export_format)
            title = f"Included Studies - {session.title}"
        elif report_type == 'excluded_studies':
            content = generator.generate_study_list('excluded', export_format)
            title = f"Excluded Studies - {session.title}"
        else:
            raise ValueError(f"Unknown report type: {report_type}")
        
        self.update_state(state='IN_PROGRESS', meta={'progress': 80})
        
        # Create file name
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{report_type}_{session.title[:50]}_{timestamp}.{export_format}"
        file_name = file_name.replace(' ', '_').replace('/', '_')
        
        # Save report record
        report = ExportReport.objects.create(
            session=session,
            generated_by=user,
            report_type=report_type,
            export_format=export_format,
            title=title,
            description=f"Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            parameters=parameters,
            file_name=file_name,
            file_size_bytes=len(content),
            expires_at=timezone.now() + timezone.timedelta(days=30)  # 30-day retention
        )
        
        # Save file
        report.file_path.save(file_name, ContentFile(content), save=True)
        
        # Update statistics
        if report_type in ['prisma_flow', 'full_report', 'included_studies', 'excluded_studies']:
            stats = generator.stats_service.get_basic_statistics(session, user)
            report.total_results = stats['total_results']
            report.included_results = stats['included_results']
            report.excluded_results = stats['excluded_results']
            report.save()
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'report_id': str(report.id)})
        
        logger.info(f"Report generated successfully: {report.id}")
        return {'report_id': str(report.id), 'file_name': file_name}
        
    except Exception as exc:
        logger.error(f"Report generation failed: {str(exc)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc), 'progress': 0}
        )
        raise exc

@shared_task
def cleanup_expired_reports():
    """
    Periodic task to clean up expired report files.
    """
    expired_reports = ExportReport.objects.filter(
        expires_at__lt=timezone.now()
    )
    
    count = 0
    for report in expired_reports:
        try:
            # Delete file from storage
            if report.file_path:
                report.file_path.delete(save=False)
            
            # Delete database record
            report.delete()
            count += 1
            
        except Exception as e:
            logger.error(f"Failed to delete expired report {report.id}: {str(e)}")
    
    logger.info(f"Cleaned up {count} expired reports")
    return count
```

## 6. Testing Requirements

### 6.1 Unit Tests

#### Model Tests
```python
# apps/reporting/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.reporting.models import ExportReport
from apps.reporting.tests.factories import ExportReportFactory
from apps.review_manager.tests.factories import SearchSessionFactory

User = get_user_model()

class ExportReportModelTest(TestCase):
    """Test ExportReport model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSessionFactory(created_by=self.user)
    
    def test_report_creation(self):
        """Test creating an export report."""
        report = ExportReport.objects.create(
            session=self.session,
            generated_by=self.user,
            report_type='prisma_flow',
            export_format='pdf',
            title='Test Report',
            file_name='test_report.pdf',
            file_size_bytes=12345
        )
        
        self.assertEqual(str(report), 'Test Report (PRISMA Flow Diagram)')
        self.assertFalse(report.is_expired)
    
    def test_expiration_logic(self):
        """Test report expiration functionality."""
        past_time = timezone.now() - timezone.timedelta(days=1)
        
        report = ExportReportFactory(
            session=self.session,
            expires_at=past_time
        )
        
        self.assertTrue(report.is_expired)
    
    def test_file_size_human_readable(self):
        """Test human-readable file size formatting."""
        report = ExportReportFactory(file_size_bytes=1536)  # 1.5 KB
        self.assertEqual(report.file_size_human, '1.5 KB')
        
        report.file_size_bytes = 1048576  # 1 MB
        self.assertEqual(report.file_size_human, '1.0 MB')
```

#### Service Tests
```python
# apps/reporting/tests/test_services.py
from django.test import TestCase
from apps.reporting.services import StatisticsService, ReportGenerationService
from apps.reporting.tests.factories import *
from apps.review_results.tests.factories import ReviewTagAssignmentFactory
from apps.results_manager.tests.factories import ProcessedResultFactory

class StatisticsServiceTest(TestCase):
    """Test statistics generation service."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSessionFactory(created_by=self.user)
        self.service = StatisticsService()
        
        # Create test data
        self.results = [
            ProcessedResultFactory(session=self.session)
            for _ in range(10)
        ]
        
        # Tag some results
        include_tag = ReviewTagFactory(name='Include')
        exclude_tag = ReviewTagFactory(name='Exclude')
        
        for i, result in enumerate(self.results):
            if i < 5:
                ReviewTagAssignmentFactory(
                    processed_result=result,
                    session=self.session,
                    user=self.user,
                    tag=include_tag
                )
            else:
                ReviewTagAssignmentFactory(
                    processed_result=result,
                    session=self.session,
                    user=self.user,
                    tag=exclude_tag,
                    reason='Not relevant'
                )
    
    def test_basic_statistics(self):
        """Test basic statistics generation."""
        stats = self.service.get_basic_statistics(self.session, self.user)
        
        self.assertEqual(stats['total_results'], 10)
        self.assertEqual(stats['included_results'], 5)
        self.assertEqual(stats['excluded_results'], 5)
        self.assertEqual(stats['tagged_results'], 10)
    
    def test_prisma_flow_data(self):
        """Test PRISMA flow data generation."""
        flow_data = self.service.get_prisma_flow_data(self.session, self.user)
        
        self.assertEqual(flow_data['identification']['total'], 10)
        self.assertEqual(flow_data['included']['total'], 5)
        self.assertIn('excluded_reasons', flow_data['eligibility'])

class ReportGenerationServiceTest(TestCase):
    """Test report generation service."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSessionFactory(
            created_by=self.user,
            status='completed'
        )
        self.service = ReportGenerationService(self.session, self.user)
    
    def test_prisma_flow_generation(self):
        """Test PRISMA flow diagram generation."""
        # Mock the actual PDF generation for unit testing
        with patch.object(self.service, '_generate_prisma_pdf') as mock_pdf:
            mock_pdf.return_value = b'fake_pdf_content'
            
            result = self.service.generate_prisma_flow('pdf')
            
            self.assertEqual(result, b'fake_pdf_content')
            mock_pdf.assert_called_once()
    
    def test_unsupported_format_error(self):
        """Test error handling for unsupported formats."""
        with self.assertRaises(ValueError):
            self.service.generate_prisma_flow('unsupported_format')
```

### 6.2 Integration Tests

```python
# apps/reporting/tests/test_integration.py
class ReportingWorkflowIntegrationTest(TestCase):
    """Test complete reporting workflow integration."""
    
    def test_complete_report_generation_workflow(self):
        """Test end-to-end report generation."""
        # Setup complete session with data
        user = User.objects.create_user(
            email='researcher@example.com',
            password='testpass'
        )
        session = SearchSessionFactory(
            created_by=user,
            status='completed'
        )
        
        # Add results and tags
        results = [ProcessedResultFactory(session=session) for _ in range(20)]
        include_tag = ReviewTagFactory(name='Include')
        exclude_tag = ReviewTagFactory(name='Exclude', requires_reason=True)
        
        for i, result in enumerate(results):
            if i < 10:
                ReviewTagAssignmentFactory(
                    processed_result=result,
                    session=session,
                    user=user,
                    tag=include_tag
                )
            else:
                ReviewTagAssignmentFactory(
                    processed_result=result,
                    session=session,
                    user=user,
                    tag=exclude_tag,
                    reason='Not relevant to research question'
                )
        
        # Test report generation
        service = ReportGenerationService(session, user)
        
        # Generate different report types
        reports = {}
        
        # Note: In actual tests, mock the file generation methods
        # to avoid creating actual files during testing
        
        with patch.object(service, '_generate_prisma_pdf') as mock_prisma:
            mock_prisma.return_value = b'prisma_content'
            reports['prisma'] = service.generate_prisma_flow('pdf')
        
        with patch.object(service, '_generate_excel_study_list') as mock_excel:
            mock_excel.return_value = b'excel_content'
            reports['included'] = service.generate_study_list('included', 'xlsx')
        
        # Verify all reports were generated
        self.assertIn('prisma', reports)
        self.assertIn('included', reports)
        
        # Verify content
        self.assertEqual(reports['prisma'], b'prisma_content')
        self.assertEqual(reports['included'], b'excel_content')
```

## 7. Performance Optimization

### 7.1 Database Optimization
- Indexed queries on session and user relationships
- Prefetch related data for report generation
- Cached statistics calculations with Redis
- Optimized queryset annotations for large datasets

### 7.2 File Generation Optimization
- Background task processing for large reports
- Streaming file generation for memory efficiency
- Compressed file storage for large exports
- Progressive report generation with status updates

### 7.3 Caching Strategy
```python
# Cache expensive statistical calculations
STATISTICS_CACHE_TTL = 3600  # 1 hour

def get_cached_statistics(session_id, user_id):
    cache_key = f'session_stats:{session_id}:{user_id}'
    cached_stats = cache.get(cache_key)
    
    if cached_stats is None:
        service = StatisticsService()
        session = SearchSession.objects.get(pk=session_id)
        user = User.objects.get(pk=user_id)
        cached_stats = service.get_basic_statistics(session, user)
        cache.set(cache_key, cached_stats, STATISTICS_CACHE_TTL)
    
    return cached_stats
```

## 8. Security Considerations

### 8.1 Access Control
- All views require authentication and session ownership validation
- Report downloads protected by user permissions
- File paths obfuscated to prevent direct access
- Rate limiting on report generation endpoints

### 8.2 File Security
- Generated files stored outside web root
- Secure file serving through Django views
- Automatic file cleanup after expiration
- File type validation for exports

### 8.3 Data Privacy
- User data anonymization options in exports
- Audit logging for all report generation
- Secure deletion of expired files
- No sensitive data in file names or paths

## 9. Phase Implementation

### 9.1 Phase 1 (Current Scope)
- ✅ ExportReport model with full metadata tracking
- ✅ Basic statistics generation
- ✅ PRISMA flow diagram generation (PDF)
- ✅ Study lists export (Excel, CSV)
- ✅ Background task processing
- ✅ Report management interface
- ✅ File lifecycle management

### 9.2 Phase 2 (Future Enhancements)
- [ ] Advanced visualization dashboard
- [ ] Custom report templates
- [ ] Collaborative reporting features
- [ ] API integration for external tools
- [ ] Advanced statistical analysis
- [ ] Real-time report preview
- [ ] Bulk report generation
- [ ] Report scheduling and automation

## 10. Development Checklist

### 10.1 Implementation Checklist
- [ ] Complete view implementations for all report types
- [ ] Implement PDF generation with WeasyPrint
- [ ] Create Excel export functionality with openpyxl
- [ ] Set up Celery background tasks
- [ ] Create report download and management views
- [ ] Implement file cleanup and lifecycle management
- [ ] Add comprehensive error handling
- [ ] Create responsive templates
- [ ] Implement progress tracking for long operations

### 10.2 Testing Checklist
- [ ] Unit tests for all services and utilities (95%+ coverage)
- [ ] Integration tests for complete workflows
- [ ] Performance tests for large datasets
- [ ] Security tests for file access and permissions
- [ ] Background task testing
- [ ] File generation testing with mocked outputs
- [ ] User interface testing with Selenium

### 10.3 Documentation Checklist
- [ ] User guide for report generation
- [ ] API documentation for background tasks
- [ ] Developer guide for adding new report types
- [ ] Deployment configuration for file storage
- [ ] Performance tuning guidelines

## 11. Success Metrics

### 11.1 Performance Metrics
- Report generation completes < 2 minutes for 1000+ results
- File downloads start < 3 seconds after request
- Background task success rate > 99%
- Memory usage < 512MB per report generation

### 11.2 User Experience Metrics
- Report generation success rate > 95%
- User satisfaction with report quality > 4.5/5
- Average time to generate standard report < 30 seconds
- Report download completion rate > 98%

### 11.3 Technical Metrics
- File storage efficiency > 80% (compressed vs raw)
- Cache hit rate for statistics > 75%
- Database query optimization < 20 queries per report
- Background task queue processing < 5 minutes average

## 12. References

### 12.1 Internal Documentation
- [Master PRD](../PRD.md)
- [Review Manager PRD](../review-manager/review-manager-prd.md)
- [Review Results PRD](../review-results/review-results-prd.md)
- [Results Manager PRD](../results-manager/results-manager-prd.md)

### 12.2 External References
- [PRISMA 2020 Guidelines](http://www.prisma-statement.org/)
- [WeasyPrint Documentation](https://weasyprint.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Django File Handling](https://docs.djangoproject.com/en/4.2/topics/files/)

---

**Document Status:** Complete  
**Last Updated:** 2025-01-25  
**Next Review:** Phase 1 Implementation Completion