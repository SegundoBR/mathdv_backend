from django.urls import path

from .views import GoogleAuthView, TeacherLoginView, TeacherMeView, UserProfileView

app_name = "account"

urlpatterns = [
    path("auth/google/", GoogleAuthView.as_view(), name="google-auth"),
    path("auth/teacher/login/", TeacherLoginView.as_view(), name="teacher-login"),
    path("profile/", UserProfileView.as_view(), name="user-profile"),
    path("teacher/me/", TeacherMeView.as_view(), name="teacher-me"),
]
