from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from account.permissions import IsAuthenticatedAndTeacher
from core.paginator.custom_paginator import CustomPaginator
from exam.models import Exam, Question, Topic, UserExamAttempt

from .selectors import (
    filter_exams,
    get_daily_logins_items,
    get_dashboard_summary,
    get_student_stats,
    get_students_by_month_items,
    get_students_list_queryset,
    get_topics_queryset,
)
from .serializers import (
    DashboardDailyLoginsItemSerializer,
    DashboardStudentsByMonthItemSerializer,
    DashboardSummarySerializer,
    ExamListSerializer,
    ExamWriteSerializer,
    QuestionListSerializer,
    QuestionWriteSerializer,
    StudentDetailSerializer,
    StudentListSerializer,
    StudentAttemptDetailSerializer,
    TopicListSerializer,
    TopicWriteSerializer,
)
from .services import create_exam, update_exam, update_exam_status

User = get_user_model()


def _parse_bool(value):
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request) -> Response:
        serializer = DashboardSummarySerializer(get_dashboard_summary())
        return Response(serializer.data, status=status.HTTP_200_OK)


class DashboardStudentsByMonthView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request) -> Response:
        items = get_students_by_month_items()
        serializer = DashboardStudentsByMonthItemSerializer(items, many=True)
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)


class DashboardDailyLoginsView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request) -> Response:
        items = get_daily_logins_items()
        serializer = DashboardDailyLoginsItemSerializer(items, many=True)
        return Response({"items": serializer.data}, status=status.HTTP_200_OK)


class BackofficeExamListCreateView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request) -> Response:
        queryset = filter_exams(
            search=request.query_params.get("search"),
            topic_id=request.query_params.get("topic_id"),
            difficulty=request.query_params.get("difficulty"),
            is_active=_parse_bool(request.query_params.get("is_active")),
            is_diagnostic=_parse_bool(request.query_params.get("is_diagnostic")),
        )

        paginator = CustomPaginator()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ExamListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request: Request) -> Response:
        serializer = ExamWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam = create_exam(validated_data=serializer.validated_data)
        return Response(ExamListSerializer(exam).data, status=status.HTTP_201_CREATED)


class BackofficeExamDetailView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request, exam_id) -> Response:
        exam = get_object_or_404(
            Exam.objects.select_related("topic").annotate(
                questions_count=Count("questions")
            ),
            pk=exam_id,
        )
        return Response(ExamListSerializer(exam).data, status=status.HTTP_200_OK)

    def put(self, request: Request, exam_id) -> Response:
        exam = get_object_or_404(Exam, pk=exam_id)
        serializer = ExamWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam = update_exam(exam=exam, validated_data=serializer.validated_data)
        exam = (
            Exam.objects.select_related("topic")
            .annotate(questions_count=Count("questions"))
            .get(pk=exam.pk)
        )
        return Response(ExamListSerializer(exam).data, status=status.HTTP_200_OK)

    def patch(self, request: Request, exam_id) -> Response:
        exam = get_object_or_404(Exam, pk=exam_id)
        serializer = ExamWriteSerializer(exam, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        exam = update_exam(exam=exam, validated_data=serializer.validated_data)
        exam = (
            Exam.objects.select_related("topic")
            .annotate(questions_count=Count("questions"))
            .get(pk=exam.pk)
        )
        return Response(ExamListSerializer(exam).data, status=status.HTTP_200_OK)


class BackofficeExamStatusView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def patch(self, request: Request, exam_id) -> Response:
        exam = get_object_or_404(Exam, pk=exam_id)
        is_active = _parse_bool(request.data.get("is_active"))
        if is_active is None:
            return Response(
                {"detail": "El campo 'is_active' es requerido y debe ser booleano."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        exam = update_exam_status(exam=exam, is_active=is_active)
        exam = (
            Exam.objects.select_related("topic")
            .annotate(questions_count=Count("questions"))
            .get(pk=exam.pk)
        )
        return Response(ExamListSerializer(exam).data, status=status.HTTP_200_OK)


class BackofficeExamQuestionListCreateView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request, exam_id) -> Response:
        exam = get_object_or_404(Exam, pk=exam_id)
        questions = (
            Question.objects.filter(exam=exam)
            .prefetch_related("options")
            .order_by("order", "created_at")
        )
        serializer = QuestionListSerializer(questions, many=True)
        return Response({"questions": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request: Request, exam_id) -> Response:
        payload = request.data.copy()
        payload["exam"] = str(exam_id)
        serializer = QuestionWriteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        question = Question.objects.prefetch_related("options", "exam").get(
            pk=question.pk
        )
        return Response(
            QuestionListSerializer(question).data, status=status.HTTP_201_CREATED
        )


class BackofficeQuestionDetailView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request, question_id) -> Response:
        question = get_object_or_404(
            Question.objects.select_related("exam").prefetch_related("options"),
            pk=question_id,
        )
        return Response(
            QuestionListSerializer(question).data, status=status.HTTP_200_OK
        )

    def put(self, request: Request, question_id) -> Response:
        question = get_object_or_404(Question, pk=question_id)
        payload = request.data.copy()
        payload["exam"] = str(question.exam_id)
        serializer = QuestionWriteSerializer(question, data=payload)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        question = Question.objects.prefetch_related("options", "exam").get(
            pk=question.pk
        )
        return Response(
            QuestionListSerializer(question).data, status=status.HTTP_200_OK
        )

    def patch(self, request: Request, question_id) -> Response:
        question = get_object_or_404(Question, pk=question_id)
        payload = request.data.copy()
        payload["exam"] = str(question.exam_id)
        serializer = QuestionWriteSerializer(question, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        question = serializer.save()
        question = Question.objects.prefetch_related("options", "exam").get(
            pk=question.pk
        )
        return Response(
            QuestionListSerializer(question).data, status=status.HTTP_200_OK
        )


class BackofficeTopicListCreateView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request) -> Response:
        topics = get_topics_queryset()
        serializer = TopicListSerializer(topics, many=True)
        return Response({"topics": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request: Request) -> Response:
        serializer = TopicWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()
        topic = Topic.objects.annotate(exams_count=Count("exams")).get(pk=topic.pk)
        return Response(TopicListSerializer(topic).data, status=status.HTTP_201_CREATED)


class BackofficeTopicDetailView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def put(self, request: Request, topic_id) -> Response:
        topic = get_object_or_404(Topic, pk=topic_id)
        serializer = TopicWriteSerializer(topic, data=request.data)
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()
        topic = Topic.objects.annotate(exams_count=Count("exams")).get(pk=topic.pk)
        return Response(TopicListSerializer(topic).data, status=status.HTTP_200_OK)

    def patch(self, request: Request, topic_id) -> Response:
        topic = get_object_or_404(Topic, pk=topic_id)
        serializer = TopicWriteSerializer(topic, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        topic = serializer.save()
        topic = Topic.objects.annotate(exams_count=Count("exams")).get(pk=topic.pk)
        return Response(TopicListSerializer(topic).data, status=status.HTTP_200_OK)


class BackofficeStudentListView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request) -> Response:
        date_joined_from_raw = request.query_params.get("date_joined_from")
        date_joined_to_raw = request.query_params.get("date_joined_to")

        try:
            date_joined_from = (
                date.fromisoformat(date_joined_from_raw)
                if date_joined_from_raw
                else None
            )
            date_joined_to = (
                date.fromisoformat(date_joined_to_raw) if date_joined_to_raw else None
            )
        except ValueError:
            return Response(
                {"detail": "Las fechas deben tener formato YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = get_students_list_queryset(
            search=request.query_params.get("search"),
            is_active=_parse_bool(request.query_params.get("is_active")),
            date_joined_from=date_joined_from,
            date_joined_to=date_joined_to,
        ).annotate(
            attempts_count=Count("exam_attempts"),
            completed_attempts=Count(
                "exam_attempts", filter=Q(exam_attempts__is_completed=True)
            ),
        )

        paginator = CustomPaginator()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = StudentListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class BackofficeStudentDetailView(APIView):
    permission_classes = [IsAuthenticatedAndTeacher]

    def get(self, request: Request, student_id) -> Response:
        student = get_object_or_404(
            User.objects.filter(role=User.Role.STUDENT), pk=student_id
        )
        attempts = (
            student.exam_attempts.select_related("exam", "exam__topic")
            .prefetch_related(
                "answers__question__options",
                "answers__selected_option",
            )
            .order_by("-started_at")
        )
        stats = get_student_stats(student=student)

        paginator = CustomPaginator()
        page = paginator.paginate_queryset(attempts, request, view=self)

        serializer = StudentDetailSerializer(student)
        payload = serializer.data
        payload["stats"] = stats
        attempts_page = paginator.get_paginated_response(
            StudentAttemptDetailSerializer(page, many=True).data
        )
        attempts_page.data["student"] = payload
        return attempts_page
