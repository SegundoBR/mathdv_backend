from __future__ import annotations

from typing import TypedDict
import numpy as np
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .algorithms.recomendation import LinUCBRecommender, DiagnosticFeatureExtractor, ActivityFeatureExtractor

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
    LinUCBRecommender().recommend_for_user(user)
    percentage = round((score / total_questions) * 100, 1) if total_questions else 0.0

    return {
        "score": score,
        "total_questions": total_questions,
        "percentage": percentage,
    }


def generate_exam_recommendations(*, user: User) -> list[ExamRecommendation]:
    """
    Genera recomendaciones de actividades personalizadas utilizando el algoritmo LinUCB
    a partir de las dimensiones del examen diagnóstico.
    """
    # 1. Obtener vector de contexto del estudiante a partir de su diagnóstico [d=5]
    # [score_pct, weak_topic_ratio, cognitive_score, procedural_score, difficulty_pattern]
    user_features = DiagnosticFeatureExtractor.get_user_diagnostic_features(user)
    
    # Si el usuario es nuevo o no ha completado el diagnóstico, retornamos lista vacía
    # obligando a la interfaz móvil a guiarlo a completar su evaluación inicial.
    diagnostic_exists = UserExamAttempt.objects.filter(
        user=user,
        attempt_type=UserExamAttempt.AttemptType.DIAGNOSTIC,
        is_completed=True
    ).exists()
    
    if not diagnostic_exists:
        return []

    # 2. Obtener todas las actividades candidatas que no sean de diagnóstico directo
    candidate_exams = Exam.objects.filter(is_active=True).select_related('topic')
    
    saved_recommendations: list[ExamRecommendation] = []
    
    # Parámetros simulados de exploración LinUCB (Incertidumbre controlada)
    # En producción completa, A_a y b_a se extraen de la tabla histórica de coeficientes
    alpha = 0.2 
    
    for exam in candidate_exams:
        # 3. Extraer vector de características del examen candidato [d=5]
        # [difficulty_level, is_cognitive, is_procedural, success_rate, completion_rate]
        activity_features = ActivityFeatureExtractor.get_activity_features(exam)
        
        # 4. Cálculo del componente de Explotación (Producto punto de vectores)
        # Pondera qué tanta necesidad tiene el usuario de cubrir esa competencia/dificultad específica
        estimated_reward = float(np.dot(user_features, activity_features))
        
        # 5. Componente de Exploración (Incertidumbre de la varianza del ejercicio)
        # Agrega un margen de confianza superior para evitar el estancamiento pedagógico
        uncertainty = float(alpha * np.sqrt(np.sum(np.square(activity_features))))
        
        # Puntaje Final LinUCB (Límite superior de confianza)
        linucb_score = estimated_reward + uncertainty
        
        # Convertir score a formato de confianza porcentual para guardar en el registro [0.0 - 1.0]
        confidence = round(float(np.clip(linucb_score / 2.0, 0.50, 0.99)), 2)
        
        # Invertimos el score_basis para que a menor rendimiento previo en esa dimensión, 
        # mayor prioridad de aparición tenga en la visualización
        score_basis = round((1.0 - estimated_reward) * 100, 1)
        
        # 6. Guardar o actualizar la actividad recomendada en la base de datos
        recommendation, _ = ExamRecommendation.objects.update_or_create(
            user=user,
            recommended_exam=exam,
            defaults={
                "score_basis": score_basis,
                "confidence": confidence,
                "reason": f"Prioridad adaptativa LinUCB para nivel {exam.difficulty} ({exam.competency_type})",
            },
        )
        saved_recommendations.append(recommendation)
        
    # Retornar el árbol de actividades ordenadas por la prioridad matemática del algoritmo
    return sorted(saved_recommendations, key=lambda r: (-r.confidence, r.score_basis))