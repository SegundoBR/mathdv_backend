# apps/exam/algorithms/feature_extractor.py
import numpy as np
from typing import Any
from django.contrib.auth import get_user_model
from django.db.models import Avg, Q, Count
from ..models import UserExamAttempt, UserAnswer, Exam, Topic

User = get_user_model()

class DiagnosticFeatureExtractor:
    """Extrae features del usuario desde su examen diagnóstico."""
    
    @staticmethod
    def get_user_diagnostic_features(user: Any) -> np.ndarray:
        """
        Retorna vector de features del usuario [d=5]:
        [score_pct, weak_topic_count, avg_weak_score, strong_topic_score, 
         difficulty_pattern]
        """
        # Obtener último intento diagnóstico completado
        diagnostic = UserExamAttempt.objects.filter(
            user=user,
            attempt_type=UserExamAttempt.AttemptType.DIAGNOSTIC,
            is_completed=True
        ).order_by('-completed_at').first()
        
        if not diagnostic:
            # Usuario nuevo: features por defecto (neutral)
            return np.array([0.5, 0.5, 0.5, 0.5, 0.5])
        
        # Feature 1: % de respuestas correctas
        score_pct = (diagnostic.score / diagnostic.total_questions) if diagnostic.total_questions > 0 else 0.5
        score_pct = min(1.0, score_pct)  # Normalizar [0, 1]
        
        # Features por tema
        topic_scores = DiagnosticFeatureExtractor._get_topic_scores(diagnostic)
        
        # Feature 2: Cantidad de temas débiles (< 70%)
        weak_topics = [t for t in topic_scores if t['score_pct'] < 0.7]
        weak_topic_count = min(1.0, len(weak_topics) / max(1, len(topic_scores)))
        
        # Feature 3: Promedio de temas débiles
        avg_weak_score = (
            np.mean([t['score_pct'] for t in weak_topics]) 
            if weak_topics else 0.7
        )
        
        # Feature 4: Mejor score en temas
        strong_topic_score = (
            max([t['score_pct'] for t in topic_scores]) 
            if topic_scores else 0.5
        )
        
        # Feature 5: Patrón de dificultad
        difficulty_pattern = DiagnosticFeatureExtractor._get_difficulty_pattern(diagnostic)
        
        features = np.array([
            score_pct,
            weak_topic_count,
            avg_weak_score,
            strong_topic_score,
            difficulty_pattern
        ], dtype=np.float32)
        
        # Normalizar al rango [0, 1]
        features = np.clip(features, 0, 1)
        return features
    
    @staticmethod
    def _get_topic_scores(diagnostic: UserExamAttempt) -> list[dict]:
        """Calcula score por tema en el diagnóstico."""
        answers = diagnostic.answers.select_related('question__exam__topic')
        
        topic_map = {}
        for answer in answers:
            topic_id = answer.question.exam.topic.id
            if topic_id not in topic_map:
                topic_map[topic_id] = {'correct': 0, 'total': 0}
            topic_map[topic_id]['total'] += 1
            if answer.is_correct:
                topic_map[topic_id]['correct'] += 1
        
        return [
            {'topic_id': tid, 'score_pct': data['correct'] / data['total']}
            for tid, data in topic_map.items()
        ]
    
    @staticmethod
    def _get_difficulty_pattern(diagnostic: UserExamAttempt) -> float:
        """
        Retorna patrón de dificultad:
        1.0 = mejor en preguntas difíciles
        0.5 = desempeño uniforme
        0.0 = mejor en preguntas fáciles
        """
        answers = diagnostic.answers.select_related('question__exam')
        
        by_difficulty = {}
        for answer in answers:
            diff = answer.question.exam.difficulty
            if diff not in by_difficulty:
                by_difficulty[diff] = {'correct': 0, 'total': 0}
            by_difficulty[diff]['total'] += 1
            if answer.is_correct:
                by_difficulty[diff]['correct'] += 1
        
        if not by_difficulty:
            return 0.5
        
        easy_pct = by_difficulty.get('EASY', {}).get('correct', 0) / max(1, by_difficulty.get('EASY', {}).get('total', 1))
        hard_pct = by_difficulty.get('HARD', {}).get('correct', 0) / max(1, by_difficulty.get('HARD', {}).get('total', 1))
        
        return min(1.0, max(0.0, hard_pct - easy_pct + 0.5))

class ActivityFeatureExtractor:
    """Extrae features de una actividad (Examen)."""
    
    @staticmethod
    def get_activity_features(exam: Exam) -> np.ndarray:
        """
        Retorna vector de features del examen [d=5]:
        [difficulty_level, topic_popularity, success_rate, completion_rate,
         is_diagnostic]
        """
        # Feature 1: Dificultad normalizada
        difficulty_map = {'EASY': 0.33, 'MEDIUM': 0.66, 'HARD': 1.0}
        difficulty = difficulty_map.get(exam.difficulty, 0.5)
        
        # Feature 2: Popularidad del tema (normalizad)
        topic_exam_count = Exam.objects.filter(
            topic=exam.topic,
            is_active=True
        ).count()
        topic_popularity = min(1.0, topic_exam_count / 10.0)  # Asumir max 10 exams/tema
        
        # Feature 3: Tasa de éxito histórica
        attempts = UserExamAttempt.objects.filter(exam=exam, is_completed=True)
        if attempts.exists():
            total_correct = UserAnswer.objects.filter(
                attempt__exam=exam,
                is_correct=True
            ).count()
            total_answers = UserAnswer.objects.filter(
                attempt__exam=exam
            ).count()
            success_rate = (total_correct / total_answers) if total_answers > 0 else 0.5
        else:
            success_rate = 0.5  # Desconocido: explorar
        
        # Feature 4: Tasa de completitud
        completion_rate = attempts.count() / max(1, UserExamAttempt.objects.count())
        completion_rate = min(1.0, completion_rate * 10)  # Scale
        
        # Feature 5: Es diagnóstico
        is_diagnostic = float(exam.is_diagnostic)
        
        features = np.array([
            difficulty,
            topic_popularity,
            success_rate,
            completion_rate,
            is_diagnostic
        ], dtype=np.float32)
        
        return np.clip(features, 0, 1)