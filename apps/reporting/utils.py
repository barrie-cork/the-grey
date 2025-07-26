"""
Utility functions for the reporting app.

This module contains helper functions for generating reports.
Business logic has been moved to dedicated services.
"""

from .services.export_service import ExportService
from .services.performance_analytics_service import PerformanceAnalyticsService

# Service imports for backward compatibility
from .services.prisma_reporting_service import PrismaReportingService
from .services.search_strategy_reporting_service import SearchStrategyReportingService
from .services.study_analysis_service import StudyAnalysisService

# Initialize services for backward compatibility
prisma_reporting_service = PrismaReportingService()
search_strategy_reporting_service = SearchStrategyReportingService()
study_analysis_service = StudyAnalysisService()
performance_analytics_service = PerformanceAnalyticsService()
export_service = ExportService()

# Legacy function proxies for backward compatibility
generate_prisma_flow_data = prisma_reporting_service.generate_prisma_flow_data
calculate_review_period_from_data = (
    prisma_reporting_service.calculate_review_period_from_data
)
get_exclusion_reasons = prisma_reporting_service.get_exclusion_reasons
calculate_review_period = prisma_reporting_service.calculate_review_period
export_prisma_checklist = prisma_reporting_service.export_prisma_checklist
generate_search_strategy_report = (
    search_strategy_reporting_service.generate_search_strategy_report
)
generate_study_characteristics_table = (
    study_analysis_service.generate_study_characteristics_table
)
calculate_search_performance_metrics = (
    performance_analytics_service.calculate_search_performance_metrics
)
generate_export_formats = export_service.generate_export_formats
get_content_type = export_service.get_content_type
estimate_file_size = export_service.estimate_file_size
