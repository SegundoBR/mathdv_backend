from __future__ import annotations

from typing import TypedDict

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    Exam,
    ExamRecommendation,
    Question,
    QuestionOption,
    UserAnswer,
    UserExamAttempt,
)
from .selectors import (
    get_diagnostic_questions,
    get_user_attempt,
    get_user_scores_by_topic,
)

User = get_user_model()


class SubmitAnswerResult(TypedDict):
    is_correct: bool
    spoken_feedback: str
    current_score: int
    remaining_questions: int


def get_active_questions() -> list[Question]:
    return get_diagnostic_questions(limit=10)


def create_or_get_attempt(
    *,
    user: User,
    exam: Exam,
    attempt_type: str,
    title: str,
) -> UserExamAttempt:
    attempt = get_user_attempt(user=user, exam=exam, is_completed=False)
    if attempt is not None:
        changed_fields: list[str] = []
        if attempt.attempt_type != attempt_type:
            attempt.attempt_type = attempt_type
            changed_fields.append("attempt_type")
        if attempt.title != title:
            attempt.title = title
            changed_fields.append("title")
        if changed_fields:
            attempt.save(update_fields=changed_fields)
        return attempt

    total_questions = Question.objects.filter(exam=exam, is_active=True).count()
    return UserExamAttempt.objects.create(
        user=user,
        exam=exam,
        attempt_type=attempt_type,
        title=title,
        total_questions=total_questions,
    )


def calculate_score(*, attempt: UserExamAttempt) -> int:
    score = attempt.answers.filter(is_correct=True).count()
    if attempt.score != score:
        attempt.score = score
        attempt.save(update_fields=["score"])
    return score


@transaction.atomic
def submit_user_answer(
    *,
    user: User,
    question_id,
    selected_option_id,
    exam_id=None,
) -> SubmitAnswerResult:
    question = (
        Question.objects.select_related("exam", "exam__topic")
        .filter(
            id=question_id,
            is_active=True,
            exam__is_active=True,
        )
        .prefetch_related("options")
        .first()
    )
    if question is None:
        raise ValidationError({"question_id": "La pregunta no existe o está inactiva."})

    if question.exam is None:
        raise ValidationError(
            {"question_id": "La pregunta no está asociada a un examen."}
        )

    exam = question.exam
    is_reinforcement = exam_id is not None
    if exam_id is not None:
        requested_exam = Exam.objects.filter(id=exam_id, is_active=True).first()
        if requested_exam is None:
            raise ValidationError({"exam_id": "El examen no existe o está inactivo."})
        if requested_exam.id != question.exam_id:
            raise ValidationError(
                {"exam_id": "La pregunta no pertenece al examen indicado."}
            )
        exam = requested_exam

    selected_option = QuestionOption.objects.filter(id=selected_option_id).first()
    if selected_option is None:
        raise ValidationError(
            {"selected_option_id": "La opción seleccionada no existe."}
        )

    if selected_option.question_id != question.id:
        raise ValidationError(
            {
                "selected_option_id": "La opción seleccionada no pertenece a la pregunta indicada."
            }
        )

    attempt_type = (
        UserExamAttempt.AttemptType.REINFORCEMENT
        if is_reinforcement
        else UserExamAttempt.AttemptType.DIAGNOSTIC
    )
    title = f"Reforzamiento: {exam.title}" if is_reinforcement else "Examen diagnóstico"

    attempt = create_or_get_attempt(
        user=user,
        exam=exam,
        attempt_type=attempt_type,
        title=title,
    )

    if UserAnswer.objects.filter(attempt=attempt, question=question).exists():
        raise ValidationError(
            {"question_id": "Esta pregunta ya fue respondida en el intento actual."}
        )

    is_correct = selected_option.is_correct

    UserAnswer.objects.create(
        attempt=attempt,
        question=question,
        selected_option=selected_option,
        is_correct=is_correct,
    )

    current_score = calculate_score(attempt=attempt)
    answered_count = attempt.answers.count()
    remaining_questions = max(attempt.total_questions - answered_count, 0)

    if remaining_questions == 0 and not attempt.is_completed:
        attempt.is_completed = True
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=["is_completed", "completed_at"])

    spoken_feedback = (
        question.spoken_feedback_correct
        if is_correct
        else question.spoken_feedback_incorrect
    )

    return {
        "is_correct": is_correct,
        "spoken_feedback": spoken_feedback,
        "current_score": current_score,
        "remaining_questions": remaining_questions,
    }


class BatchResult(TypedDict):
    score: int
    total_questions: int
    percentage: float


@transaction.atomic
def submit_batch_answers(
    *,
    user: User,
    exam_id,
    answers: list[dict],
) -> BatchResult:
    if not answers:
        raise ValidationError({"answers": "Debe enviar al menos una respuesta."})

    requested_exam = None
    is_reinforcement = exam_id is not None
    if exam_id is not None:
        requested_exam = Exam.objects.filter(id=exam_id, is_active=True).first()
        if requested_exam is None:
            raise ValidationError({"exam_id": "El examen no existe o está inactivo."})

    # Pre-fetch referenced questions and options in two bulk queries.
    question_ids = [a["question_id"] for a in answers]
    option_ids = [a["selected_option_id"] for a in answers]

    questions_map = {
        q.id: q
        for q in Question.objects.select_related("exam").filter(
            id__in=question_ids,
            is_active=True,
            exam__is_active=True,
        )
    }
    options_map = {o.id: o for o in QuestionOption.objects.filter(id__in=option_ids)}

    resolved_exam = requested_exam
    if resolved_exam is None:
        for item in answers:
            question = questions_map.get(item["question_id"])
            if question is not None and question.exam is not None:
                resolved_exam = question.exam
                break

    if resolved_exam is None:
        raise ValidationError(
            {"exam_id": "No se pudo inferir el examen para las respuestas enviadas."}
        )

    # Keep compatibility but isolate attempt by exam.
    UserExamAttempt.objects.filter(
        user=user,
        exam=resolved_exam,
        is_completed=False,
    ).delete()

    total_questions = Question.objects.filter(
        exam=resolved_exam,
        is_active=True,
    ).count()

    attempt = UserExamAttempt.objects.create(
        user=user,
        exam=resolved_exam,
        attempt_type=(
            UserExamAttempt.AttemptType.REINFORCEMENT
            if is_reinforcement
            else UserExamAttempt.AttemptType.DIAGNOSTIC
        ),
        title=(
            f"Reforzamiento: {resolved_exam.title}"
            if is_reinforcement
            else "Examen diagnóstico"
        ),
        total_questions=total_questions,
    )

    to_create = []
    score = 0
    seen_questions = set()

    for item in answers:
        question = questions_map.get(item["question_id"])
        selected_option = options_map.get(item["selected_option_id"])

        if question is None:
            raise ValidationError(
                {"question_id": "Una pregunta no existe o está inactiva."}
            )
        if selected_option is None:
            raise ValidationError(
                {"selected_option_id": "Una opción seleccionada no existe."}
            )
        if question.exam_id != resolved_exam.id:
            raise ValidationError(
                {
                    "exam_id": "Todas las preguntas del lote deben pertenecer al mismo examen."
                }
            )
        if question.id in seen_questions:
            raise ValidationError(
                {"question_id": "Hay preguntas repetidas en el lote."}
            )
        seen_questions.add(question.id)
        if selected_option.question_id != question.id:
            raise ValidationError(
                {
                    "selected_option_id": "La opción seleccionada no pertenece a la pregunta indicada."
                }
            )

        is_correct = selected_option.is_correct
        if is_correct:
            score += 1

        to_create.append(
            UserAnswer(
                attempt=attempt,
                question=question,
                selected_option=selected_option,
                is_correct=is_correct,
            )
        )

    UserAnswer.objects.bulk_create(to_create, ignore_conflicts=True)

    attempt.score = score
    attempt.is_completed = True
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["score", "is_completed", "completed_at"])

    percentage = round((score / total_questions) * 100, 1) if total_questions else 0.0

    return {
        "score": score,
        "total_questions": total_questions,
        "percentage": percentage,
    }


def generate_exam_recommendations(*, user: User) -> list[ExamRecommendation]:
    """
    Build recommendations from completed attempts.
    Rule: topics with average percentage < 70 are considered weak.
    """
    topic_scores = get_user_scores_by_topic(user=user)
    weak_topics = [row for row in topic_scores if row["avg_percentage"] < 70]

    if not weak_topics:
        return []

    saved: list[ExamRecommendation] = []
    recommended_exam_ids: set = set()

    for row in sorted(weak_topics, key=lambda r: r["avg_percentage"]):
        avg = row["avg_percentage"]
        topic_id = row["topic_id"]
        confidence = round(min(0.99, max(0.50, (70.0 - avg) / 70.0 + 0.5)), 2)

        exams = Exam.objects.filter(
            topic_id=topic_id,
            is_active=True,
        ).order_by("is_diagnostic", "title")

        for exam in exams:
            if exam.id in recommended_exam_ids:
                continue

            recommendation, _ = ExamRecommendation.objects.update_or_create(
                user=user,
                recommended_exam=exam,
                defaults={
                    "score_basis": round(avg, 1),
                    "confidence": confidence,
                    "reason": "Bajo rendimiento detectado",
                },
            )
            recommended_exam_ids.add(exam.id)
            saved.append(recommendation)

    return sorted(saved, key=lambda r: (r.score_basis, -r.confidence))
