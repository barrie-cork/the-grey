"""
Celery tasks for asynchronous SERP execution.
Handles search execution, result processing, and session monitoring.
"""

import logging
from decimal import Decimal
from typing import Any, Dict

from celery import group, shared_task
from django.db import transaction
from django.utils import timezone

from apps.core.config import get_config
from .models import SearchExecution
from .recovery import recovery_manager
from .services.result_processor import ResultProcessor
from .services.serper_client import SerperAPIError, SerperClient
# from .services.usage_tracker import UsageTracker  # TODO: Create usage_tracker module

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
)
def initiate_search_session_execution_task(self, session_id: str) -> Dict[str, Any]:
    """
    Initiate execution of all queries for a search session.

    Args:
        session_id: ID of the SearchSession to execute

    Returns:
        Dictionary with execution summary
    """
    from apps.review_manager.models import SearchSession
    from apps.search_strategy.models import SearchQuery

    logger.info(f"Starting search session execution for session {session_id}")

    try:
        # Get session and validate status
        session = SearchSession.objects.select_related("owner").get(id=session_id)

        if session.status != "ready_to_execute":
            logger.warning(f"Session {session_id} not in ready_to_execute status")
            return {
                "success": False,
                "error": "Session not ready for execution",
                "session_id": str(session_id),
            }

        # Update session status
        session.status = "executing"
        session.started_at = timezone.now()
        session.save(update_fields=["status", "started_at"])

        # Get active queries
        queries = SearchQuery.objects.filter(
            strategy__session=session, is_active=True
        ).order_by("execution_order", "created_at")

        if not queries.exists():
            logger.error(f"No active queries found for session {session_id}")
            session.status = "ready_to_execute"
            session.save(update_fields=["status"])
            return {
                "success": False,
                "error": "No active queries found",
                "session_id": str(session_id),
            }

        # Create execution tasks for each query
        execution_tasks = []
        for query in queries:
            # Create SearchExecution record
            execution = SearchExecution.objects.create(
                query=query,
                initiated_by=session.owner,
                status="pending",
                celery_task_id=self.request.id,
            )

            # Create task for this query
            task = perform_serp_query_task.si(str(execution.id), str(query.id))
            execution_tasks.append(task)

        # Execute all queries in parallel with a callback
        job = group(execution_tasks) | monitor_session_completion_task.si(
            str(session_id)
        )
        job.apply_async()

        logger.info(
            f"Initiated {len(execution_tasks)} query executions for session {session_id}"
        )

        return {
            "success": True,
            "session_id": str(session_id),
            "queries_count": len(execution_tasks),
            "status": "executing",
        }

    except SearchSession.DoesNotExist:
        logger.error(f"SearchSession {session_id} not found")
        return {
            "success": False,
            "error": "Session not found",
            "session_id": str(session_id),
        }
    except Exception as e:
        logger.error(f"Error initiating session execution: {str(e)}")

        # Revert session status on error
        try:
            session = SearchSession.objects.get(id=session_id)
            session.status = "ready_to_execute"
            session.save(update_fields=["status"])
        except:
            pass

        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    retry_backoff=True,
    retry_jitter=True,
)
def perform_serp_query_task(self, execution_id: str, query_id: str) -> Dict[str, Any]:
    """
    Perform a single SERP query execution.

    Args:
        execution_id: ID of the SearchExecution
        query_id: ID of the SearchQuery

    Returns:
        Dictionary with execution results
    """
    from apps.search_strategy.models import SearchQuery

    logger.info(f"Executing SERP query for execution {execution_id}")

    try:
        # Get execution and query
        execution = SearchExecution.objects.select_related("query").get(id=execution_id)
        query = SearchQuery.objects.get(id=query_id)

        # Update execution status
        execution.status = "running"
        execution.started_at = timezone.now()
        execution.celery_task_id = self.request.id
        execution.save(update_fields=["status", "started_at", "celery_task_id"])

        # Initialize services
        serper_client = SerperClient()
        result_processor = ResultProcessor()

        # Use the pre-built query text
        search_query = query.query_text

        # Get configuration
        config = get_config()
        
        # Get configuration from the strategy (allows overrides)
        strategy = query.strategy
        file_types = strategy.search_config.get("file_types", config.search.default_file_types)
        
        # Get search location from strategy or use configured default
        location = strategy.search_config.get("location", config.search.default_location)
        
        # Build API parameters with configuration values
        api_params = {
            "q": search_query,
            "num": strategy.search_config.get("num_results", config.search.default_num_results),
            "language": strategy.search_config.get("language", config.search.default_language),
            "file_types": file_types,
        }
        
        # Only add location if specified (None means global search)
        if location:
            api_params["location"] = location

        # Store parameters
        execution.api_parameters = api_params
        execution.save(update_fields=["api_parameters"])

        # Execute search with retry logic
        try:
            results, metadata = serper_client.search(
                search_query,
                num_results=api_params["num"],
                use_cache=True,
                **{
                    k: v
                    for k, v in api_params.items()
                    if k not in ["q", "num"] and v is not None
                },
            )

        except SerperAPIError as e:
            # Simple retry logic
            if recovery_manager.should_retry(e, execution.retry_count):
                # Update retry count
                execution.retry_count += 1
                execution.save(update_fields=["retry_count"])

                # Get retry delay
                delay = recovery_manager.get_retry_delay(e)
                
                # Retry with delay
                raise self.retry(exc=e, countdown=delay)
            else:
                # Can't retry, mark as failed
                execution.status = "failed"
                execution.error_message = str(e)
                execution.completed_at = timezone.now()
                execution.save(
                    update_fields=["status", "error_message", "completed_at"]
                )

                return {
                    "success": False,
                    "execution_id": str(execution_id),
                    "error": str(e),
                    "error_category": recovery_manager.get_error_category(str(e)),
                }

        # Process successful results
        organic_results = results.get("organic", [])

        if not organic_results:
            logger.warning(f"No results returned for execution {execution_id}")
            execution.status = "completed"
            execution.results_count = 0
            execution.completed_at = timezone.now()
            execution.save(update_fields=["status", "results_count", "completed_at"])

            return {
                "success": True,
                "execution_id": str(execution_id),
                "results_count": 0,
            }

        # Process and store results
        processed_count, duplicate_count, errors = (
            result_processor.process_search_results(
                execution_id=execution_id, 
                raw_results=organic_results, 
                batch_size=config.processing.batch_size
            )
        )

        # Update execution with results
        execution.status = "completed"
        execution.results_count = processed_count
        execution.completed_at = timezone.now()
        execution.save(
            update_fields=[
                "status",
                "results_count",
                "completed_at",
            ]
        )

        # Usage tracking removed for simplification

        # Query execution tracking is handled via SearchExecution model

        logger.info(
            f"Successfully executed query {query_id}: "
            f"{processed_count} results, {duplicate_count} duplicates"
        )

        return {
            "success": True,
            "execution_id": str(execution_id),
            "results_count": processed_count,
            "duplicates_count": duplicate_count,
            "errors": errors,
        }

    except SearchExecution.DoesNotExist:
        logger.error(f"SearchExecution {execution_id} not found")
        return {
            "success": False,
            "error": "Execution not found",
            "execution_id": execution_id,
        }
    except Exception as e:
        logger.error(f"Unexpected error in SERP query execution: {str(e)}")

        # Update execution status
        try:
            execution = SearchExecution.objects.get(id=execution_id)

            if self.request.retries >= self.max_retries:
                execution.status = "failed"
                execution.error_message = f"Max retries exceeded: {str(e)}"
                execution.completed_at = timezone.now()
                execution.save(
                    update_fields=["status", "error_message", "completed_at"]
                )

            else:
                execution.retry_count = self.request.retries
                execution.save(update_fields=["retry_count"])
        except:
            pass

        raise self.retry(exc=e)


@shared_task
def monitor_session_completion_task(session_id: str) -> Dict[str, Any]:
    """
    Monitor search session completion and trigger next steps.

    Args:
        session_id: ID of the SearchSession

    Returns:
        Dictionary with session summary
    """
    from apps.review_manager.models import SearchSession

    logger.info(f"Monitoring completion for session {session_id}")

    try:
        with transaction.atomic():
            session = SearchSession.objects.select_for_update().get(id=session_id)

            # Check all executions
            executions = SearchExecution.objects.filter(
                query__strategy__session=session
            ).select_related("query")

            total_executions = executions.count()
            completed_executions = executions.filter(
                status__in=["completed", "failed", "cancelled"]
            ).count()

            logger.info(
                f"Session {session_id}: {completed_executions}/{total_executions} executions completed"
            )

            # Check if all executions are done
            if completed_executions < total_executions:
                # Not all done, check again later
                monitor_session_completion_task.apply_async(
                    args=[session_id], countdown=30  # Check again in 30 seconds
                )
                return {
                    "session_id": str(session_id),
                    "status": "executing",
                    "progress": f"{completed_executions}/{total_executions}",
                }

            # All executions completed
            successful_executions = executions.filter(status="completed")
            failed_executions = executions.filter(status="failed")

            # Calculate totals
            total_results = sum(e.results_count for e in successful_executions)

            # Update session status
            if failed_executions.exists() and not successful_executions.exists():
                # All failed
                session.status = "ready_to_execute"  # Allow retry
                session.completed_at = timezone.now()
                session.save(update_fields=["status", "completed_at"])

                # Notify about failures
                _send_session_notification(
                    session,
                    f"All search executions failed for session '{session.title}'. "
                    f"Please review error logs and retry.",
                )

                return {
                    "session_id": str(session_id),
                    "status": "all_failed",
                    "successful": 0,
                    "failed": failed_executions.count(),
                }
            else:
                # At least some succeeded, move to processing
                session.status = "processing_results"
                session.completed_at = timezone.now()
                session.total_results = total_results
                session.save(update_fields=["status", "completed_at", "total_results"])

                # Trigger result processing
                from apps.results_manager.tasks import process_session_results_task

                process_session_results_task.delay(str(session_id))

                # Send completion notification
                _send_session_notification(
                    session,
                    f"Search execution completed for '{session.title}'. "
                    f"Found {total_results} results across {successful_executions.count()} queries. "
                    f"Processing results now.",
                )

                return {
                    "session_id": str(session_id),
                    "status": "processing_results",
                    "successful": successful_executions.count(),
                    "failed": failed_executions.count(),
                    "total_results": total_results,
                }

    except SearchSession.DoesNotExist:
        logger.error(f"SearchSession {session_id} not found")
        return {
            "success": False,
            "error": "Session not found",
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"Error monitoring session completion: {str(e)}")

        # Retry monitoring later
        monitor_session_completion_task.apply_async(args=[session_id], countdown=60)

        return {"session_id": str(session_id), "status": "error", "error": str(e)}


def _send_execution_notification(execution: SearchExecution, message: str):
    """Send notification about execution issue."""
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail

    User = get_user_model()

    if execution.initiated_by and execution.initiated_by.email:
        subject = f"Search Execution Alert - {execution.query.strategy.session.title}"

        full_message = f"""
        {message}
        
        Execution Details:
        - Query: {execution.query.query_text[:100]}...
        - Status: {execution.status}
        - Attempts: {execution.retry_count + 1}
        - Error: {execution.error_message}
        
        You can view more details in the execution status page.
        """

        try:
            send_mail(
                subject,
                full_message,
                settings.DEFAULT_FROM_EMAIL,
                [execution.initiated_by.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send notification email: {str(e)}")


def _send_session_notification(session: "SearchSession", message: str):
    """Send notification about session status."""
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core.mail import send_mail

    User = get_user_model()

    if session.owner and session.owner.email:
        subject = f"Search Session Update - {session.title}"

        full_message = f"""
        {message}
        
        You can view your session in the dashboard.
        """

        try:
            send_mail(
                subject,
                full_message,
                settings.DEFAULT_FROM_EMAIL,
                [session.owner.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Failed to send notification email: {str(e)}")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
)
def retry_failed_execution_task(
    self, execution_id: str, delay_seconds: int = 0
) -> Dict[str, Any]:
    """
    Retry a failed search execution.

    Args:
        execution_id: ID of the SearchExecution to retry
        delay_seconds: Optional delay before retrying

    Returns:
        Dictionary with retry result
    """
    logger.info(f"Retrying failed execution {execution_id} with {delay_seconds}s delay")

    try:
        # Get execution
        execution = SearchExecution.objects.select_related("query", "initiated_by").get(
            id=execution_id
        )

        # Validate can retry
        if not execution.can_retry():
            logger.error(f"Execution {execution_id} cannot be retried")
            return {
                "success": False,
                "error": "Execution cannot be retried",
                "execution_id": str(execution_id),
            }

        # Update execution status
        execution.status = "pending"
        execution.error_message = ""
        execution.celery_task_id = self.request.id
        execution.save(update_fields=["status", "error_message", "celery_task_id"])

        # If delay requested, schedule for later
        if delay_seconds > 0:
            perform_serp_query_task.apply_async(
                args=[str(execution.id), str(execution.query.id)],
                countdown=delay_seconds,
            )

            return {
                "success": True,
                "execution_id": str(execution_id),
                "scheduled_delay": delay_seconds,
                "message": f"Retry scheduled for {delay_seconds} seconds",
            }
        else:
            # Execute immediately
            result = perform_serp_query_task.delay(
                str(execution.id), str(execution.query.id)
            )

            return {
                "success": True,
                "execution_id": str(execution_id),
                "task_id": result.id,
                "message": "Retry started immediately",
            }

    except SearchExecution.DoesNotExist:
        logger.error(f"SearchExecution {execution_id} not found")
        return {
            "success": False,
            "error": "Execution not found",
            "execution_id": execution_id,
        }
    except Exception as e:
        logger.error(f"Error retrying execution {execution_id}: {str(e)}")
        return {"success": False, "error": str(e), "execution_id": str(execution_id)}
