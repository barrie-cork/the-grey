#!/usr/bin/env python
"""
Minimal test data creation script using only essential fields.
"""

import uuid
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult, ProcessingSession

User = get_user_model()

def create_minimal_test_data():
    print("Creating minimal Results Manager test data...")
    
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
    
    # Create test search session
    session, created = SearchSession.objects.get_or_create(
        title="Diabetes Management Guidelines Test",
        defaults={
            'description': 'Test session for Results Manager user testing',
            'owner': user,
            'status': 'ready_for_review'
        }
    )
    
    # Create processing session
    processing_session, created = ProcessingSession.objects.get_or_create(
        search_session=session,
        defaults={
            'status': 'completed',
            'total_raw_results': 10,
            'processed_count': 10,
            'duplicate_count': 2,
            'error_count': 0,
            'current_stage': 'finalization',
            'stage_progress': 100
        }
    )
    
    # Clear existing results
    ProcessedResult.objects.filter(session=session).delete()
    
    # Sample test results with minimal required fields
    sample_results = [
        {
            'title': 'Clinical Guidelines for Type 2 Diabetes Management',
            'url': 'https://www.nice.org.uk/guidance/ng28/resources/type-2-diabetes-in-adults-management-pdf',
            'snippet': 'Evidence-based recommendations for managing type 2 diabetes in adults...',
            'is_pdf': True
        },
        {
            'title': 'Diabetes Management Best Practices 2023',
            'url': 'https://diabetes.org/healthcare-providers/clinical-practice-recommendations',
            'snippet': 'Comprehensive guide to diabetes management and treatment approaches...',
            'is_pdf': False
        },
        {
            'title': 'WHO Guidelines on Diabetes Treatment',
            'url': 'https://www.who.int/publications/i/item/9789241549950',
            'snippet': 'World Health Organization guidelines for diabetes prevention and control...',
            'is_pdf': True
        },
        {
            'title': 'Advanced Insulin Therapy Guidelines',
            'url': 'https://care.diabetesjournals.org/content/44/Supplement_1/S111',
            'snippet': 'Latest recommendations for insulin therapy in diabetes management...',
            'is_pdf': False
        },
        {
            'title': 'Diabetes Care Standards of Medical Care',
            'url': 'https://care.diabetesjournals.org/content/diacare/suppl/2023/DC_47_S1_final.pdf',
            'snippet': 'Professional practice committee recommendations for diabetes care...',
            'is_pdf': True
        },
        {
            'title': 'Pediatric Diabetes Management Guidelines',
            'url': 'https://www.endocrine.org/clinical-practice-guidelines/pediatric-diabetes',
            'snippet': 'Specialized guidelines for managing diabetes in children and adolescents...',
            'is_pdf': False
        },
        {
            'title': 'Gestational Diabetes Clinical Recommendations',
            'url': 'https://www.acog.org/clinical/clinical-guidance/practice-bulletin/gestational-diabetes',
            'snippet': 'Clinical practice guidelines for gestational diabetes mellitus...',
            'is_pdf': True
        },
        {
            'title': 'International Diabetes Federation Guidelines',
            'url': 'https://www.idf.org/our-activities/care-prevention/gdm/guidelines.html',
            'snippet': 'Global recommendations for diabetes care and prevention strategies...',
            'is_pdf': True
        }
    ]
    
    # Create processed results
    for i, result_data in enumerate(sample_results):
        ProcessedResult.objects.create(
            session=session,
            title=result_data['title'],
            url=result_data['url'],
            snippet=result_data['snippet'],
            is_pdf=result_data['is_pdf'],
            document_type='pdf' if result_data['is_pdf'] else 'webpage',
            publication_year=2023 - (i % 3),
            language='en'
        )
    
    print("✅ Test data created successfully!")
    print(f"📊 Created {len(sample_results)} processed results")
    print(f"🔑 Login: testuser / testpass123")
    print(f"🌐 Results URL: http://localhost:8000/results-manager/results/{session.id}/")

if __name__ == '__main__':
    create_minimal_test_data()