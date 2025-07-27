"""
Celery tasks for results processing pipeline.

This module implements the Results Manager processing pipeline using Celery tasks
for background processing of search results with progress tracking and error handling.
"""

import logging
from typing import Any, Dict, List, Optional

from celery import chain, group, shared_task
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.serp_execution.models import RawSearchResult

from .models import DuplicateGroup, ProcessedResult, ProcessingSession
from .utils import detect_duplicates, get_processing_statistics, normalize_url

logger = logging.getLogger(__name__)

# Configuration constants
BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds


def _validate_session(session_id: str) -> SearchSession:
    """Validate and retrieve search session."""
    try:
        return SearchSession.objects.get(id=session_id)
    except SearchSession.DoesNotExist:
        logger.error(f"SearchSession {session_id} not found")
        raise


def _get_or_create_processing_session(session: SearchSession) -> ProcessingSession:
    """Get or create processing session."""
    processing_session, created = ProcessingSession.objects.get_or_create(
        search_session=session, defaults={"status": "pending"}
    )
    return processing_session


def _check_already_completed(processing_session: ProcessingSession, session_id: str) -> Optional[Dict[str, Any]]:
    """Check if session is already processed."""
    if processing_session.status == "completed":
        logger.info(f"Session {session_id} already processed")
        return {
            "status": "already_completed",
            "session_id": session_id,
            "processed_count": processing_session.processed_count,
        }
    return None


def _get_raw_results_count(session: SearchSession) -> int:
    """Get count of unprocessed raw results."""
    return RawSearchResult.objects.filter(
        execution__query__strategy__session=session, is_processed=False
    ).count()


def _handle_no_results(processing_session: ProcessingSession, session_id: str) -> Dict[str, Any]:
    """Handle case when no raw results found."""
    logger.warning(f"No raw results found for session {session_id}")
    processing_session.status = "completed"
    processing_session.save()
    return {
        "status": "no_results",
        "session_id": session_id,
        "message": "No raw results to process",
    }


def _start_processing(session: SearchSession, processing_session: ProcessingSession, 
                     total_results: int, task_id: str) -> None:
    """Update session status and start processing."""
    session.status = "processing_results"
    session.save(update_fields=["status"])
    processing_session.start_processing(
        total_raw_results=total_results, celery_task_id=task_id
    )


def _mark_processing_failed(session_id: str, exc: Exception) -> None:
    """Mark processing session as failed."""
    try:
        processing_session = ProcessingSession.objects.get(
            search_session_id=session_id
        )
        processing_session.fail_processing(
            error_message=f"Failed to start processing: {str(exc)}",
            error_details={"exception_type": type(exc).__name__},
        )
    except ProcessingSession.DoesNotExist:
        pass


def _handle_processing_error(session_id: str, exc: Exception, retries: int) -> Dict[str, Any]:
    """Handle processing errors and retries."""
    _mark_processing_failed(session_id, exc)

    # Check if should retry
    if retries < MAX_RETRIES:
        retry_countdown = RETRY_DELAY * (2**retries)
        logger.info(
            f"Retrying processing for session {session_id} in {retry_countdown}s"
        )
        # Caller will handle the retry
        raise

    return {"status": "failed", "error": str(exc)}


@shared_task(bind=True, max_retries=MAX_RETRIES)
def process_session_results_task(self, session_id: str) -> Dict[str, Any]:
    """
    Main orchestration task for processing all results for a search session.

    This task coordinates the entire processing pipeline:
    1. Initialize processing session
    2. Process results in batches
    3. Run deduplication
    4. Finalize processing

    Args:
        session_id: UUID string of the SearchSession

    Returns:
        Dictionary with processing results and statistics
    """
    logger.info(f"Starting results processing for session {session_id}")

    try:
        # Validate and get session
        session = _validate_session(session_id)
        
        # Get or create processing session
        processing_session = _get_or_create_processing_session(session)
        
        # Check if already completed
        completed_result = _check_already_completed(processing_session, session_id)
        if completed_result:
            return completed_result
        
        # Get raw results count
        total_results = _get_raw_results_count(session)
        
        # Handle no results case
        if total_results == 0:
            return _handle_no_results(processing_session, session_id)
        
        # Start processing
        _start_processing(session, processing_session, total_results, self.request.id)
        
        # Create processing workflow
        workflow = create_processing_workflow.delay(
            session_id=session_id, processing_session_id=str(processing_session.id)
        )

        return {
            "status": "started",
            "session_id": session_id,
            "total_results": total_results,
            "workflow_task_id": workflow.id,
        }

    except SearchSession.DoesNotExist:
        return {"status": "error", "message": f"Session {session_id} not found"}

    except Exception as exc:
        logger.error(f"Error starting processing for session {session_id}: {str(exc)}")
        result = _handle_processing_error(session_id, exc, self.request.retries)
        
        # Re-raise for Celery retry if needed
        if self.request.retries < MAX_RETRIES:
            retry_countdown = RETRY_DELAY * (2**self.request.retries)
            raise self.retry(countdown=retry_countdown, exc=exc)
        
        return result


@shared_task(bind=True)
def create_processing_workflow(
    self, session_id: str, processing_session_id: str
) -> Dict[str, Any]:
    """
    Create and execute the processing workflow.

    Args:
        session_id: UUID string of the SearchSession
        processing_session_id: UUID string of the ProcessingSession

    Returns:
        Dictionary with workflow execution results
    """
    try:
        processing_session = ProcessingSession.objects.get(id=processing_session_id)

        # Get raw results in batches
        raw_results = RawSearchResult.objects.filter(
            execution__query__strategy__session_id=session_id, is_processed=False
        ).values_list("id", flat=True)

        batch_ids = [
            list(raw_results[i : i + BATCH_SIZE])
            for i in range(0, len(raw_results), BATCH_SIZE)
        ]

        # Create batch processing tasks
        batch_tasks = [
            process_batch_task.s(session_id, processing_session_id, batch)
            for batch in batch_ids
        ]

        # Create workflow: batch processing -> deduplication -> finalization
        workflow = chain(
            group(*batch_tasks),
            run_deduplication_task.s(session_id, processing_session_id),
            finalize_processing_task.s(session_id, processing_session_id),
        )

        # Execute workflow
        result = workflow.apply_async()

        return {
            "status": "workflow_created",
            "batch_count": len(batch_tasks),
            "workflow_id": result.id,
        }

    except Exception as exc:
        logger.error(f"Error creating workflow for session {session_id}: {str(exc)}")
        processing_session.fail_processing(
            error_message=f"Workflow creation failed: {str(exc)}"
        )
        return {"status": "failed", "error": str(exc)}


@shared_task(bind=True, max_retries=MAX_RETRIES)
def process_batch_task(
    self, session_id: str, processing_session_id: str, raw_result_ids: List[str]
) -> Dict[str, Any]:
    """
    Process a batch of raw results.

    Args:
        session_id: UUID string of the SearchSession
        processing_session_id: UUID string of the ProcessingSession
        raw_result_ids: List of RawSearchResult IDs to process

    Returns:
        Dictionary with batch processing results
    """
    logger.info(
        f"Processing batch of {len(raw_result_ids)} results for session {session_id}"
    )

    try:
        processing_session = ProcessingSession.objects.get(id=processing_session_id)
        processing_session.update_progress("url_normalization", 10)

        # Get raw results
        raw_results = RawSearchResult.objects.filter(
            id__in=raw_result_ids
        ).select_related("execution", "execution__query")

        processed_count = 0
        error_count = 0

        # Process each raw result
        for raw_result in raw_results:
            try:
                processed_result = process_single_result(raw_result, session_id)
                if processed_result:
                    processed_count += 1

                    # Mark raw result as processed
                    raw_result.is_processed = True
                    raw_result.save(update_fields=["is_processed"])

            except Exception as exc:
                logger.error(f"Error processing result {raw_result.id}: {str(exc)}")
                error_count += 1

                # Record error in raw result
                raw_result.processing_error = str(exc)
                raw_result.save(update_fields=["processing_error"])

                # Add error to processing session
                processing_session.add_error(
                    error_message=f"Failed to process result {raw_result.id}",
                    error_details={
                        "raw_result_id": str(raw_result.id),
                        "error": str(exc),
                        "title": raw_result.title,
                        "url": raw_result.link,
                    },
                )

        # Update progress
        processing_session.update_progress(
            stage="metadata_extraction",
            stage_progress=50,
            processed_count=processing_session.processed_count + processed_count,
            error_count=processing_session.error_count + error_count,
        )

        return {
            "status": "completed",
            "processed_count": processed_count,
            "error_count": error_count,
            "batch_size": len(raw_result_ids),
        }

    except Exception as exc:
        logger.error(f"Batch processing failed for session {session_id}: {str(exc)}")

        if self.request.retries < MAX_RETRIES:
            retry_countdown = RETRY_DELAY * (2**self.request.retries)
            raise self.retry(countdown=retry_countdown, exc=exc)

        return {"status": "failed", "error": str(exc)}


def process_single_result(
    raw_result: RawSearchResult, session_id: str
) -> Optional[ProcessedResult]:
    """
    Process a single raw search result into a ProcessedResult.

    Args:
        raw_result: RawSearchResult instance
        session_id: Session ID for the result

    Returns:
        ProcessedResult instance or None if processing failed
    """
    try:
        with transaction.atomic():
            # Normalize URL
            normalized_url = normalize_url(raw_result.link)

            # Simple document type detection from URL
            document_type = "pdf" if ".pdf" in raw_result.link.lower() else "webpage"

            # Create ProcessedResult
            processed_result = ProcessedResult.objects.create(
                session_id=session_id,
                raw_result=raw_result,
                title=raw_result.title,
                url=normalized_url,
                snippet=raw_result.snippet,
                publication_date=raw_result.detected_date,
                publication_year=(
                    raw_result.detected_date.year if raw_result.detected_date else None
                ),
                document_type=document_type,
                language="en",  # Default to English
                source_organization="",  # Keep simple
                full_text_url=raw_result.link if raw_result.has_pdf else "",
                is_pdf=raw_result.has_pdf,
            )

            return processed_result

    except IntegrityError as exc:
        logger.warning(f"Duplicate result detected for {raw_result.link}: {str(exc)}")
        return None
    except Exception as exc:
        logger.error(f"Error processing result {raw_result.id}: {str(exc)}")
        raise


@shared_task(bind=True)
def run_deduplication_task(
    self, batch_results: List[Dict], session_id: str, processing_session_id: str
) -> Dict[str, Any]:
    """
    Run deduplication across all processed results for a session.

    Args:
        batch_results: Results from batch processing tasks
        session_id: UUID string of the SearchSession
        processing_session_id: UUID string of the ProcessingSession

    Returns:
        Dictionary with deduplication results
    """
    logger.info(f"Running deduplication for session {session_id}")

    try:
        processing_session = ProcessingSession.objects.get(id=processing_session_id)
        processing_session.update_progress("deduplication", 0)

        # Get all processed results for the session
        results = ProcessedResult.objects.filter(session_id=session_id).select_related(
            "duplicate_group"
        )

        # Run duplicate detection
        duplicate_groups = detect_duplicates(results, similarity_threshold=0.85)

        duplicate_count = 0

        # Create duplicate groups
        for group_data in duplicate_groups:
            canonical_result = group_data["canonical_result"]
            duplicates = group_data["duplicates"]

            # Create duplicate group
            duplicate_group = DuplicateGroup.objects.create(
                session_id=session_id,
                canonical_url=canonical_result.url,
                similarity_type=group_data["similarity_type"],
                result_count=len(duplicates) + 1,
            )

            # Assign results to group
            canonical_result.duplicate_group = duplicate_group
            canonical_result.save(update_fields=["duplicate_group"])

            for duplicate in duplicates:
                duplicate.duplicate_group = duplicate_group
                duplicate.save(update_fields=["duplicate_group"])
                duplicate_count += 1

        # Update progress - deduplication completed
        processing_session.update_progress(
            stage="finalization", stage_progress=0, duplicate_count=duplicate_count
        )

        return {
            "status": "completed",
            "duplicate_groups_created": len(duplicate_groups),
            "total_duplicates": duplicate_count,
        }

    except Exception as exc:
        logger.error(f"Deduplication failed for session {session_id}: {str(exc)}")
        processing_session.add_error(error_message=f"Deduplication failed: {str(exc)}")
        return {"status": "failed", "error": str(exc)}


@shared_task(bind=True)
def finalize_processing_task(
    self, dedup_results: Dict, session_id: str, processing_session_id: str
) -> Dict[str, Any]:
    """
    Finalize results processing and update session status.

    Args:
        dedup_results: Results from deduplication task
        session_id: UUID string of the SearchSession
        processing_session_id: UUID string of the ProcessingSession

    Returns:
        Dictionary with final processing results
    """
    logger.info(f"Finalizing processing for session {session_id}")

    try:
        processing_session = ProcessingSession.objects.get(id=processing_session_id)
        session = SearchSession.objects.get(id=session_id)

        # Results are now ready for review after deduplication

        processing_session.update_progress("finalization", 100)

        # Get final statistics
        stats = get_processing_statistics(session_id)

        # Complete processing
        processing_session.complete_processing()

        # Update session status
        session.status = "ready_for_review"
        session.save(update_fields=["status"])

        logger.info(
            f"Processing completed for session {session_id}: {stats['processed_results']} results"
        )

        return {
            "status": "completed",
            "session_id": session_id,
            "statistics": stats,
            "processing_time_seconds": processing_session.duration_seconds,
        }

    except Exception as exc:
        logger.error(f"Finalization failed for session {session_id}: {str(exc)}")
        processing_session.fail_processing(
            error_message=f"Finalization failed: {str(exc)}"
        )
        return {"status": "failed", "error": str(exc)}


@shared_task
def cleanup_failed_processing(days_old: int = 7) -> Dict[str, Any]:
    """
    Clean up failed processing sessions older than specified days.

    Args:
        days_old: Number of days old to consider for cleanup

    Returns:
        Dictionary with cleanup results
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=days_old)

    failed_sessions = ProcessingSession.objects.filter(
        status="failed", created_at__lt=cutoff_date
    )

    count = failed_sessions.count()
    failed_sessions.delete()

    logger.info(
        f"Cleaned up {count} failed processing sessions older than {days_old} days"
    )

    return {
        "status": "completed",
        "cleaned_up_count": count,
        "cutoff_date": cutoff_date.isoformat(),
    }


@shared_task
def retry_failed_processing_task(session_id: str) -> Dict[str, Any]:
    """
    Retry processing for a failed session.

    Args:
        session_id: UUID string of the SearchSession

    Returns:
        Dictionary with retry results
    """
    try:
        processing_session = ProcessingSession.objects.get(search_session_id=session_id)

        if processing_session.status != "failed":
            return {
                "status": "not_retryable",
                "message": f"Session status is {processing_session.status}, not failed",
            }

        # Reset processing session
        processing_session.status = "pending"
        processing_session.retry_count += 1
        processing_session.error_details = []
        processing_session.error_count = 0
        processing_session.processed_count = 0
        processing_session.duplicate_count = 0
        processing_session.save()

        # Reset processed flags on raw results
        RawSearchResult.objects.filter(execution__query__strategy__session_id=session_id).update(
            is_processed=False, processing_error=""
        )

        # Delete existing processed results
        ProcessedResult.objects.filter(session_id=session_id).delete()

        # Restart processing
        result = process_session_results_task.delay(session_id)

        return {
            "status": "restarted",
            "retry_count": processing_session.retry_count,
            "task_id": result.id,
        }

    except ProcessingSession.DoesNotExist:
        return {"status": "error", "message": "Processing session not found"}
    except Exception as exc:
        logger.error(f"Error retrying processing for session {session_id}: {str(exc)}")
        return {"status": "error", "error": str(exc)}
