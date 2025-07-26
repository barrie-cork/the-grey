# Review Results Core Requirements

**Feature:** Review Results App
**Version:** 1.0
**Date:** 2025-05-31
**Dependencies:** Results Manager, Review Manager, Accounts
**Status:** Planned

## Overview

This document outlines the core functional and technical requirements for the Review Results feature. This app is responsible for providing researchers with an interface to manually review, tag, and annotate processed search results (`ProcessedResult` records) associated with a `SearchSession`. The goal is to facilitate a PRISMA-compliant review workflow, enabling transparent reporting of the study selection process.

The Review Results app allows users to systematically screen search results, assign relevance tags (`ReviewTag` via `ReviewTagAssignment`), and add contextual notes (`Note` model), ultimately determining which results are included or excluded from their systematic review.

## Core Requirements (Phase 1)

### Phase 1 Functional Requirements

**REQ-FR-RR-1: Display of Processed Results**
- System must display `ProcessedResult` records for a given `SearchSession` in a clear, scroll-paginated interface (e.g., loading 25 results at a time, with more loading as the user scrolls).
- This will be handled by a Django Class-Based View (CBV), likely `ResultsOverviewView(ListView)`, rendering a template like `review_results/results_overview.html`.
- Each result displayed must show key information: title, snippet, normalized URL, source search engine, and extracted metadata (file type, `ProcessedResult.quality_score`) from the `ProcessedResult` model.

**REQ-FR-RR-2: Results Tagging (Inclusion/Exclusion/Maybe)**
- Users must be able to assign a `ReviewTag` (e.g., "Include", "Exclude", "Maybe") to each `ProcessedResult`.
- Tagging will be managed through `ReviewTagAssignment` records, linking a `User`, `ProcessedResult`, `ReviewTag`, and the `SearchSession`. Tag changes by a user for a specific result in a session will update the existing `ReviewTagAssignment` record.
- The UI for each result item will feature dedicated buttons for "Include", "Exclude", and "Maybe" tags. Clicking a tag button will assign it to the result (likely via an AJAX call). Only one tag can be active per result; selecting a new tag updates the existing assignment. Buttons should visually reflect the currently selected tag (e.g., by changing color, using the `ReviewTag.color` attribute).
- Tagging a result as "Exclude" must require the user to provide a reason (stored in `ReviewTagAssignment.reason`). Clicking 'Exclude' will trigger a modal prompting the user for an exclusion reason (for Phase 1, a simple text field in the modal is sufficient; predefined reasons could be a future enhancement). Other tags ("Include", "Maybe") do not require a reason.
- The interface must clearly indicate the current tag status of each result, potentially using the `ReviewTag.color`.

**REQ-FR-RR-3: Note Taking**
- Users must be able to add textual `Note` records to individual `ProcessedResult` items.
- Each `Note` will be associated with a `User`, `ProcessedResult`, and `SearchSession`.
- A Django `Form` (`NoteForm`) will handle note creation and editing, potentially integrated into the results display via AJAX (e.g., a small icon to expand/collapse a note section or open a modal).
- Notes should be easily viewable alongside the result they pertain to.

**REQ-FR-RR-4: Results Filtering and Sorting in Overview**
- The `ResultsOverviewView` must support comprehensive filtering of `ProcessedResult` records.
- Filtering options (implemented via Django ORM queries) must include: by `ReviewTag` (including "Untagged" as a status), presence of `Note`, `ProcessedResult.file_type`, `ProcessedResult.quality_score`.
- Sorting options (implemented via Django ORM `order_by()`) must include: `ProcessedResult.processed_at` (date processed), title, `ProcessedResult.quality_score`, tag status.
- Django `Forms` will be used to capture filter and sort preferences from the user.
- Filter/sort state should ideally be maintained during pagination or navigation.

**REQ-FR-RR-5: Session Status Progression & Review Completion**
- The app must update the `SearchSession.status` based on review progress.
- When a user starts reviewing (e.g., assigns the first tag), the `SearchSession.status` might change from `ready_for_review` to `in_review`.
- A `SearchSession` is considered fully reviewed when all `ProcessedResult` items within that session have a `ReviewTagAssignment` from the reviewing user. Upon achieving this, the status should transition to `completed_fully_reviewed` (new status).
- Users must have an option to 'Conclude Review Early' even if not all items are tagged. If this option is chosen:
    - The `SearchSession.status` will transition to `review_concluded_incomplete` (new status).
    - The Reporting app must clearly differentiate between fully reviewed sessions and those concluded incompletely.
- Views handling tagging or a dedicated 'Conclude Review' action will be responsible for these status updates and checks.

**REQ-FR-RR-6: Display Duplicate Information**
- The `ResultsOverviewView` should visually indicate (e.g., with an icon) if a `ProcessedResult` is marked as `is_duplicate` by the Results Manager.
- If a result is indicated as a duplicate, clicking the icon (or a similar interactive element) must open a modal window listing the titles of its related duplicates (as identified by `DuplicateRelationship` records).

### Phase 1 Technical Requirements

**REQ-TR-RR-1: Django Views and Templates**
- Core functionality will be implemented using Django Class-Based Views (e.g., `ResultsOverviewView(ListView)`, views for AJAX tag/note operations) or function views.
- Django templates (`review_results/*.html`) will render the user interface, extending a base project template and maintaining UI consistency with other apps like Search Strategy.
- URL patterns will be defined in `apps/review_results/urls.py` and included in the project's main `urls.py`.

**REQ-TR-RR-2: Efficient ORM Usage**
- Django ORM queries for fetching and updating `ProcessedResult`, `ReviewTag`, `ReviewTagAssignment`, and `Note` data must be efficient.
- Utilize `select_related()` and `prefetch_related()` in views like `ResultsOverviewView` to minimize database queries and optimize performance, especially with scroll-based pagination.
- Database indexes on `ProcessedResult`, `ReviewTagAssignment`, and `Note` fields used for filtering and sorting will be crucial.

**REQ-TR-RR-3: Forms for Data Input**
- Django `Forms` or `ModelForms` will be used for:
    - Assigning tags and capturing exclusion reasons (`ReviewTagAssignmentForm`).
    - Creating/editing notes (`NoteForm`).
    - Capturing filter/sort criteria in the results overview.
- Forms must include appropriate validation (e.g., reason required for "Exclude" tag).

**REQ-TR-RR-4: AJAX for Enhanced UX**
- Tagging results and adding/editing notes should be handled via AJAX requests to provide a non-blocking, dynamic user experience.
- Django views will handle these AJAX requests, returning JSON responses to update the UI without full page reloads.

**REQ-TR-RR-5: Performance for Results Display**
- The `ResultsOverviewView` must load quickly and scroll smoothly, even with many `ProcessedResult` items in a session, through efficient scroll-based pagination and optimized ORM queries.
- AJAX-based tagging and note-adding operations should be responsive (e.g., complete within 1-2 seconds).

### Phase 1 User Interface Requirements

**REQ-UI-RR-1: Results Overview and Review Interface**
- A single, primary interface (e.g., `review_results/results_overview.html` rendered by `ResultsOverviewView`) for displaying scroll-paginated `ProcessedResult` items (e.g., 25 at a time).
- Each item must clearly display its content (title, snippet, URL), metadata (`ProcessedResult.quality_score`, file type), and source search engine.
- Interactive elements for each result:
    - Dedicated buttons for "Include", "Exclude", "Maybe" tags. Buttons change color or style to reflect the active tag. Only one tag active at a time.
    - Mechanism to add/view/edit notes (e.g., an icon opening a modal or an inline expandable area).
    - An icon indicating if the result `is_duplicate`, which on click opens a modal listing titles of related duplicates.
- Clear visual indication of each result's review status (untagged, or the color/style associated with its assigned `ReviewTag.color`).
- Filters and sorting controls should be readily accessible.
- Progress indicators (e.g., "X of Y results tagged") for the current `SearchSession` to help users track towards full review completion.

**REQ-UI-RR-2: Integration with Session Workflow**
- The interface should reflect the current `SearchSession.status` (e.g., `in_review`, `completed_fully_reviewed`, `review_concluded_incomplete`).
- Navigation should guide users from a `SearchSession` (e.g., on the Review Manager dashboard) to the `ResultsOverviewView` when the session is `ready_for_review`.
- Actions within the Review Results app (like tagging all results or choosing to 'Conclude Review Early') should update the `SearchSession.status` and potentially navigate the user or provide clear next steps.

## Data Model Requirements (Review Results App Focus)

The Review Results app will primarily define and manage the following Django models, while consuming others like `ProcessedResult` and `SearchSession`. All models will use UUID primary keys.

**ReviewTag Model (`apps/review_results/models.py`)**
```python
import uuid
from django.db import models

class ReviewTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True, help_text='e.g., "Include", "Exclude", "Maybe"')
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=50, unique=True, help_text="A short label for URLs and programmatic access.")
    color = models.CharField(max_length=7, blank=True, help_text="Hex color code (e.g., #FF0000) for UI indication.")

    def __str__(self):
        return self.name
```

**ReviewTagAssignment Model (`apps/review_results/models.py`)**
```python
import uuid
from django.db import models
from django.conf import settings

class ReviewTagAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    processed_result = models.ForeignKey('results_manager.ProcessedResult', on_delete=models.CASCADE, related_name='tag_assignments')
    tag = models.ForeignKey(ReviewTag, on_delete=models.PROTECT, related_name='assignments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="User who assigned the tag")
    session = models.ForeignKey('review_manager.SearchSession', on_delete=models.CASCADE, related_name='review_tag_assignments')
    reason = models.TextField(blank=True, null=True, help_text='Required if tag is "Exclude", otherwise optional.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('processed_result', 'session', 'user') # A user has one active tag assignment for a result per session
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.tag.name} for {self.processed_result_id} by {self.user_id} in session {self.session_id}"
```

**Note Model (`apps/review_results/models.py`)**
```python
import uuid
from django.db import models
from django.conf import settings

class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    processed_result = models.ForeignKey('results_manager.ProcessedResult', on_delete=models.CASCADE, related_name='notes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, help_text="User who wrote the note")
    session = models.ForeignKey('review_manager.SearchSession', on_delete=models.CASCADE, related_name='review_notes')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Note on {self.processed_result_id} by {self.user_id}"
```

**Consumed Models (Defined in other apps):**
- `results_manager.ProcessedResult`: The items being reviewed.
- `review_manager.SearchSession`: The context for the review.
- `accounts.User` (via `settings.AUTH_USER_MODEL`): The reviewer.

## Integration Requirements

**REQ-INT-RR-1: Results Manager Integration**
- Consumes `ProcessedResult` records that are ready for review for a specific `SearchSession`.
- Assumes `ProcessedResult` data (metadata including `quality_score`, normalized URL, `is_duplicate` status) is populated by the Results Manager app.

**REQ-INT-RR-2: Review Manager Integration**
- Updates `SearchSession.status` (e.g., to `in_review`, `completed_fully_reviewed`, `review_concluded_incomplete`) based on review actions and progress.
- The `ResultsOverviewView` is typically accessed via a `SearchSession` from the Review Manager dashboard when the session status is `ready_for_review`.

**REQ-INT-RR-3: Accounts Integration**
- Associates `ReviewTagAssignment` and `Note` records with the authenticated `User` performing the review.
- Views must be protected by `@login_required` and custom permission checks (e.g., `SessionOwnershipMixin`) to ensure the user has access to the `SearchSession`.

## Security Requirements

**REQ-SEC-RR-1: Ownership and Permissions**
- Users must only be able to review and tag results for `SearchSession` records they own (Phase 1). Future phases might introduce more granular team/collaborator permissions.
- Django views must enforce these permissions, typically by filtering querysets by `request.user` or checking `SearchSession.created_by`.
- Standard Django security measures (CSRF protection, XSS prevention via template auto-escaping) must be employed.

## Performance Requirements

**REQ-PERF-RR-1: Results Overview Page Load & Interaction**
- The `ResultsOverviewView` with scroll-based pagination should provide a responsive experience, loading initial results quickly (e.g., within 3 seconds for the first batch of 25-50) and subsequent batches smoothly on scroll.
- AJAX-based tagging and note-adding operations must complete within 1-2 seconds.

## Quality Assurance Requirements

**REQ-QA-RR-1: Testing**
- Unit tests (using Django's `TestCase`) for:
    - `ResultsOverviewView` logic (filtering, sorting, pagination, context data).
    - Views/logic handling AJAX tagging and note creation/updates.
    - Django `Forms` validation (e.g., `ReviewTagAssignmentForm` for exclusion reasons).
    - Model methods and properties (if any beyond standard Django).
- Integration tests for the complete review workflow for a `ProcessedResult` (tagging, noting, status updates).
- Aim for high test coverage (e.g., >90%) for the `review_results` app.

## Acceptance Criteria (Phase 1)

- [ ] User can view a scroll-paginated list of `ProcessedResult` items for a `SearchSession`, showing title, snippet, URL, quality score, and file type.
- [ ] Each result has dedicated "Include", "Exclude", "Maybe" buttons; clicking assigns the tag via AJAX and updates button appearance (e.g., using `ReviewTag.color`).
- [ ] User is prompted for a reason via a modal when selecting the "Exclude" tag; reason is saved.
- [ ] User can add, view, and edit `Note` items for each result via an AJAX-driven interface.
- [ ] The `ResultsOverviewView` supports filtering by `ReviewTag` (including "Untagged"), presence of `Note`, `file_type`, and `quality_score`.
- [ ] The `ResultsOverviewView` supports sorting by date processed, title, `quality_score`, and tag status.
- [ ] `SearchSession.status` is updated to `in_review` on first review action.
- [ ] `SearchSession.status` transitions to `completed_fully_reviewed` if all results are tagged.
- [ ] User can 'Conclude Review Early', transitioning `SearchSession.status` to `review_concluded_incomplete` if not all results are tagged.
- [ ] An icon indicates if a `ProcessedResult` `is_duplicate`; clicking it opens a modal listing titles of related duplicates.
- [ ] All views are protected by authentication and session ownership checks.
- [ ] Core Django models (`ReviewTag` with slug and color, `ReviewTagAssignment`, `Note`) are implemented in `apps/review_results/models.py`.
- [ ] Basic unit tests for views, forms, and models are in place.