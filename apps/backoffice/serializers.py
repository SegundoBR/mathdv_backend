from django.contrib.auth import get_user_model
from rest_framework import serializers

from exam.models import Exam, Question, QuestionOption, Topic, UserExamAttempt
from exam.serializers import ExamAttemptDetailSerializer

User = get_user_model()


class DashboardSummarySerializer(serializers.Serializer):
    total_students = serializers.IntegerField()
    total_exams = serializers.IntegerField()
    active_exams = serializers.IntegerField()
    inactive_exams = serializers.IntegerField()
    total_attempts = serializers.IntegerField()


class DashboardStudentsByMonthItemSerializer(serializers.Serializer):
    month = serializers.CharField()
    total_students = serializers.IntegerField()


class DashboardDailyLoginsItemSerializer(serializers.Serializer):
    date = serializers.CharField()
    total_logins = serializers.IntegerField()


class TopicListSerializer(serializers.ModelSerializer):
    exams_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Topic
        fields = ["id", "name", "exams_count"]
        read_only_fields = ["id", "exams_count"]


class TopicWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = ["name"]


class ExamListSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source="topic.name", read_only=True)
    questions_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "description",
            "topic",
            "topic_name",
            "difficulty",
            "recommended_age_min",
            "recommended_age_max",
            "is_active",
            "is_diagnostic",
            "questions_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "questions_count",
            "topic_name",
        ]


class ExamWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = [
            "title",
            "description",
            "topic",
            "difficulty",
            "recommended_age_min",
            "recommended_age_max",
            "is_active",
            "is_diagnostic",
        ]


class QuestionOptionWriteSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=255)
    position = serializers.ChoiceField(choices=QuestionOption.Position.choices)
    is_correct = serializers.BooleanField(required=False, default=False)
    order = serializers.IntegerField(required=False, default=0)


class QuestionOptionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ["id", "label", "position", "is_correct", "order"]
        read_only_fields = fields


class QuestionListSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source="exam.title", read_only=True)
    options = QuestionOptionReadSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "exam",
            "exam_title",
            "title",
            "question_text",
            "spoken_instruction",
            "spoken_question",
            "spoken_feedback_correct",
            "spoken_feedback_incorrect",
            "order",
            "is_active",
            "options",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "exam_title", "options"]


class QuestionWriteSerializer(serializers.ModelSerializer):
    options = QuestionOptionWriteSerializer(many=True)

    class Meta:
        model = Question
        fields = [
            "exam",
            "title",
            "question_text",
            "spoken_instruction",
            "spoken_question",
            "spoken_feedback_correct",
            "spoken_feedback_incorrect",
            "order",
            "is_active",
            "options",
        ]

    def validate_options(self, value):
        positions = [item["position"] for item in value]
        if len(value) != 2 or set(positions) != {"LEFT", "RIGHT"}:
            raise serializers.ValidationError(
                "La pregunta debe tener exactamente 2 opciones: LEFT y RIGHT."
            )
        return value

    def create(self, validated_data):
        options = validated_data.pop("options")
        question = Question.objects.create(**validated_data)
        for option in options:
            QuestionOption.objects.create(question=question, **option)
        return question

    def update(self, instance, validated_data):
        options = validated_data.pop("options", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if options is not None:
            for option in options:
                QuestionOption.objects.update_or_create(
                    question=instance,
                    position=option["position"],
                    defaults={
                        "label": option["label"],
                        "is_correct": option.get("is_correct", False),
                        "order": option.get("order", 0),
                    },
                )

        return instance


class StudentListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    attempts_count = serializers.IntegerField(read_only=True)
    completed_attempts = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_active",
            "date_joined",
            "last_login",
            "attempts_count",
            "completed_attempts",
        ]


class StudentAttemptSerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(source="exam.title", read_only=True)

    class Meta:
        model = UserExamAttempt
        fields = [
            "id",
            "exam",
            "exam_title",
            "started_at",
            "completed_at",
            "score",
            "total_questions",
            "is_completed",
        ]


class StudentAttemptDetailSerializer(ExamAttemptDetailSerializer):
    pass


class StudentDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    stats = serializers.DictField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "photo_url",
            "is_active",
            "date_joined",
            "last_login",
            "stats",
        ]
