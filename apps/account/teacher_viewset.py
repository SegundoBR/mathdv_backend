from rest_framework import viewsets

from apps.account.models import User
from apps.account.teacher_serializer import TeacherSerializer


class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherSerializer

    def get_queryset(self):
        return User.objects.filter(
            role=User.Role.TEACHER
        ).order_by("first_name")