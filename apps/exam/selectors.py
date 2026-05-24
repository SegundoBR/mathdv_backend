from __future__ import annotations

import random

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, F, FloatField, Prefetch, QuerySet, Q
from django.db.models.functions import Cast

from .models import (
    Exam,
    ExamRecommendation,
    Question,
    QuestionOption,
    Topic,
    UserAnswer,
    UserExamAttempt,
)

User = get_user_model()


def get_questions(*, active_only: bool = True) -> QuerySet[Question]:
    queryset = (
        Question.objects.prefetch_related(
            Prefetch(
                "options",
                queryset=QuestionOption.objects.order_by("order", "created_at"),
            )
        )
        .select_related("exam", "exam__topic")
        .order_by("order", "created_at")
    )

    if active_only:
        queryset = queryset.filter(
            is_active=True,
            exam__is_active=True,
        )

    return queryset


def get_topics() -> QuerySet[Topic]:
    return Topic.objects.order_by("name")


def get_exams(*, active_only: bool = True) -> QuerySet[Exam]:
    queryset = Exam.objects.select_related("topic").order_by("topic__name", "title")
    if active_only:
        queryset = queryset.filter(is_active=True)
    return queryset


def get_exam_questions(*, exam_id) -> QuerySet[Question]:
    return get_questions(active_only=True).filter(exam_id=exam_id)


def get_diagnostic_questions(*, limit: int = 20) -> list[Question]:
    """Return randomized active questions from the exam with most active questions."""
    # Get the exam with the most active questions
    exam = (
        Exam.objects.filter(is_active=True)
        .annotate(
            active_questions_count=Count(
                "questions", filter=Q(questions__is_active=True)
            )
        )
        .filter(active_questions_count__gt=0)
        .order_by("-active_questions_count")
        .first()
    )

    if not exam:
        return []

    # Get questions from this exam, randomized
    questions = list(
        Question.objects.filter(
            exam=exam,
            is_active=True,
        )
    )

    random.shuffle(questions)
    return questions[:limit]


def get_user_attempt(
    *, user: User, exam: Exam | None = None, is_completed: bool | None = None
) -> UserExamAttempt | None:
    queryset = UserExamAttempt.objects.filter(user=user).order_by("-started_at")
    if exam is not None:
        queryset = queryset.filter(exam=exam)
    if is_completed is not None:
        queryset = queryset.filter(is_completed=is_completed)
    return queryset.first()


def get_user_scores_by_topic(*, user: User) -> list[dict]:
    score_expr = (
        Cast(F("score"), FloatField())
        * 100.0
        / Cast(F("total_questions"), FloatField())
    )

    rows = (
        UserExamAttempt.objects.filter(
            user=user,
            is_completed=True,
            total_questions__gt=0,
            exam__isnull=False,
            exam__topic__isnull=False,
        )
        .values("exam__topic_id", "exam__topic__name")
        .annotate(avg_percentage=Avg(score_expr), attempts=Count("id"))
        .order_by("avg_percentage")
    )

    result: list[dict] = []
    for row in rows:
        result.append(
            {
                "topic_id": row["exam__topic_id"],
                "topic_name": row["exam__topic__name"],
                "avg_percentage": float(row["avg_percentage"] or 0),
            }
        )
    return result


def get_recommended_exams(*, user: User) -> QuerySet[ExamRecommendation]:
    return (
        ExamRecommendation.objects.filter(user=user)
        .select_related("recommended_exam", "recommended_exam__topic")
        .order_by("-confidence", "created_at")
    )


def get_user_exam_history(*, user: User) -> QuerySet[UserExamAttempt]:
    return (
        UserExamAttempt.objects.filter(user=user)
        .select_related("exam")
        .order_by("-started_at")
    )


def get_user_exam_attempt_detail(*, user: User, attempt_id) -> UserExamAttempt | None:
    return (
        UserExamAttempt.objects.filter(user=user, id=attempt_id)
        .select_related("exam", "exam__topic")
        .prefetch_related(
            Prefetch(
                "answers",
                queryset=UserAnswer.objects.select_related(
                    "question", "selected_option"
                )
                .prefetch_related("question__options")
                .order_by("answered_at"),
            )
        )
        .first()
    )
