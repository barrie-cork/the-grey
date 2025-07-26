"""
Study analysis service for reporting slice.
Business capability: Study characteristics analysis and reporting.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional

from apps.core.logging import ServiceLoggerMixin
from apps.reporting.constants import StudyAnalysisConstants, PerformanceConstants
from apps.results_manager.models import ProcessedResult
from apps.review_results.models import SimpleReviewDecision


class StudyAnalysisService(ServiceLoggerMixin):
    """Service for analyzing study characteristics and generating study tables."""
    
    def generate_study_characteristics_table(self, session_id: str) -> Dict[str, Any]:
        """
        Generate a table of study characteristics for included studies.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with study characteristics data
        """
        # Get included studies
        included_result_ids = SimpleReviewDecision.objects.filter(
            result__session_id=session_id,
            tag__name=PerformanceConstants.INCLUDE_TAG
        ).values_list('result_id', flat=True)
        
        included_studies = ProcessedResult.objects.filter(id__in=included_result_ids)
        
        characteristics = {
            'total_studies': included_studies.count(),
            'studies': [],
            'summary_statistics': {
                'publication_years': {},
                'document_types': {},
                'source_organizations': {},
                'languages': {},
                'full_text_availability': 0
            }
        }
        
        for study in included_studies:
            study_data = {
                'id': str(study.id),
                'title': study.title,
                'authors': study.authors,
                'publication_year': study.publication_year,
                'document_type': study.document_type,
                'source_organization': study.source_organization,
                'language': study.language,
                'url': study.url,
                'has_full_text': study.has_full_text,
                'quality_indicators': study.quality_indicators,
                'relevance_score': study.relevance_score
            }
            
            # Add metadata if available
            if hasattr(study, 'metadata'):
                metadata = study.metadata
                study_data.update({
                    'doi': getattr(metadata, 'doi', ''),
                    'keywords': getattr(metadata, 'keywords', []),
                    'abstract': getattr(metadata, 'abstract', ''),
                    'methodology': getattr(metadata, 'methodology', ''),
                    'country': getattr(metadata, 'country', ''),
                    'subject_areas': getattr(metadata, 'subject_areas', [])
                })
            
            characteristics['studies'].append(study_data)
            
            # Update summary statistics
            year = study.publication_year
            if year:
                characteristics['summary_statistics']['publication_years'][year] = \
                    characteristics['summary_statistics']['publication_years'].get(year, 0) + 1
            
            doc_type = study.document_type or 'unknown'
            characteristics['summary_statistics']['document_types'][doc_type] = \
                characteristics['summary_statistics']['document_types'].get(doc_type, 0) + 1
            
            if study.source_organization:
                org = study.source_organization
                characteristics['summary_statistics']['source_organizations'][org] = \
                    characteristics['summary_statistics']['source_organizations'].get(org, 0) + 1
            
            lang = study.language or 'unknown'
            characteristics['summary_statistics']['languages'][lang] = \
                characteristics['summary_statistics']['languages'].get(lang, 0) + 1
            
            if study.has_full_text:
                characteristics['summary_statistics']['full_text_availability'] += 1
        
        return characteristics
    
    def analyze_study_quality_distribution(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze quality distribution of included studies.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with quality analysis
        """
        # Get included studies
        included_result_ids = SimpleReviewDecision.objects.filter(
            result__session_id=session_id,
            tag__name=PerformanceConstants.INCLUDE_TAG
        ).values_list('result_id', flat=True)
        
        included_studies = ProcessedResult.objects.filter(id__in=included_result_ids)
        
        if not included_studies.exists():
            return {'total_studies': 0}
        
        total = included_studies.count()
        
        quality_analysis = {
            'total_studies': total,
            'quality_indicators': {
                'peer_reviewed': 0,
                'has_doi': 0,
                'full_text_available': 0,
                'recent_publication': 0,
                'academic_source': 0
            },
            'relevance_distribution': {
                'high': 0,  # > high_quality threshold
                'medium': 0,  # medium_quality to high_quality threshold
                'low': 0  # < medium_quality threshold
            },
            'publication_recency': {
                'last_5_years': 0,
                'last_10_years': 0,
                'older': 0
            }
        }
        
        current_year = datetime.now().year
        
        for study in included_studies:
            # Quality indicators
            if study.quality_indicators.get('peer_reviewed'):
                quality_analysis['quality_indicators']['peer_reviewed'] += 1
            
            if study.quality_indicators.get('has_doi'):
                quality_analysis['quality_indicators']['has_doi'] += 1
            
            if study.has_full_text:
                quality_analysis['quality_indicators']['full_text_available'] += 1
            
            if study.publication_year and study.publication_year >= current_year - StudyAnalysisConstants.RECENCY_PERIODS['recent']:
                quality_analysis['quality_indicators']['recent_publication'] += 1
            
            if study.quality_indicators.get('is_academic'):
                quality_analysis['quality_indicators']['academic_source'] += 1
            
            # Relevance distribution
            if study.relevance_score:
                if study.relevance_score > StudyAnalysisConstants.THRESHOLDS['high_quality']:
                    quality_analysis['relevance_distribution']['high'] += 1
                elif study.relevance_score >= StudyAnalysisConstants.THRESHOLDS['medium_quality']:
                    quality_analysis['relevance_distribution']['medium'] += 1
                else:
                    quality_analysis['relevance_distribution']['low'] += 1
            
            # Publication recency
            if study.publication_year:
                if study.publication_year >= current_year - StudyAnalysisConstants.RECENCY_PERIODS['recent']:
                    quality_analysis['publication_recency']['last_5_years'] += 1
                elif study.publication_year >= current_year - StudyAnalysisConstants.RECENCY_PERIODS['fairly_recent']:
                    quality_analysis['publication_recency']['last_10_years'] += 1
                else:
                    quality_analysis['publication_recency']['older'] += 1
        
        return quality_analysis
    
    def generate_study_geographical_distribution(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze geographical distribution of studies.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with geographical analysis
        """
        # Get included studies
        included_result_ids = SimpleReviewDecision.objects.filter(
            result__session_id=session_id,
            tag__name=PerformanceConstants.INCLUDE_TAG
        ).values_list('result_id', flat=True)
        
        included_studies = ProcessedResult.objects.filter(id__in=included_result_ids)
        
        geo_distribution = {
            'total_studies': included_studies.count(),
            'countries': {},
            'regions': {},
            'unknown_geography': 0
        }
        
        for study in included_studies:
            country = None
            
            # Try to extract country from metadata first
            if hasattr(study, 'metadata') and getattr(study.metadata, 'country', None):
                country = study.metadata.country
            
            # Fallback to URL analysis
            if not country and study.url:
                url_lower = study.url.lower()
                for domain, mapped_country in StudyAnalysisConstants.DOMAIN_TO_COUNTRY.items():
                    if domain in url_lower:
                        country = mapped_country
                        break
            
            if country:
                geo_distribution['countries'][country] = \
                    geo_distribution['countries'].get(country, 0) + 1
            else:
                geo_distribution['unknown_geography'] += 1
        
        # Group into regions
        country_to_region = {
            'United States': 'North America',
            'Canada': 'North America',
            'United Kingdom': 'Europe',
            'Germany': 'Europe',
            'France': 'Europe',
            'Netherlands': 'Europe',
            'European Union': 'Europe',
            'Australia': 'Oceania',
            'International': 'International'
        }
        
        for country, count in geo_distribution['countries'].items():
            region = country_to_region.get(country, 'Other')
            geo_distribution['regions'][region] = \
                geo_distribution['regions'].get(region, 0) + count
        
        return geo_distribution