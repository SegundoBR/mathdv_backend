from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsExamAuthenticated
from .selectors import (
    get_exam_questions,
    get_exams,
    get_recommended_exams,
    get_topics,
    get_user_exam_attempt_detail,
    get_user_exam_history,
    get_user_attempt,
)
from .serializers import (
    BatchResultSerializer,
    ExamAttemptDetailSerializer,
    ExamHistorySerializer,
    ExamSerializer,
    ExamResultSerializer,
    QuestionSerializer,
    RecommendationSerializer,
    SubmitAnswerSerializer,
    SubmitBatchSerializer,
    TopicSerializer,
)
from .services import (
    generate_exam_recommendations,
    get_active_questions,
    submit_batch_answers,
    submit_user_answer,
)


class QuestionListView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request: Request) -> Response:
        # Diagnostic mixed question set (randomized, max 20).
        questions = get_active_questions()
        serializer = QuestionSerializer(questions, many=True)
        return Response({"questions": serializer.data}, status=status.HTTP_200_OK)


class TopicListView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request: Request) -> Response:
        topics = get_topics()
        serializer = TopicSerializer(topics, many=True)
        return Response({"topics": serializer.data}, status=status.HTTP_200_OK)


class ExamListView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request: Request) -> Response:
        exams = get_exams(active_only=True)
        serializer = ExamSerializer(exams, many=True)
        return Response({"exams": serializer.data}, status=status.HTTP_200_OK)


class ExamQuestionListView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request: Request, exam_id) -> Response:
        questions = get_exam_questions(exam_id=exam_id)
        serializer = QuestionSerializer(questions, many=True)
        return Response({"questions": serializer.data}, status=status.HTTP_200_OK)


class SubmitAnswerView(APIView):
    permission_classes = [IsExamAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SubmitAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = submit_user_answer(
            user=request.user,
            question_id=serializer.validated_data["question_id"],
            selected_option_id=serializer.validated_data["selected_option_id"],
            exam_id=serializer.validated_data.get("exam_id"),
        )
        return Response(result, status=status.HTTP_200_OK)


class ExamResultView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request: Request) -> Response:
        attempt = get_user_attempt(user=request.user, is_completed=False)
        if attempt is None:
            attempt = get_user_attempt(user=request.user, is_completed=True)

        if attempt is None or attempt.total_questions == 0:
            payload = {
                "score": 0,
                "total_questions": 0,
                "percentage": 0.0,
                "completed": False,
            }
        else:
            percentage = round((attempt.score / attempt.total_questions) * 100, 1)
            payload = {
                "score": attempt.score,
                "total_questions": attempt.total_questions,
                "percentage": percentage,
                "completed": attempt.is_completed,
            }

        serializer = ExamResultSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubmitBatchView(APIView):
    permission_classes = [IsExamAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SubmitBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = submit_batch_answers(
            user=request.user,
            exam_id=serializer.validated_data.get("exam_id"),
            answers=serializer.validated_data["answers"],
        )
        return Response(BatchResultSerializer(result).data, status=status.HTTP_200_OK)


class RecommendationListView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request: Request) -> Response:
        generate_exam_recommendations(user=request.user)
        recommendations = get_recommended_exams(user=request.user)
        serializer = RecommendationSerializer(recommendations, many=True)
        return Response(
            {"recommendations": serializer.data},
            status=status.HTTP_200_OK,
        )


class ExamHistoryAPIView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request: Request) -> Response:
        history = get_user_exam_history(user=request.user)
        serializer = ExamHistorySerializer(history, many=True)
        return Response({"history": serializer.data}, status=status.HTTP_200_OK)


class ExamAttemptDetailAPIView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request: Request, attempt_id) -> Response:
        attempt = get_user_exam_attempt_detail(user=request.user, attempt_id=attempt_id)
        if attempt is None:
            return Response(
                {"detail": "Intento no encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ExamAttemptDetailSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)
