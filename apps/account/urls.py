from django.urls import path

from .views import GoogleAuthView, TeacherLoginView, TeacherMeView, UserProfileView
from .teacher_viewset import TeacherViewSet

app_name = "account"

urlpatterns = [
    path("auth/google/", GoogleAuthView.as_view(), name="google-auth"),
    path("auth/teacher/login/", TeacherLoginView.as_view(), name="teacher-login"),
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("teacher/me/", TeacherMeView.as_view(), name="teacher-me"),
    path("teacher/me/", TeacherMeView.as_view(), name="teacher-me"),

    path(
        "teachers/",
        TeacherViewSet.as_view(
            {
                "get": "list",
                "post": "create",
            }
        ),
        name="teacher-list",
    ),

    path(
        "teachers/<uuid:pk>/",
        TeacherViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "delete": "destroy",
            }
        ),
        name="teacher-detail",
    ),
]
