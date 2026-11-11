# apps/exam/algorithms/recommender.py

from .feature_extractor import (
    DiagnosticFeatureExtractor,
    ActivityFeatureExtractor,
)

from ..models import ExamRecommendation, Exam

class LinUCBRecommender:

    def recommend_for_user(self, user):

        user_features = (
            DiagnosticFeatureExtractor
            .get_user_diagnostic_features(user)
        )

        exams = Exam.objects.filter(
            is_active=True,
            is_diagnostic=False
        )

        recommendations = []

        for exam in exams:

            arm_features = (
                ActivityFeatureExtractor
                .get_activity_features(exam)
            )

            score = self.linucb_predict(
                user_features,
                arm_features
            )

            recommendations.append(
                (exam, score)
            )

        recommendations.sort(
            key=lambda x: x[1],
            reverse=True
        )

        top_exams = recommendations[:5]

        for exam, confidence in top_exams:

            ExamRecommendation.objects.update_or_create(
                user=user,
                recommended_exam=exam,
                defaults={
                    "confidence": confidence
                }
            )