# Generated manually for adaptive exam refactor

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def assign_default_exam(apps, schema_editor):
    Topic = apps.get_model("exam", "Topic")
    Exam = apps.get_model("exam", "Exam")
    Question = apps.get_model("exam", "Question")
    UserExamAttempt = apps.get_model("exam", "UserExamAttempt")

    topic, _ = Topic.objects.get_or_create(name="General")
    exam, _ = Exam.objects.get_or_create(
        topic=topic,
        title="Diagnóstico General",
        defaults={
            "description": "Examen base creado por migración para compatibilidad.",
            "difficulty": "EASY",
            "is_diagnostic": True,
            "is_active": True,
        },
    )

    Question.objects.filter(exam__isnull=True).update(exam=exam)

    for attempt in UserExamAttempt.objects.filter(exam__isnull=True):
        first_answer = attempt.answers.select_related("question__exam").first()
        if first_answer and first_answer.question and first_answer.question.exam_id:
            attempt.exam_id = first_answer.question.exam_id
        else:
            attempt.exam = exam
        attempt.save(update_fields=["exam"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("exam", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Topic",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=150, unique=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Exam",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "difficulty",
                    models.CharField(
                        choices=[
                            ("EASY", "Fácil"),
                            ("MEDIUM", "Media"),
                            ("HARD", "Difícil"),
                        ],
                        default="EASY",
                        max_length=16,
                    ),
                ),
                (
                    "recommended_age_min",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                (
                    "recommended_age_max",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                ("is_diagnostic", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "topic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exams",
                        to="exam.topic",
                    ),
                ),
            ],
            options={"ordering": ["topic__name", "title"]},
        ),
        migrations.AddField(
            model_name="question",
            name="exam",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="questions",
                to="exam.exam",
            ),
        ),
        migrations.AddField(
            model_name="userexamattempt",
            name="exam",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attempts",
                to="exam.exam",
            ),
        ),
        migrations.CreateModel(
            name="ExamRecommendation",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("score_basis", models.FloatField(default=0)),
                ("confidence", models.FloatField(default=0)),
                ("reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "recommended_exam",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendations",
                        to="exam.exam",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="exam_recommendations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-confidence", "created_at"]},
        ),
        migrations.RunPython(assign_default_exam, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="question",
            name="exam",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="questions",
                to="exam.exam",
            ),
        ),
        migrations.AlterField(
            model_name="userexamattempt",
            name="exam",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="attempts",
                to="exam.exam",
            ),
        ),
        migrations.RemoveIndex(
            model_name="question",
            name="exam_questi_categor_70ddb2_idx",
        ),
        migrations.RemoveIndex(
            model_name="question",
            name="exam_questi_is_acti_13f0e4_idx",
        ),
        migrations.RemoveIndex(
            model_name="userexamattempt",
            name="exam_userex_user_id_495270_idx",
        ),
        migrations.RemoveField(model_name="question", name="category"),
        migrations.RemoveField(model_name="question", name="difficulty"),
        migrations.AddIndex(
            model_name="exam",
            index=models.Index(
                fields=["is_active", "is_diagnostic"],
                name="exam_exam_is_acti_80724e_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="exam",
            index=models.Index(
                fields=["topic", "is_active"],
                name="exam_exam_topic_i_b4b623_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="question",
            index=models.Index(
                fields=["exam", "is_active", "order"],
                name="exam_questi_exam_id_5194ea_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userexamattempt",
            index=models.Index(
                fields=["user", "exam", "is_completed", "started_at"],
                name="exam_userex_user_id_388eb5_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="examrecommendation",
            constraint=models.UniqueConstraint(
                fields=("user", "recommended_exam"),
                name="exam_unique_recommendation_per_user_exam",
            ),
        ),
        migrations.AddIndex(
            model_name="examrecommendation",
            index=models.Index(
                fields=["user", "confidence"],
                name="exam_examre_user_id_0d277a_idx",
            ),
        ),
    ]
