from rest_framework import viewsets

from .models import User
from .teacher_serializer import TeacherSerializer


class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherSerializer

    def get_queryset(self):
        return User.objects.filter(
            role=User.Role.TEACHER
        ).order_by("first_name")