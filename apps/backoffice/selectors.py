from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth

from account.models import StudentLoginActivity
from exam.models import Exam, Topic, UserExamAttempt

User = get_user_model()


def get_students_queryset():
    return User.objects.filter(role=User.Role.STUDENT).select_related("profile")


def get_dashboard_summary() -> dict:
    total_students = get_students_queryset().count()
    total_exams = Exam.objects.count()
    active_exams = Exam.objects.filter(is_active=True).count()
    inactive_exams = total_exams - active_exams
    total_attempts = UserExamAttempt.objects.count()

    return {
        "total_students": total_students,
        "total_exams": total_exams,
        "active_exams": active_exams,
        "inactive_exams": inactive_exams,
        "total_attempts": total_attempts,
    }


def get_students_by_month_items() -> list[dict]:
    rows = (
        get_students_queryset()
        .annotate(month=TruncMonth("date_joined"))
        .values("month")
        .annotate(total_students=Count("id"))
        .order_by("month")
    )

    items = []
    for row in rows:
        month = row["month"]
        items.append(
            {
                "month": month.strftime("%Y-%m") if month else "",
                "total_students": row["total_students"],
            }
        )
    return items


def get_daily_logins_items() -> list[dict]:
    rows = (
        StudentLoginActivity.objects.annotate(day=TruncDate("logged_at"))
        .values("day")
        .annotate(total_logins=Count("id"))
        .order_by("day")
    )

    items = []
    for row in rows:
        day = row["day"]
        items.append(
            {
                "date": day.isoformat() if day else "",
                "total_logins": row["total_logins"],
            }
        )
    return items


def filter_exams(
    *, search=None, topic_id=None, difficulty=None, is_active=None, is_diagnostic=None
):
    queryset = Exam.objects.select_related("topic").prefetch_related("questions")

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    if topic_id:
        queryset = queryset.filter(topic_id=topic_id)
    if difficulty:
        queryset = queryset.filter(difficulty=difficulty)
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    if is_diagnostic is not None:
        queryset = queryset.filter(is_diagnostic=is_diagnostic)

    return queryset.annotate(questions_count=Count("questions")).order_by("-created_at")


def get_topics_queryset():
    return Topic.objects.annotate(exams_count=Count("exams")).order_by("name")


def get_students_list_queryset(
    *, search=None, is_active=None, date_joined_from=None, date_joined_to=None
):
    queryset = get_students_queryset().order_by("-date_joined")

    if search:
        queryset = queryset.filter(
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active)
    if date_joined_from:
        queryset = queryset.filter(date_joined__date__gte=date_joined_from)
    if date_joined_to:
        queryset = queryset.filter(date_joined__date__lte=date_joined_to)

    return queryset


def get_student_stats(*, student):
    attempts = UserExamAttempt.objects.filter(user=student)
    total_attempts = attempts.count()
    completed_attempts = attempts.filter(is_completed=True).count()

    # Use per-attempt percentage average with plain Python for SQLite compatibility.
    values = []
    for attempt in attempts.filter(total_questions__gt=0):
        values.append((attempt.score / attempt.total_questions) * 100)
    average_score = round(sum(values) / len(values), 1) if values else 0.0

    return {
        "total_attempts": total_attempts,
        "completed_attempts": completed_attempts,
        "average_score": average_score,
    }
