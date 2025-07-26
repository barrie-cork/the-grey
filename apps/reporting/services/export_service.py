"""
Export service for reporting slice.
Business capability: Data export and format conversion.
"""

from typing import Dict, Any
from django.utils import timezone

from apps.core.logging import ServiceLoggerMixin


class ExportService(ServiceLoggerMixin):
    """Service for exporting data in various formats."""
    
    def generate_export_formats(self, data: Dict[str, Any], format_type: str) -> Dict[str, Any]:
        """
        Convert report data to various export formats.
        
        Args:
            data: Report data dictionary
            format_type: Export format ('json', 'csv', 'xlsx', 'pdf')
            
        Returns:
            Dictionary with formatted data and metadata
        """
        export_result = {
            'format': format_type,
            'generated_at': timezone.now().isoformat(),
            'data': data,
            'file_info': {
                'filename': f"report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{format_type}",
                'content_type': self.get_content_type(format_type),
                'estimated_size': self.estimate_file_size(data, format_type)
            }
        }
        
        return export_result
    
    def get_content_type(self, format_type: str) -> str:
        """Get MIME content type for export format."""
        content_types = {
            'json': 'application/json',
            'csv': 'text/csv',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'bibtex': 'application/x-bibtex'
        }
        return content_types.get(format_type, 'application/octet-stream')
    
    def estimate_file_size(self, data: Dict[str, Any], format_type: str) -> int:
        """Estimate file size for export format."""
        import json
        
        # Basic estimation based on JSON size
        json_size = len(json.dumps(data, default=str))
        
        # Format-specific multipliers
        multipliers = {
            'json': 1.0,
            'csv': 0.7,
            'xlsx': 1.5,
            'pdf': 2.0,
            'docx': 1.8,
            'bibtex': 0.8
        }
        
        multiplier = multipliers.get(format_type, 1.0)
        return int(json_size * multiplier)
    
    def export_to_csv(self, data: Dict[str, Any], export_type: str = 'studies') -> str:
        """
        Export data to CSV format.
        
        Args:
            data: Data to export
            export_type: Type of export ('studies', 'queries', 'metrics')
            
        Returns:
            CSV string
        """
        import csv
        import io
        
        output = io.StringIO()
        
        if export_type == 'studies' and 'studies' in data:
            writer = csv.DictWriter(output, fieldnames=[
                'id', 'title', 'authors', 'publication_year', 'document_type',
                'url', 'has_full_text', 'relevance_score'
            ])
            writer.writeheader()
            
            for study in data['studies']:
                writer.writerow({
                    'id': study.get('id', ''),
                    'title': study.get('title', ''),
                    'authors': study.get('authors', ''),
                    'publication_year': study.get('publication_year', ''),
                    'document_type': study.get('document_type', ''),
                    'url': study.get('url', ''),
                    'has_full_text': study.get('has_full_text', False),
                    'relevance_score': study.get('relevance_score', 0)
                })
        
        elif export_type == 'queries' and 'queries' in data:
            writer = csv.DictWriter(output, fieldnames=[
                'id', 'query_string', 'population', 'interest', 'context',
                'search_engines', 'total_results', 'success_rate'
            ])
            writer.writeheader()
            
            for query in data['queries']:
                writer.writerow({
                    'id': query.get('id', ''),
                    'query_string': query.get('query_string', ''),
                    'population': query.get('pic_framework', {}).get('population', ''),
                    'interest': query.get('pic_framework', {}).get('interest', ''),
                    'context': query.get('pic_framework', {}).get('context', ''),
                    'search_engines': ', '.join(query.get('parameters', {}).get('search_engines', [])),
                    'total_results': query.get('execution_results', {}).get('total_results', 0),
                    'success_rate': query.get('execution_results', {}).get('success_rate', 0)
                })
        
        return output.getvalue()
    
    def export_to_bibtex(self, studies: list) -> str:
        """
        Export studies to BibTeX format.
        
        Args:
            studies: List of study dictionaries
            
        Returns:
            BibTeX string
        """
        bibtex_entries = []
        
        for study in studies:
            # Generate citation key
            title_words = study.get('title', 'Unknown').split()[:3]
            citation_key = ''.join(word.capitalize() for word in title_words if word.isalpha())
            year = study.get('publication_year', 'unknown')
            citation_key = f"{citation_key}{year}"
            
            # Determine entry type
            doc_type = study.get('document_type', 'misc')
            entry_type = self._map_to_bibtex_type(doc_type)
            
            # Build entry
            entry = f"@{entry_type}{{{citation_key},\n"
            entry += f"  title = {{{study.get('title', 'Unknown Title')}}},\n"
            
            if study.get('authors'):
                entry += f"  author = {{{study['authors']}}},\n"
            
            if study.get('publication_year'):
                entry += f"  year = {{{study['publication_year']}}},\n"
            
            if study.get('url'):
                entry += f"  url = {{{study['url']}}},\n"
            
            if study.get('source_organization'):
                entry += f"  institution = {{{study['source_organization']}}},\n"
            
            entry += "}\n"
            bibtex_entries.append(entry)
        
        return '\n'.join(bibtex_entries)
    
    def _map_to_bibtex_type(self, doc_type: str) -> str:
        """Map document type to BibTeX entry type."""
        type_mapping = {
            'journal_article': 'article',
            'report': 'techreport',
            'thesis': 'phdthesis',
            'working_paper': 'unpublished',
            'book': 'book',
            'conference': 'inproceedings',
            'pdf': 'misc'
        }
        return type_mapping.get(doc_type, 'misc')
    
    def generate_export_summary(self, session_id: str, export_types: list) -> Dict[str, Any]:
        """
        Generate summary of available export options.
        
        Args:
            session_id: UUID of the SearchSession
            export_types: List of requested export types
            
        Returns:
            Dictionary with export options summary
        """
        from apps.results_manager.models import ProcessedResult
        from apps.review_results.models import ReviewTagAssignment
        
        # Count available data
        total_results = ProcessedResult.objects.filter(session_id=session_id).count()
        included_studies = ReviewTagAssignment.objects.filter(
            result__session_id=session_id,
            tag__name='Include'
        ).count()
        
        export_summary = {
            'session_id': session_id,
            'data_available': {
                'total_results': total_results,
                'included_studies': included_studies,
                'has_prisma_data': total_results > 0,
                'has_search_strategy': True,  # Assume available if session exists
                'has_performance_metrics': total_results > 0
            },
            'export_options': [],
            'recommended_formats': []
        }
        
        # Available export options
        for export_type in export_types:
            if export_type == 'prisma_flow':
                export_summary['export_options'].append({
                    'type': 'prisma_flow',
                    'name': 'PRISMA Flow Diagram',
                    'formats': ['json', 'pdf', 'docx'],
                    'available': total_results > 0
                })
            
            elif export_type == 'study_characteristics':
                export_summary['export_options'].append({
                    'type': 'study_characteristics',
                    'name': 'Study Characteristics Table',
                    'formats': ['csv', 'xlsx', 'json'],
                    'available': included_studies > 0
                })
            
            elif export_type == 'search_strategy':
                export_summary['export_options'].append({
                    'type': 'search_strategy',
                    'name': 'Search Strategy Report',
                    'formats': ['json', 'pdf', 'docx'],
                    'available': True
                })
            
            elif export_type == 'bibliography':
                export_summary['export_options'].append({
                    'type': 'bibliography',
                    'name': 'Bibliography',
                    'formats': ['bibtex', 'csv', 'json'],
                    'available': included_studies > 0
                })
        
        # Recommendations based on data availability
        if included_studies > 0:
            export_summary['recommended_formats'].extend([
                'study_characteristics_csv',
                'bibliography_bibtex',
                'prisma_flow_pdf'
            ])
        
        if total_results > 10:
            export_summary['recommended_formats'].append('performance_metrics_json')
        
        return export_summary