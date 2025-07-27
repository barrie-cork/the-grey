#!/usr/bin/env python
"""
Simplified script to create minimal test data for Results Manager user testing.
"""

import uuid
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult, ProcessingSession

User = get_user_model()

def create_simple_test_data():
    print("Creating simple Results Manager test data...")
    
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
        print(f"✅ Created test user: {user.username}")
    else:
        print(f"✅ Using existing test user: {user.username}")
    
    # Create test search session
    session, created = SearchSession.objects.get_or_create(
        title="Diabetes Management Guidelines Test",
        defaults={
            'description': 'Test session for Results Manager user testing',
            'owner': user,
            'status': 'ready_for_review',
            'created_at': timezone.now() - timedelta(hours=2),
            'updated_at': timezone.now() - timedelta(minutes=30)
        }
    )
    if created:
        print(f"✅ Created test session: {session.title}")
    else:
        session.status = 'ready_for_review'
        session.save()
        print(f"✅ Using existing test session: {session.title}")
    
    # Create processing session
    processing_session, created = ProcessingSession.objects.get_or_create(
        search_session=session,
        defaults={
            'status': 'completed',
            'total_raw_results': 15,
            'processed_count': 15,
            'duplicate_count': 2,
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
        print(f"✅ Created processing session: {processing_session.status}")
    
    # Sample test results data
    sample_results = [
        {
            'title': 'Clinical Guidelines for Type 2 Diabetes Management',
            'url': 'https://www.nice.org.uk/guidance/ng28/resources/type-2-diabetes-in-adults-management-pdf-1837338615493',
            'snippet': 'Evidence-based recommendations for managing type 2 diabetes in adults, including lifestyle interventions, medication options, and monitoring strategies...',
            'domain': 'nice.org.uk',
            'file_type': 'pdf',
            'quality_score': 0.95,
            'is_duplicate': False
        },
        {
            'title': 'Diabetes Management Best Practices 2023',
            'url': 'https://diabetes.org/healthcare-providers/clinical-practice-recommendations',
            'snippet': 'Comprehensive guide to diabetes management and treatment approaches based on latest clinical evidence and research findings...',
            'domain': 'diabetes.org',
            'file_type': 'html',
            'quality_score': 0.88,
            'is_duplicate': False
        },
        {
            'title': 'WHO Guidelines on Diabetes Treatment',
            'url': 'https://www.who.int/publications/i/item/9789241549950',
            'snippet': 'World Health Organization guidelines for diabetes prevention and control, including global strategies and implementation frameworks...',
            'domain': 'who.int',
            'file_type': 'pdf',
            'quality_score': 0.92,
            'is_duplicate': False
        },
        {
            'title': 'Advanced Insulin Therapy Guidelines',
            'url': 'https://care.diabetesjournals.org/content/44/Supplement_1/S111',
            'snippet': 'Latest recommendations for insulin therapy in diabetes management, including dosing protocols and patient monitoring...',
            'domain': 'diabetesjournals.org',
            'file_type': 'html',
            'quality_score': 0.85,
            'is_duplicate': False
        },
        {
            'title': 'Diabetes Care Standards of Medical Care',
            'url': 'https://care.diabetesjournals.org/content/diacare/suppl/2023/12/08/47.Supplement_1.DC1/DC_47_S1_final.pdf',
            'snippet': 'Professional practice committee recommendations for diabetes care, including diagnostic criteria and treatment algorithms...',
            'domain': 'diabetesjournals.org',
            'file_type': 'pdf',
            'quality_score': 0.90,
            'is_duplicate': True  # Duplicate of result #2
        },
        {
            'title': 'Pediatric Diabetes Management Guidelines',
            'url': 'https://www.endocrine.org/clinical-practice-guidelines/pediatric-diabetes',
            'snippet': 'Specialized guidelines for managing diabetes in children and adolescents, including family-centered care approaches...',
            'domain': 'endocrine.org',
            'file_type': 'html',
            'quality_score': 0.82,
            'is_duplicate': False
        },
        {
            'title': 'Gestational Diabetes Clinical Recommendations',
            'url': 'https://www.acog.org/clinical/clinical-guidance/practice-bulletin/articles/2018/07/gestational-diabetes-mellitus',
            'snippet': 'Clinical practice guidelines for gestational diabetes mellitus screening, diagnosis, and management during pregnancy...',
            'domain': 'acog.org',
            'file_type': 'pdf',
            'quality_score': 0.87,
            'is_duplicate': False
        },
        {
            'title': 'Diabetes Technology and Continuous Monitoring',
            'url': 'https://diabetes.org/tools-resources/continuous-glucose-monitoring',
            'snippet': 'Guidelines for diabetes technology including continuous glucose monitoring systems and insulin pump therapy...',
            'domain': 'diabetes.org',
            'file_type': 'html',
            'quality_score': 0.79,
            'is_duplicate': True  # Duplicate of result #2
        },
        {
            'title': 'International Diabetes Federation Guidelines',
            'url': 'https://www.idf.org/our-activities/care-prevention/gdm/guidelines.html',
            'snippet': 'Global recommendations for diabetes care and prevention strategies from the International Diabetes Federation...',
            'domain': 'idf.org',
            'file_type': 'pdf',
            'quality_score': 0.91,
            'is_duplicate': False
        },
        {
            'title': 'Diabetes Complications Prevention Guidelines',
            'url': 'https://www.niddk.nih.gov/health-information/diabetes/overview/preventing-problems',
            'snippet': 'Comprehensive guidelines for preventing diabetes complications including kidney disease, eye problems, and neuropathy...',
            'domain': 'niddk.nih.gov',
            'file_type': 'html',
            'quality_score': 0.84,
            'is_duplicate': False
        }
    ]
    
    # Clear existing processed results for this session
    ProcessedResult.objects.filter(session=session).delete()
    
    # Create processed results
    for i, result_data in enumerate(sample_results):
        processed_result = ProcessedResult.objects.create(
            session=session,
            title=result_data['title'],
            normalized_url=result_data['url'].lower().replace('www.', ''),
            snippet=result_data['snippet'],
            domain=result_data['domain'],
            file_type=result_data['file_type'],
            estimated_size='2.5 MB' if result_data['file_type'] == 'pdf' else '45 KB',
            quality_score=result_data['quality_score'],
            is_duplicate=result_data['is_duplicate'],
            processed_at=timezone.now() - timedelta(minutes=20 - i),
            enhanced_metadata={
                'language': 'en',
                'publication_year': 2023 - (i % 4),
                'authority_level': 'high' if result_data['domain'] in ['nice.org.uk', 'who.int'] else 'medium',
                'estimated_reading_time': f"{15 + (i * 2)} minutes"
            }
        )
        print(f"✅ Created processed result: {result_data['title'][:50]}...")
    
    print("🎉 Simple test data creation completed!")
    print(f"📊 Summary:")
    print(f"   • Session: {session.title}")
    print(f"   • Status: {session.status}")
    print(f"   • Total Results: {len(sample_results)}")
    print(f"   • Duplicates: {sum(1 for r in sample_results if r['is_duplicate'])}")
    print(f"   • Processing: {processing_session.status}")
    print("")
    print(f"🔑 Test Login Credentials:")
    print(f"   • Username: testuser")
    print(f"   • Password: testpass123")
    print("")
    print(f"🌐 Test URLs (start dev server first):")
    print(f"   • Results Overview: http://localhost:8000/results-manager/results/{session.id}/")
    print(f"   • Processing Status: http://localhost:8000/results-manager/processing/{session.id}/")
    print(f"   • Login: http://localhost:8000/accounts/login/")

if __name__ == '__main__':
    create_simple_test_data()