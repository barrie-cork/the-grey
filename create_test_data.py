#!/usr/bin/env python
"""
Script to create test data for Results Manager user testing.
Run with: python manage.py shell --settings=test_settings_dev < create_test_data.py
"""

import uuid
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.review_manager.models import SearchSession
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import SearchExecution, RawSearchResult
from apps.results_manager.models import ProcessedResult, ProcessingSession

User = get_user_model()

def create_test_data():
    print("Creating Results Manager test data...")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"Created test user: {user.username}")
    else:
        print(f"Using existing test user: {user.username}")
    
    # Create test search session
    session, created = SearchSession.objects.get_or_create(
        title="Diabetes Management Guidelines Test",
        defaults={
            'description': 'Test session for Results Manager user testing',
            'owner': user,
            'status': 'processing_results',
            'created_at': timezone.now() - timedelta(hours=2),
            'updated_at': timezone.now() - timedelta(minutes=30)
        }
    )
    if created:
        print(f"Created test session: {session.title}")
    else:
        print(f"Using existing test session: {session.title}")
    
    # Create test search query
    query, created = SearchQuery.objects.get_or_create(
        session=session,
        defaults={
            'population': 'adults with diabetes',
            'interest': 'management guidelines',
            'context': 'clinical practice',
            'query_string': 'diabetes management guidelines filetype:pdf',
            'search_engines': ['google'],
            'include_keywords': ['diabetes', 'management', 'guidelines'],
            'exclude_keywords': [],
            'document_types': ['pdf'],
            'languages': ['en'],
            'date_from': None,
            'date_to': None,
            'max_results': 100,
            'order': 1,
            'is_active': True,
            'is_primary': True,
            'created_at': timezone.now() - timedelta(hours=1)
        }
    )
    if created:
        print(f"Created test query: {query.query_string}")
    
    # Create test search execution
    execution, created = SearchExecution.objects.get_or_create(
        query=query,
        defaults={
            'status': 'completed',
            'results_count': 85,
            'started_at': timezone.now() - timedelta(hours=1),
            'completed_at': timezone.now() - timedelta(minutes=45),
            'api_calls_made': 1,
            'api_credits_used': 100
        }
    )
    if created:
        print(f"Created test execution: {execution.status}")
    
    # Create sample raw search results
    sample_results = [
        {
            'title': 'Clinical Guidelines for Type 2 Diabetes Management',
            'url': 'https://www.nice.org.uk/guidance/ng28/resources/type-2-diabetes-in-adults-management-pdf-1837338615493',
            'snippet': 'Evidence-based recommendations for managing type 2 diabetes in adults...',
            'file_type': 'pdf',
            'domain': 'nice.org.uk'
        },
        {
            'title': 'Diabetes Management Best Practices 2023',
            'url': 'https://diabetes.org/healthcare-providers/clinical-practice-recommendations',
            'snippet': 'Comprehensive guide to diabetes management and treatment approaches...',
            'file_type': 'html',
            'domain': 'diabetes.org'
        },
        {
            'title': 'WHO Guidelines on Diabetes Treatment',
            'url': 'https://www.who.int/publications/i/item/9789241549950',
            'snippet': 'World Health Organization guidelines for diabetes prevention and control...',
            'file_type': 'pdf',
            'domain': 'who.int'
        },
        {
            'title': 'Advanced Insulin Therapy Guidelines',
            'url': 'https://care.diabetesjournals.org/content/44/Supplement_1/S111',
            'snippet': 'Latest recommendations for insulin therapy in diabetes management...',
            'file_type': 'html',
            'domain': 'diabetesjournals.org'
        },
        {
            'title': 'Diabetes Care Standards of Medical Care',
            'url': 'https://care.diabetesjournals.org/content/diacare/suppl/2023/12/08/47.Supplement_1.DC1/DC_47_S1_final.pdf',
            'snippet': 'Professional practice committee recommendations for diabetes care...',
            'file_type': 'pdf',
            'domain': 'diabetesjournals.org'
        }
    ]
    
    raw_results = []
    for i, result_data in enumerate(sample_results):
        raw_result, created = RawSearchResult.objects.get_or_create(
            execution=execution,
            position=i + 1,
            defaults={
                'title': result_data['title'],
                'url': result_data['url'],
                'snippet': result_data['snippet'],
                'metadata': {
                    'file_type': result_data['file_type'],
                    'domain': result_data['domain'],
                    'estimated_size': '2.5 MB' if result_data['file_type'] == 'pdf' else '45 KB'
                },
                'source_engine': 'google',
                'retrieved_at': timezone.now() - timedelta(minutes=45)
            }
        )
        raw_results.append(raw_result)
        if created:
            print(f"Created raw result: {result_data['title'][:50]}...")
    
    # Create processing session
    processing_session, created = ProcessingSession.objects.get_or_create(
        search_session=session,
        defaults={
            'status': 'completed',
            'total_raw_results': len(raw_results),
            'processed_count': len(raw_results),
            'duplicate_count': 1,
            'error_count': 0,
            'current_stage': 'finalization',
            'stage_progress': 100,
            'started_at': timezone.now() - timedelta(minutes=30),
            'completed_at': timezone.now() - timedelta(minutes=15),
            'processing_config': {
                'batch_size': 50,
                'deduplication_threshold': 0.85
            }
        }
    )
    if created:
        print(f"Created processing session: {processing_session.status}")
    
    # Create processed results
    for i, raw_result in enumerate(raw_results):
        # Create a duplicate for testing
        is_duplicate = i == 4  # Make the last result a duplicate of the second
        duplicate_of = raw_results[1] if is_duplicate else None
        
        processed_result, created = ProcessedResult.objects.get_or_create(
            session=session,
            raw_result=raw_result,
            defaults={
                'normalized_url': raw_result.url.lower().replace('www.', ''),
                'title': raw_result.title,
                'snippet': raw_result.snippet,
                'domain': raw_result.metadata.get('domain', ''),
                'file_type': raw_result.metadata.get('file_type', 'unknown'),
                'estimated_size': raw_result.metadata.get('estimated_size', 'Unknown'),
                'quality_score': 0.95 if 'nice.org.uk' in raw_result.url else 0.80 + (i * 0.02),
                'is_duplicate': is_duplicate,
                'duplicate_of': ProcessedResult.objects.filter(
                    raw_result=duplicate_of).first() if duplicate_of else None,
                'processed_at': timezone.now() - timedelta(minutes=20),
                'enhanced_metadata': {
                    'language': 'en',
                    'publication_year': 2023 - (i % 3),
                    'authority_level': 'high' if any(domain in raw_result.url 
                                                   for domain in ['nice.org.uk', 'who.int']) else 'medium'
                }
            }
        )
        if created:
            print(f"Created processed result: {processed_result.title[:50]}...")
    
    print("✅ Test data creation completed!")
    print(f"📊 Created:")
    print(f"   - 1 Search Session: {session.title}")
    print(f"   - 1 Search Query: {query.query_text}")
    print(f"   - 1 Search Execution with {len(raw_results)} results")
    print(f"   - 1 Processing Session (completed)")
    print(f"   - {len(raw_results)} Processed Results (including 1 duplicate)")
    print(f"🔑 Test user credentials:")
    print(f"   - Username: testuser")
    print(f"   - Password: testpass123")
    print(f"🌐 Access URLs:")
    print(f"   - Results Overview: http://localhost:8000/results-manager/results/{session.id}/")
    print(f"   - Processing Status: http://localhost:8000/results-manager/processing/{session.id}/")

if __name__ == '__main__':
    create_test_data()