from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Topic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Exam(models.Model):
    class Difficulty(models.TextChoices):
        EASY = "EASY", "Fácil"
        MEDIUM = "MEDIUM", "Media"
        HARD = "HARD", "Difícil"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="exams")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=16,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )
    grade_level = models.CharField(max_length=50, null=True, blank=True,
        default="")
    competency_type = models.CharField(max_length=50, null=True, blank=True,
        default="")
    recommended_age_min = models.PositiveSmallIntegerField(null=True, blank=True)
    recommended_age_max = models.PositiveSmallIntegerField(null=True, blank=True)
    is_diagnostic = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["topic__name", "title"]
        indexes = [
            models.Index(fields=["is_active", "is_diagnostic"]),
            models.Index(fields=["topic", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.topic.name})"


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    title = models.CharField(max_length=200)
    question_text = models.TextField()
    spoken_instruction = models.TextField()
    spoken_question = models.TextField()
    spoken_feedback_correct = models.TextField()
    spoken_feedback_incorrect = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "created_at"]
        indexes = [
            models.Index(fields=["exam", "is_active", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} - {self.exam.title}"


class QuestionOption(models.Model):
    class Position(models.TextChoices):
        LEFT = "LEFT", "Left"
        RIGHT = "RIGHT", "Right"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
    )
    label = models.CharField(max_length=255)
    position = models.CharField(max_length=16, choices=Position.choices)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"],
                name="exam_unique_option_position_per_question",
            )
        ]

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self) -> None:
        super().clean()
        if not self.question_id:
            return

        existing_count = QuestionOption.objects.filter(question_id=self.question_id)
        if self.pk:
            existing_count = existing_count.exclude(pk=self.pk)

        if existing_count.count() >= 2:
            raise ValidationError(
                "Cada pregunta solo puede tener 2 opciones (LEFT y RIGHT)."
            )

    def __str__(self) -> str:
        return f"{self.question.title}: {self.label}"


class UserExamAttempt(models.Model):
    class AttemptType(models.TextChoices):
        DIAGNOSTIC = "DIAGNOSTIC", "Diagnóstico"
        REINFORCEMENT = "REINFORCEMENT", "Reforzamiento"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_attempts",
    )
    attempt_type = models.CharField(
        max_length=20,
        choices=AttemptType.choices,
        default=AttemptType.DIAGNOSTIC,
    )
    title = models.CharField(max_length=255, default="Examen diagnóstico")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "exam", "is_completed", "started_at"]),
        ]

    def __str__(self) -> str:
        return f"Attempt {self.id} - {self.user} - {self.exam.title}"


class UserAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        UserExamAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="user_answers",
    )
    selected_option = models.ForeignKey(
        QuestionOption,
        on_delete=models.CASCADE,
        related_name="selected_in_answers",
    )
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["answered_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="exam_unique_answer_per_attempt_question",
            )
        ]

    def __str__(self) -> str:
        return f"{self.attempt.user} - {self.question.title}"


class ExamRecommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_recommendations",
    )
    recommended_exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    score_basis = models.FloatField(default=0)
    confidence = models.FloatField(default=0)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-confidence", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recommended_exam"],
                name="exam_unique_recommendation_per_user_exam",
            )
        ]
        indexes = [models.Index(fields=["user", "confidence"])]

    def __str__(self) -> str:
        return f"{self.user} -> {self.recommended_exam.title} ({self.confidence:.2f})"
