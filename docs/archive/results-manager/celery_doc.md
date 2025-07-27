"""
Celery Tasks for Results Manager
Handles background processing of search results from SERP execution.

This module implements Task 3.0 Background Task Implementation from:
docs/features/results-manager/tasks-results-manager-implementation.md

REQ-TR-RM-1: Asynchronous Processing Pipeline using Celery tasks
REQ-FR-RM-1: Automated Results Processing as background server-side operation
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from celery import shared_task, group, chain
from celery.exceptions import Retry

from .models import ProcessedResult, DuplicateRelationship, ProcessingSession
from .services.result_processor import ResultProcessor
from .services.deduplication_engine import DeduplicationEngine
from .services.metadata_extractor import MetadataExtractor
from .utils.url_normalizer import URLNormalizer
from apps.review_manager.models import SearchSession, SessionActivity
from apps.serp_execution.models import RawSearchResult, SearchExecution

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_session_results_task(self, session_id: str, user_id: str) -> Dict[str, Any]:
    """
    Main orchestrating task for processing search results from SERP execution.
    
    This task replaces the placeholder in serp_execution.tasks and implements:
    REQ-FR-RM-1: Automated Results Processing
    REQ-FR-RM-6: Processing Status Notifications
    
    Workflow:
    1. Create ProcessingSession record
    2. Validate session is ready for processing
    3. Launch sub-tasks for normalization and deduplication
    4. Monitor progress and update session status
    
    Args:
        session_id (str): UUID of the SearchSession to process
        user_id (str): UUID of the user who initiated processing
        
    Returns:
        dict: Processing result with status and statistics
    """
    processing_session = None
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get session and user
        try:
            session = SearchSession.objects.get(id=session_id)
            user = User.objects.get(id=user_id)
        except (SearchSession.DoesNotExist, User.DoesNotExist) as e:
            logger.error(f"Session or user not found: {str(e)}")
            return {'status': 'error', 'message': 'Session or user not found'}
        
        # Validate session can be processed
        if session.status != SearchSession.Status.PROCESSING:
            logger.warning(f"Session {session_id} is not in processing status: {session.status}")
            return {'status': 'skipped', 'message': 'Session not in processing status'}
        
        # Create or get processing session
        processing_session, created = ProcessingSession.objects.get_or_create(
            search_session=session,
            defaults={
                'status': 'pending',
                'raw_results_count': 0,
            }
        )
        
        if not created and processing_session.status in ['running', 'completed']:
            logger.info(f"Processing session already {processing_session.status}")
            return {
                'status': processing_session.status,
                'message': f'Processing already {processing_session.status}'
            }
        
        # Get raw results from successful executions
        successful_executions = SearchExecution.objects.filter(
            query__session=session,
            status='completed'
        )
        
        if not successful_executions.exists():
            processing_session.fail_processing('No successful search executions found')
            
            SessionActivity.log_activity(
                session=session,
                action='ERROR',
                description='No successful search results to process',
                user=user,
                details={'error_type': 'no_results'}
            )
            
            return {'status': 'failed', 'message': 'No successful results to process'}
        
        # Count raw results
        raw_results = RawSearchResult.objects.filter(execution__in=successful_executions)
        raw_count = raw_results.count()
        
        # Update processing session with count and start
        processing_session.raw_results_count = raw_count
        processing_session.start_processing()
        
        logger.info(f"Starting processing of {raw_count} raw results for session {session.title}")
        
        # Log processing start
        SessionActivity.log_activity(
            session=session,
            action='RESULTS_PROCESSED',
            description=f'Started processing {raw_count} raw results',
            user=user,
            details={
                'processing_session_id': str(processing_session.id),
                'raw_results_count': raw_count,
                'successful_executions': successful_executions.count()
            }
        )
        
        # Chain sub-tasks: normalization -> deduplication -> completion
        task_chain = chain(
            normalize_raw_results_task.s(session_id, user_id),
            deduplicate_results_task.s(session_id, user_id),
            monitor_processing_completion_task.s(session_id, user_id)
        )
        
        # Execute the chain
        result = task_chain.apply_async()
        
        return {
            'status': 'initiated',
            'session_id': session_id,
            'processing_session_id': str(processing_session.id),
            'raw_results_count': raw_count,
            'message': f'Processing initiated for {raw_count} raw results'
        }
        
    except Exception as e:
        logger.error(f"Error initiating results processing: {str(e)}")
        
        # Attempt to mark processing as failed
        try:
            if processing_session:
                processing_session.fail_processing(str(e))
            
            session = SearchSession.objects.get(id=session_id)
            session.status = SearchSession.Status.FAILED
            session.save()
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            
            SessionActivity.log_activity(
                session=session,
                action='ERROR',
                description=f'Results processing initiation failed: {str(e)}',
                user=user,
                details={'error_type': 'processing_initiation_failure', 'error_message': str(e)}
            )
        except:
            pass  # Don't fail if we can't log the error
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        return {
            'status': 'error',
            'message': f'Failed to initiate processing after {self.max_retries} retries: {str(e)}'
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def normalize_raw_results_task(self, previous_result: Dict[str, Any], session_id: str, user_id: str) -> Dict[str, Any]:
    """
    Normalize raw search results from SERP execution.
    
    This task implements:
    REQ-FR-RM-2: URL Normalization
    REQ-FR-RM-3: Metadata Extraction
    REQ-TR-RM-2: Efficient Data Storage
    
    Process:
    1. Fetch all RawSearchResult records for the session
    2. Apply URL normalization
    3. Extract metadata (file type, content type, quality scores)
    4. Create ProcessedResult records
    5. Update processing progress
    
    Args:
        previous_result: Result from previous task in chain
        session_id (str): UUID of the SearchSession
        user_id (str): UUID of the user
        
    Returns:
        dict: Normalization result with statistics
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get session, user, and processing session
        session = SearchSession.objects.get(id=session_id)
        user = User.objects.get(id=user_id)
        processing_session = ProcessingSession.objects.get(search_session=session)
        
        # Update progress to normalization stage
        processing_session.update_progress(25)
        
        logger.info(f"Starting normalization for session {session.title}")
        
        # Get successful executions and their raw results
        successful_executions = SearchExecution.objects.filter(
            query__session=session,
            status='completed'
        )
        
        raw_results = RawSearchResult.objects.filter(
            execution__in=successful_executions
        ).order_by('execution', 'position')
        
        # Initialize services
        url_normalizer = URLNormalizer()
        metadata_extractor = MetadataExtractor()
        result_processor = ResultProcessor()
        
        # Process results in batches
        batch_size = 50
        total_results = raw_results.count()
        processed_count = 0
        error_count = 0
        
        for i in range(0, total_results, batch_size):
            batch = raw_results[i:i + batch_size]
            
            with transaction.atomic():
                for raw_result in batch:
                    try:
                        # Process single result
                        processed_result = result_processor.process_single_result(
                            raw_result=raw_result,
                            url_normalizer=url_normalizer,
                            metadata_extractor=metadata_extractor
                        )
                        
                        processed_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing raw result {raw_result.id}: {str(e)}")
                        error_count += 1
                        continue
            
            # Update progress after each batch
            progress_percentage = 25 + int((processed_count / total_results) * 50)  # 25-75%
            processing_session.update_progress(
                progress_percentage, 
                processed_count=processed_count,
                errors_count=error_count
            )
        
        # Log normalization completion
        SessionActivity.log_activity(
            session=session,
            action='RESULTS_PROCESSED',
            description=f'Normalization completed: {processed_count} results processed, {error_count} errors',
            user=user,
            details={
                'stage': 'normalization',
                'processed_count': processed_count,
                'error_count': error_count,
                'total_raw_results': total_results
            }
        )
        
        logger.info(f"Normalization completed: {processed_count}/{total_results} processed")
        
        return {
            'status': 'completed',
            'stage': 'normalization',
            'session_id': session_id,
            'processed_count': processed_count,
            'error_count': error_count,
            'total_count': total_results
        }
        
    except Exception as e:
        logger.error(f"Error during normalization: {str(e)}")
        
        # Update processing session with error
        try:
            processing_session = ProcessingSession.objects.get(search_session_id=session_id)
            processing_session.processing_errors += 1
            processing_session.save()
        except:
            pass
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {
            'status': 'error',
            'stage': 'normalization',
            'message': str(e)
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def deduplicate_results_task(self, previous_result: Dict[str, Any], session_id: str, user_id: str) -> Dict[str, Any]:
    """
    Identify and link duplicate results.
    
    This task implements:
    REQ-FR-RM-7: Basic Deduplication
    REQ-TR-RM-3: Deduplication Infrastructure
    
    Process:
    1. Fetch all ProcessedResult records for the session
    2. Apply deduplication algorithms (URL and title-based)
    3. Create DuplicateRelationship records
    4. Mark duplicates in ProcessedResult records
    5. Update processing progress
    
    Args:
        previous_result: Result from normalization task
        session_id (str): UUID of the SearchSession
        user_id (str): UUID of the user
        
    Returns:
        dict: Deduplication result with statistics
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get session, user, and processing session
        session = SearchSession.objects.get(id=session_id)
        user = User.objects.get(id=user_id)
        processing_session = ProcessingSession.objects.get(search_session=session)
        
        # Update progress to deduplication stage
        processing_session.update_progress(75)
        
        logger.info(f"Starting deduplication for session {session.title}")
        
        # Get all processed results for this session
        processed_results = ProcessedResult.objects.filter(session=session).order_by('processed_at')
        
        if not processed_results.exists():
            logger.warning(f"No processed results found for session {session_id}")
            return {
                'status': 'skipped',
                'stage': 'deduplication',
                'message': 'No processed results to deduplicate'
            }
        
        # Initialize deduplication engine
        dedup_engine = DeduplicationEngine()
        
        # Find duplicates
        duplicate_pairs = dedup_engine.find_duplicates(processed_results)
        
        duplicates_created = 0
        
        # Create duplicate relationships
        with transaction.atomic():
            for original_result, duplicate_result, method, similarity_score in duplicate_pairs:
                
                # Determine confidence level based on similarity score
                if similarity_score >= 0.9:
                    confidence = 'high'
                elif similarity_score >= 0.7:
                    confidence = 'medium'
                else:
                    confidence = 'low'
                
                # Create duplicate relationship
                DuplicateRelationship.objects.get_or_create(
                    original_result=original_result,
                    duplicate_result=duplicate_result,
                    defaults={
                        'detection_method': method,
                        'similarity_score': similarity_score,
                        'confidence_level': confidence
                    }
                )
                
                # Mark duplicate result
                duplicate_result.is_duplicate = True
                duplicate_result.save(update_fields=['is_duplicate'])
                
                duplicates_created += 1
        
        # Update processing session with duplicate count
        processing_session.update_progress(
            90,
            duplicates_count=duplicates_created
        )
        
        # Log deduplication completion
        SessionActivity.log_activity(
            session=session,
            action='RESULTS_PROCESSED',
            description=f'Deduplication completed: {duplicates_created} duplicate relationships created',
            user=user,
            details={
                'stage': 'deduplication',
                'duplicates_found': duplicates_created,
                'total_processed_results': processed_results.count(),
                'unique_results': processed_results.count() - duplicates_created
            }
        )
        
        logger.info(f"Deduplication completed: {duplicates_created} duplicates found")
        
        return {
            'status': 'completed',
            'stage': 'deduplication',
            'session_id': session_id,
            'duplicates_found': duplicates_created,
            'total_processed': processed_results.count(),
            'unique_results': processed_results.count() - duplicates_created
        }
        
    except Exception as e:
        logger.error(f"Error during deduplication: {str(e)}")
        
        # Update processing session with error
        try:
            processing_session = ProcessingSession.objects.get(search_session_id=session_id)
            processing_session.processing_errors += 1
            processing_session.save()
        except:
            pass
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))
        
        return {
            'status': 'error',
            'stage': 'deduplication',
            'message': str(e)
        }


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def monitor_processing_completion_task(self, previous_result: Dict[str, Any], session_id: str, user_id: str) -> Dict[str, Any]:
    """
    Monitor and finalize the processing workflow.
    
    This task implements:
    REQ-FR-RM-1: Automated Results Processing completion
    REQ-FR-RM-6: Processing Status Notifications
    
    Process:
    1. Verify all processing stages completed successfully
    2. Update ProcessingSession to completed status
    3. Transition SearchSession to ready_for_review
    4. Send completion notifications
    5. Log final statistics
    
    Args:
        previous_result: Result from deduplication task
        session_id (str): UUID of the SearchSession
        user_id (str): UUID of the user
        
    Returns:
        dict: Final processing result with complete statistics
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get session, user, and processing session
        session = SearchSession.objects.get(id=session_id)
        user = User.objects.get(id=user_id)
        processing_session = ProcessingSession.objects.get(search_session=session)
        
        logger.info(f"Finalizing processing for session {session.title}")
        
        # Gather final statistics
        processed_results = ProcessedResult.objects.filter(session=session)
        total_processed = processed_results.count()
        unique_results = processed_results.filter(is_duplicate=False).count()
        duplicate_count = processed_results.filter(is_duplicate=True).count()
        
        # Complete processing session
        processing_session.complete_processing()
        
        # Transition search session to ready_for_review
        with transaction.atomic():
            old_status = session.status
            session.status = SearchSession.Status.READY_FOR_REVIEW
            session.updated_by = user
            session.save()
            
            # Log final completion
            SessionActivity.log_activity(
                session=session,
                action='STATUS_CHANGED',
                description=f'Results processing completed successfully',
                user=user,
                old_status=old_status,
                new_status='ready_for_review',
                details={
                    'processing_summary': {
                        'total_raw_results': processing_session.raw_results_count,
                        'processed_results': total_processed,
                        'unique_results': unique_results,
                        'duplicates_found': duplicate_count,
                        'processing_errors': processing_session.processing_errors,
                        'processing_duration': str(timezone.now() - processing_session.started_at)
                    }
                }
            )
        
        logger.info(
            f"Processing completed for session {session.title}: "
            f"{total_processed} processed, {unique_results} unique, {duplicate_count} duplicates"
        )
        
        return {
            'status': 'completed',
            'session_id': session_id,
            'session_status': 'ready_for_review',
            'processing_summary': {
                'total_raw_results': processing_session.raw_results_count,
                'processed_results': total_processed,
                'unique_results': unique_results,
                'duplicates_found': duplicate_count,
                'processing_errors': processing_session.processing_errors
            }
        }
        
    except Exception as e:
        logger.error(f"Error finalizing processing: {str(e)}")
        
        # Mark processing as failed
        try:
            processing_session = ProcessingSession.objects.get(search_session_id=session_id)
            processing_session.fail_processing(str(e))
            
            # Also mark session as failed
            session = SearchSession.objects.get(id=session_id)
            session.status = SearchSession.Status.FAILED
            session.save()
        except:
            pass
        
        # Retry with shorter delay
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=15 * (2 ** self.request.retries))
        
        return {
            'status': 'error',
            'message': f'Failed to finalize processing: {str(e)}'
        }


# Retry and recovery tasks

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def retry_failed_processing_task(self, session_id: str, user_id: str) -> Dict[str, Any]:
    """
    Retry failed processing for a session.
    
    This task implements:
    REQ-TR-RM-4: Error Handling and Recovery
    
    Args:
        session_id (str): UUID of the SearchSession to retry
        user_id (str): UUID of the user requesting retry
        
    Returns:
        dict: Retry operation result
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        session = SearchSession.objects.get(id=session_id)
        user = User.objects.get(id=user_id)
        
        # Get or reset processing session
        processing_session, created = ProcessingSession.objects.get_or_create(
            search_session=session,
            defaults={'status': 'pending', 'retry_count': 0}
        )
        
        if not created:
            processing_session.retry_count += 1
            processing_session.status = 'pending'
            processing_session.error_message = ''
            processing_session.save()
        
        # Log retry attempt
        SessionActivity.log_activity(
            session=session,
            action='ERROR_RECOVERY',
            description=f'Retrying failed results processing (attempt #{processing_session.retry_count})',
            user=user,
            details={
                'retry_count': processing_session.retry_count,
                'previous_error': processing_session.error_message
            }
        )
        
        # Restart processing
        result = process_session_results_task.apply_async(
            args=[session_id, user_id],
            countdown=5  # Start in 5 seconds
        )
        
        return {
            'status': 'retrying',
            'session_id': session_id,
            'retry_count': processing_session.retry_count,
            'task_id': result.id
        }
        
    except Exception as e:
        logger.error(f"Error retrying processing: {str(e)}")
        return {
            'status': 'error',
            'message': str(e)
        }