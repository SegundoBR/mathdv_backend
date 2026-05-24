from django.urls import path

from .views import (
    BackofficeExamDetailView,
    BackofficeExamListCreateView,
    BackofficeExamStatusView,
    BackofficeStudentDetailView,
    BackofficeStudentListView,
    BackofficeTopicDetailView,
    BackofficeTopicListCreateView,
    DashboardDailyLoginsView,
    DashboardStudentsByMonthView,
    DashboardSummaryView,
    BackofficeExamQuestionListCreateView,
    BackofficeQuestionDetailView,
)

app_name = "backoffice"

urlpatterns = [
    path(
        "dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"
    ),
    path(
        "dashboard/students-by-month/",
        DashboardStudentsByMonthView.as_view(),
        name="dashboard-students-by-month",
    ),
    path(
        "dashboard/daily-logins/",
        DashboardDailyLoginsView.as_view(),
        name="dashboard-daily-logins",
    ),
    path("exams/", BackofficeExamListCreateView.as_view(), name="exam-list-create"),
    path(
        "exams/<uuid:exam_id>/", BackofficeExamDetailView.as_view(), name="exam-detail"
    ),
    path(
        "exams/<uuid:exam_id>/questions/",
        BackofficeExamQuestionListCreateView.as_view(),
        name="exam-question-list-create",
    ),
    path(
        "exams/<uuid:exam_id>/status/",
        BackofficeExamStatusView.as_view(),
        name="exam-status",
    ),
    path(
        "questions/<uuid:question_id>/",
        BackofficeQuestionDetailView.as_view(),
        name="question-detail",
    ),
    path("topics/", BackofficeTopicListCreateView.as_view(), name="topic-list-create"),
    path(
        "topics/<uuid:topic_id>/",
        BackofficeTopicDetailView.as_view(),
        name="topic-detail",
    ),
    path("students/", BackofficeStudentListView.as_view(), name="student-list"),
    path(
        "students/<uuid:student_id>/",
        BackofficeStudentDetailView.as_view(),
        name="student-detail",
    ),
]
