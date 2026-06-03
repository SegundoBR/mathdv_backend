from __future__ import annotations
import logging
import numpy as np
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from .services import generate_exam_recommendations
from .algorithms.recomendation import DiagnosticFeatureExtractor, ActivityFeatureExtractor
from .models import Exam, UserExamAttempt

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


logger = logging.getLogger('django')


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
    

class RecommendedActivitiesView(APIView):
    permission_classes = [IsExamAuthenticated]

    def get(self, request):
        user = request.user
        
        logger.info(f"============ INICIO DE PROCESAMIENTO LINUCB ============")
        logger.info(f"Usuario evaluado: {user.email} (ID: {user.id})")
        
        # 1. Extraer vector de contexto del alumno
        user_features = DiagnosticFeatureExtractor.get_user_diagnostic_features(user)
        
        # Formatear el vector para que sea fácil de leer en los logs de Render
        user_vector_str = [f"{val:.2f}" for val in user_features]
        logger.info(f"--> [CONTEXTO ESTUDIANTE] Vector x_t (d=5): {user_vector_str}")
        logger.info(f"    [Detalle] Global: {user_vector_str[0]} | Ratio Debiles: {user_vector_str[1]} | Cognitivo: {user_vector_str[2]} | Procedimental: {user_vector_str[3]} | Patron Dificultad: {user_vector_str[4]}")
        
        # Verificar si tiene el diagnóstico completo
        diagnostic_exists = UserExamAttempt.objects.filter(
            user=user,
            attempt_type=UserExamAttempt.AttemptType.DIAGNOSTIC,
            is_completed=True
        ).exists()
        
        if not diagnostic_exists:
            logger.warning(f"⚠️ El usuario {user.email} no cuenta con un examen diagnóstico completado. Retornando lista vacía.")
            logger.info(f"============ FIN DE PROCESAMIENTO LINUCB ============")
            return Response({"exams": []})
            
        # 2. Obtener exámenes candidatos
        candidate_exams = Exam.objects.filter(is_active=True).select_related('topic')
        logger.info(f"Total de actividades candidatas encontradas en Supabase: {candidate_exams.count()}")
        
        data = []
        alpha = 0.2  # Hiperparámetro de exploración
        
        logger.info(f"--- Evaluación de Límite Superior de Confianza (UCB) ---")
        
        for exam in candidate_exams:
            # 3. Extraer características de la actividad
            activity_features = ActivityFeatureExtractor.get_activity_features(exam)
            act_vector_str = [f"{val:.2f}" for val in activity_features]
            
            # 4. Cálculos matemáticos del LinUCB
            estimated_reward = float(np.dot(user_features, activity_features))
            uncertainty = float(alpha * np.sqrt(np.sum(np.square(activity_features))))
            linucb_score = estimated_reward + uncertainty
            
            # Formatear datos para la respuesta del celular
            confidence = round(float(np.clip(linucb_score / 2.0, 0.50, 0.99)), 2)
            score_basis = round((1.0 - estimated_reward) * 100, 1)
            
            # Imprimir en el log el desglose de la decisión por cada examen
            logger.info(
                f"Actividad: '{exam.title}' | Tema: {exam.topic.name if exam.topic else 'Ninguno'} \n"
                f"    -> Vector Actividad: {act_vector_str} (Dif: {act_vector_str[0]}, Cogn: {act_vector_str[1]}, Proc: {act_vector_str[2]}) \n"
                f"    -> [LinUCB Matemático] Explotación (Predicción): {estimated_reward:.4f} + Exploración (Incertidumbre): {uncertainty:.4f} = Score Total: {linucb_score:.4f} (Confianza guardada: {confidence})"
            )
            
            data.append({
                "id": exam.id,
                "title": exam.title,
                "description": exam.description,
                "difficulty": exam.difficulty,
                "topic_name": exam.topic.name if exam.topic else "",
                "confidence": confidence,
                "score_basis": score_basis,
                "reason": f"Prioridad adaptativa LinUCB para nivel {exam.difficulty} ({exam.competency_type})",
            })
            
        # 5. Ordenar las actividades tal y como lo exige el criterio del bandido contextual
        data_sorted = sorted(data, key=lambda r: (-r["confidence"], r["score_basis"]))
        
        logger.info(f"--- Ranking Final de Recomendaciones Asignadas ---")
        for rank, item in enumerate(data_sorted[:3], start=1):
            logger.info(f"   Top {rank}: {item['title']} (Score de Confianza: {item['confidence']})")
            
        logger.info(f"============ FIN DE PROCESAMIENTO LINUCB ============")
        
        return Response({"exams": data_sorted})