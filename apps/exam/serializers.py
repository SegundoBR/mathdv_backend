from __future__ import annotations

from rest_framework import serializers

from .models import (
    Exam,
    ExamRecommendation,
    Question,
    QuestionOption,
    Topic,
    UserAnswer,
    UserExamAttempt,
)


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["id", "name"]
        read_only_fields = fields


class ExamSerializer(serializers.ModelSerializer):
    topic = TopicSerializer(read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id",
            "topic",
            "title",
            "description",
            "difficulty",
            "recommended_age_min",
            "recommended_age_max",
            "is_diagnostic",
            "is_active",
        ]
        read_only_fields = fields


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "label", "position"]
        read_only_fields = ["id", "label", "position"]


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    exam_id = serializers.UUIDField(source="exam.id", read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "exam_id",
            "title",
            "question_text",
            "spoken_instruction",
            "spoken_question",
            "spoken_feedback_correct",
            "spoken_feedback_incorrect",
            "options",
        ]
        read_only_fields = fields


class SubmitAnswerSerializer(serializers.Serializer):
    question_id = serializers.UUIDField(required=True)
    selected_option_id = serializers.UUIDField(required=True)
    exam_id = serializers.UUIDField(required=False)


class AnswerItemSerializer(serializers.Serializer):
    question_id = serializers.UUIDField(required=True)
    selected_option_id = serializers.UUIDField(required=True)


class SubmitBatchSerializer(serializers.Serializer):
    exam_id = serializers.UUIDField(required=False)
    answers = AnswerItemSerializer(many=True, min_length=1)


class ExamResultSerializer(serializers.Serializer):
    score = serializers.IntegerField(read_only=True)
    total_questions = serializers.IntegerField(read_only=True)
    percentage = serializers.FloatField(read_only=True)
    completed = serializers.BooleanField(read_only=True)


class BatchResultSerializer(serializers.Serializer):
    score = serializers.IntegerField(read_only=True)
    total_questions = serializers.IntegerField(read_only=True)
    percentage = serializers.FloatField(read_only=True)


class RecommendationSerializer(serializers.ModelSerializer):
    exam_id = serializers.UUIDField(source="recommended_exam.id", read_only=True)
    title = serializers.CharField(source="recommended_exam.title", read_only=True)
    description = serializers.CharField(
        source="recommended_exam.description", read_only=True
    )
    topic = serializers.CharField(source="recommended_exam.topic.name", read_only=True)

    class Meta:
        model = ExamRecommendation
        fields = [
            "exam_id",
            "title",
            "description",
            "topic",
            "reason",
            "confidence",
        ]
        read_only_fields = fields


class ExamHistorySerializer(serializers.ModelSerializer):
    percentage = serializers.SerializerMethodField()
    completed = serializers.BooleanField(source="is_completed", read_only=True)

    class Meta:
        model = UserExamAttempt
        fields = [
            "id",
            "title",
            "attempt_type",
            "score",
            "total_questions",
            "percentage",
            "completed",
            "started_at",
            "completed_at",
        ]
        read_only_fields = fields

    def get_percentage(self, obj: UserExamAttempt) -> float:
        if obj.total_questions == 0:
            return 0.0
        return round((obj.score / obj.total_questions) * 100, 1)


class AttemptAnswerDetailSerializer(serializers.ModelSerializer):
    question_id = serializers.UUIDField(source="question.id", read_only=True)
    question_title = serializers.CharField(source="question.title", read_only=True)
    question_text = serializers.CharField(
        source="question.question_text", read_only=True
    )
    selected_option_id = serializers.UUIDField(
        source="selected_option.id", read_only=True
    )
    selected_option_label = serializers.CharField(
        source="selected_option.label", read_only=True
    )
    correct_option_id = serializers.SerializerMethodField()
    correct_option_label = serializers.SerializerMethodField()

    class Meta:
        model = UserAnswer
        fields = [
            "id",
            "question_id",
            "question_title",
            "question_text",
            "selected_option_id",
            "selected_option_label",
            "correct_option_id",
            "correct_option_label",
            "is_correct",
            "answered_at",
        ]
        read_only_fields = fields

    def get_correct_option_id(self, obj: UserAnswer):
        correct_option = next(
            (opt for opt in obj.question.options.all() if opt.is_correct), None
        )
        return str(correct_option.id) if correct_option is not None else None

    def get_correct_option_label(self, obj: UserAnswer):
        correct_option = next(
            (opt for opt in obj.question.options.all() if opt.is_correct), None
        )
        return correct_option.label if correct_option is not None else ""


class ExamAttemptDetailSerializer(serializers.ModelSerializer):
    exam_id = serializers.UUIDField(source="exam.id", read_only=True)
    exam_title = serializers.CharField(source="exam.title", read_only=True)
    topic_name = serializers.CharField(source="exam.topic.name", read_only=True)
    percentage = serializers.SerializerMethodField()
    completed = serializers.BooleanField(source="is_completed", read_only=True)
    answers = AttemptAnswerDetailSerializer(many=True, read_only=True)

    class Meta:
        model = UserExamAttempt
        fields = [
            "id",
            "exam_id",
            "exam_title",
            "topic_name",
            "title",
            "attempt_type",
            "score",
            "total_questions",
            "percentage",
            "completed",
            "started_at",
            "completed_at",
            "answers",
        ]
        read_only_fields = fields

    def get_percentage(self, obj: UserExamAttempt) -> float:
        if obj.total_questions == 0:
            return 0.0
        return round((obj.score / obj.total_questions) * 100, 1)
