from django.urls import path

from . import views

app_name = "review_manager"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    # Session CRUD
    path("sessions/create/", views.SessionCreateView.as_view(), name="create_session"),
    path(
        "sessions/<uuid:session_id>/",
        views.SessionDetailView.as_view(),
        name="session_detail",
    ),
    path(
        "sessions/<uuid:session_id>/edit/",
        views.SessionUpdateView.as_view(),
        name="edit_session",
    ),
    path(
        "sessions/<uuid:session_id>/delete/",
        views.SessionDeleteView.as_view(),
        name="delete_session",
    ),
    # Session Actions
    path(
        "sessions/<uuid:session_id>/duplicate/",
        views.DuplicateSessionView.as_view(),
        name="duplicate_session",
    ),
    path(
        "sessions/<uuid:session_id>/archive/",
        views.ArchiveSessionView.as_view(),
        name="archive_session",
    ),
    path(
        "sessions/<uuid:session_id>/navigate/",
        views.SessionNavigateView.as_view(),
        name="session_navigate",
    ),
]
