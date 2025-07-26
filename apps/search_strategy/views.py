import json
import logging
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.review_manager.models import SearchSession, SessionActivity

from .forms import SearchStrategyForm
from .models import SearchQuery, SearchStrategy

logger = logging.getLogger(__name__)


class SessionOwnershipMixin:
    """Mixin to ensure user owns the search session."""

    def get_session(self) -> SearchSession:
        """Get and validate session ownership."""
        session_id = self.kwargs.get("session_id")
        session = get_object_or_404(SearchSession, id=session_id)

        if session.owner != self.request.user:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("You don't have permission to access this session.")

        return session


class SearchStrategyView(LoginRequiredMixin, SessionOwnershipMixin, TemplateView):
    """
    Main search strategy view implementing the PIC framework interface.
    Matches the UI design with Population, Interest/Intervention, Context sections.
    """

    template_name = "search_strategy/strategy_form.html"

    def dispatch(self, request, *args, **kwargs):
        """Validate session status before processing."""
        self.session = self.get_session()

        # Only allow strategy editing in certain states
        allowed_states = ["draft", "defining_search"]
        if self.session.status not in allowed_states:
            messages.error(
                request,
                f"Cannot edit search strategy. Session is in '{self.session.get_status_display()}' status.",
            )
            return redirect("review_manager:session_detail", session_id=self.session.id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add strategy data and form to context."""
        context = super().get_context_data(**kwargs)

        # Get or create strategy
        strategy, created = SearchStrategy.objects.get_or_create(
            session=self.session,
            defaults={
                "user": self.request.user,
                "search_config": {
                    "domains": [],
                    "include_general_search": True,
                    "file_types": ["pdf"],
                    "search_type": "google",
                },
            },
        )

        # Initialize form with strategy data
        form = SearchStrategyForm(instance=strategy)

        # Get strategy statistics
        stats = strategy.get_stats()

        # Get generated queries for preview
        queries = strategy.generate_queries()

        context.update(
            {
                "session": self.session,
                "strategy": strategy,
                "form": form,
                "stats": stats,
                "queries": queries,
                "is_complete": strategy.is_complete,
                "validation_errors": strategy.validation_errors,
            }
        )

        return context

    def post(self, request, *args, **kwargs):
        """Handle strategy form submission."""
        self.session = self.get_session()

        # Get or create strategy
        strategy, created = SearchStrategy.objects.get_or_create(
            session=self.session, defaults={"user": request.user}
        )

        # Initialize form with POST data
        form = SearchStrategyForm(request.POST, instance=strategy)

        if form.is_valid():
            with transaction.atomic():
                # Save the strategy
                strategy = form.save()

                # Debug: print the saved strategy data
                logger.info(f"Saved strategy - Population: {strategy.population_terms}")
                logger.info(f"Saved strategy - Interest: {strategy.interest_terms}")
                logger.info(f"Saved strategy - Context: {strategy.context_terms}")
                logger.info(f"Saved strategy - Config: {strategy.search_config}")

                # Validate completeness
                is_complete = strategy.validate_completeness()
                strategy.save(update_fields=["is_complete", "validation_errors"])

                # Generate and save queries
                self._update_search_queries(strategy)

                # Log activity
                SessionActivity.log_activity(
                    session=self.session,
                    activity_type="search_defined",
                    description="Search strategy updated",
                    user=request.user,
                    metadata={
                        "is_complete": is_complete,
                        "query_count": len(strategy.generate_queries()),
                        "stats": strategy.get_stats(),
                    },
                )

                # Update session status if strategy is complete
                if is_complete:
                    # Check if we need to transition to ready_to_execute
                    if self.session.status in ["draft", "defining_search"]:
                        if self.session.can_transition_to("ready_to_execute"):
                            old_status = self.session.status
                            self.session.status = "ready_to_execute"
                            self.session.save(update_fields=["status"])

                            SessionActivity.log_activity(
                                session=self.session,
                                activity_type="status_changed",
                                description="Session ready for execution",
                                user=request.user,
                                metadata={
                                    "old_status": old_status,
                                    "new_status": "ready_to_execute",
                                },
                            )

                            messages.success(
                                request,
                                "Search strategy completed! Session is now ready for execution.",
                            )
                        else:
                            messages.warning(
                                request,
                                "Search strategy saved, but session status could not be updated.",
                            )
                else:
                    messages.success(request, "Search strategy saved successfully.")

                # Redirect based on action
                print(f"POST data keys: {list(request.POST.keys())}")  # Debug
                print(
                    f"execute_search in POST: {'execute_search' in request.POST}"
                )  # Debug

                if "execute_search" in request.POST:
                    # Check if strategy is complete
                    if not is_complete:
                        messages.error(
                            request,
                            "Cannot execute search: Strategy is not complete. Please fill in all required fields.",
                        )
                        return redirect(
                            "search_strategy:strategy_form", session_id=self.session.id
                        )

                    # Debug current status
                    print(f"Current session status: {self.session.status}")
                    print(
                        f"Can transition to ready_to_execute: {self.session.can_transition_to('ready_to_execute')}"
                    )
                    print(
                        f"Allowed transitions: {self.session.get_allowed_transitions()}"
                    )

                    # Check if we need to update status
                    if self.session.status == "draft":
                        # First transition to defining_search
                        self.session.status = "defining_search"
                        self.session.save(update_fields=["status"])
                        SessionActivity.log_activity(
                            session=self.session,
                            activity_type="status_changed",
                            description="Session moved to defining search",
                            user=request.user,
                            metadata={
                                "old_status": "draft",
                                "new_status": "defining_search",
                            },
                        )

                    # Now transition to ready_to_execute
                    if self.session.status == "defining_search":
                        self.session.status = "ready_to_execute"
                        self.session.save(update_fields=["status"])
                        SessionActivity.log_activity(
                            session=self.session,
                            activity_type="status_changed",
                            description="Session ready for execution",
                            user=request.user,
                            metadata={
                                "old_status": "defining_search",
                                "new_status": "ready_to_execute",
                            },
                        )

                    # Refresh from database to ensure we have the latest status
                    self.session.refresh_from_db()

                    # If already ready_to_execute or can execute, proceed
                    if self.session.status in ["ready_to_execute", "executing"]:
                        # Start the execution directly and go to progress page
                        try:
                            from apps.serp_execution.tasks import (
                                initiate_search_session_execution_task,
                            )

                            # Start the execution task (it will handle status update)
                            task = initiate_search_session_execution_task.delay(
                                str(self.session.id)
                            )

                            # Log the execution start
                            SessionActivity.log_activity(
                                session=self.session,
                                activity_type="search_started",
                                description="Search execution initiated",
                                user=request.user,
                                metadata={"task_id": task.id},
                            )

                            messages.success(
                                request,
                                "Search execution has been initiated. You'll be notified when it's complete.",
                            )

                            # Redirect directly to execution status/progress page
                            print(
                                f"Redirecting to serp_execution:execution_status with session_id={self.session.id}"
                            )
                            return redirect(
                                "serp_execution:execution_status",
                                session_id=self.session.id,
                            )

                        except Exception as e:
                            logger.error(
                                f"Failed to initiate search execution: {str(e)}"
                            )
                            messages.error(
                                request, f"Failed to start search execution: {str(e)}"
                            )
                            return redirect(
                                "search_strategy:strategy_form",
                                session_id=self.session.id,
                            )
                    else:
                        messages.error(
                            request,
                            f"Cannot execute search from status '{self.session.get_status_display()}'",
                        )
                        return redirect(
                            "search_strategy:strategy_form", session_id=self.session.id
                        )
                elif "save_and_continue" in request.POST:
                    return redirect(
                        "serp_execution:execute_search", session_id=self.session.id
                    )
                else:
                    # Just save - stay on strategy form
                    return redirect(
                        "search_strategy:strategy_form", session_id=self.session.id
                    )

        # Form is invalid - return with errors
        messages.error(request, "Please correct the errors below.")

        # Re-render form with errors
        context = self.get_context_data()
        context["form"] = form
        return self.render_to_response(context)

    def _update_search_queries(self, strategy: SearchStrategy) -> None:
        """Update SearchQuery objects based on strategy."""
        logger.info(f"Updating search queries for strategy {strategy.id}")

        # Delete existing queries
        deleted_count = strategy.search_queries.all().delete()[0]
        logger.info(f"Deleted {deleted_count} existing queries")

        # Generate new queries
        queries_data = strategy.generate_queries()
        logger.info(f"Generated {len(queries_data)} new queries")

        # Log the strategy data
        logger.info(
            f"Strategy data - Population: {strategy.population_terms}, Interest: {strategy.interest_terms}, Context: {strategy.context_terms}"
        )
        logger.info(f"Search config: {strategy.search_config}")

        # Create SearchQuery objects
        created_count = 0
        for i, query_data in enumerate(queries_data):
            logger.info(f"Creating query {i+1}: {query_data}")
            SearchQuery.objects.create(
                strategy=strategy,
                query_text=query_data["query"],
                query_type=query_data["type"],
                target_domain=query_data.get("domain"),
                execution_order=i + 1,
            )
            created_count += 1

        logger.info(f"Created {created_count} SearchQuery objects")

        # Verify queries were created
        final_count = strategy.search_queries.count()
        logger.info(f"Final query count for strategy: {final_count}")


@login_required
@require_http_methods(["POST"])
def update_strategy_ajax(request, session_id: str) -> JsonResponse:
    """
    AJAX endpoint for real-time strategy updates and query preview.
    Returns updated query preview and validation status.
    """
    try:
        # Get session and validate ownership
        session = get_object_or_404(SearchSession, id=session_id)
        if session.owner != request.user:
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Get or create strategy
        strategy, created = SearchStrategy.objects.get_or_create(
            session=session, defaults={"user": request.user}
        )

        # Parse form data
        data = json.loads(request.body)

        # Update strategy fields temporarily (don't save yet)
        strategy.population_terms = data.get("population_terms", [])
        strategy.interest_terms = data.get("interest_terms", [])
        strategy.context_terms = data.get("context_terms", [])
        strategy.search_config = data.get("search_config", {})

        # Validate and generate queries
        is_complete = strategy.validate_completeness()
        queries = strategy.generate_queries()
        stats = strategy.get_stats()

        # Format queries for preview
        formatted_queries = []
        for i, query_data in enumerate(queries):
            formatted_queries.append(
                {
                    "id": i + 1,
                    "query": query_data["query"],
                    "type": query_data["type"],
                    "domain": query_data.get("domain", "General Search"),
                    "estimated_results": 100,  # Placeholder
                }
            )

        return JsonResponse(
            {
                "success": True,
                "is_complete": is_complete,
                "validation_errors": strategy.validation_errors,
                "queries": formatted_queries,
                "stats": stats,
                "base_query": strategy.generate_base_query(),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def strategy_status_api(request, session_id: str) -> JsonResponse:
    """
    API endpoint to get current strategy status and statistics.
    """
    try:
        # Get session and validate ownership
        session = get_object_or_404(SearchSession, id=session_id)
        if session.owner != request.user:
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Get strategy if exists
        try:
            strategy = SearchStrategy.objects.get(session=session)
            stats = strategy.get_stats()
            queries = strategy.generate_queries()

            response_data = {
                "exists": True,
                "is_complete": strategy.is_complete,
                "validation_errors": strategy.validation_errors,
                "stats": stats,
                "query_count": len(queries),
                "updated_at": strategy.updated_at.isoformat(),
            }
        except SearchStrategy.DoesNotExist:
            response_data = {
                "exists": False,
                "is_complete": False,
                "validation_errors": {},
                "stats": {
                    "population_count": 0,
                    "interest_count": 0,
                    "context_count": 0,
                    "total_terms": 0,
                    "domain_count": 0,
                    "query_count": 0,
                    "is_complete": False,
                },
                "query_count": 0,
                "updated_at": None,
            }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
