from django.urls import path

from .views import (
    ExamAttemptDetailAPIView,
    ExamListView,
    ExamQuestionListView,
    ExamHistoryAPIView,
    ExamResultView,
    QuestionListView,
    RecommendationListView,
    SubmitAnswerView,
    SubmitBatchView,
    TopicListView,
    RecommendedActivitiesView,
)

app_name = "exam"

urlpatterns = [
    path("topics/", TopicListView.as_view(), name="topics"),
    path("list/", ExamListView.as_view(), name="exam-list"),
    path("questions/", QuestionListView.as_view(), name="questions"),
    path(
        "<uuid:exam_id>/questions/",
        ExamQuestionListView.as_view(),
        name="exam-questions",
    ),
    path("submit-answer/", SubmitAnswerView.as_view(), name="submit-answer"),
    path("submit-batch/", SubmitBatchView.as_view(), name="submit-batch"),
    path("recommendations/", RecommendationListView.as_view(), name="recommendations"),
    path("history/", ExamHistoryAPIView.as_view(), name="history"),
    path(
        "history/<uuid:attempt_id>/",
        ExamAttemptDetailAPIView.as_view(),
        name="history-detail",
    ),
    path("result/", ExamResultView.as_view(), name="result"),
    path("recommended-activities/", RecommendedActivitiesView.as_view(), name="recommended_activities"),
]
