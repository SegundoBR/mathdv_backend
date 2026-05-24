from django.contrib import admin

from .models import (
    Exam,
    ExamRecommendation,
    Question,
    QuestionOption,
    Topic,
    UserAnswer,
    UserExamAttempt,
)


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 2
    min_num = 2
    max_num = 2
    validate_min = True
    validate_max = True
    fields = ["label", "position", "is_correct", "order"]


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ["title", "order", "is_active"]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "topic",
        "difficulty",
        "is_diagnostic",
        "is_active",
        "created_at",
    ]
    list_filter = ["topic", "difficulty", "is_diagnostic", "is_active"]
    search_fields = ["title", "description", "topic__name"]
    ordering = ["topic__name", "title"]
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        "exam",
        "title",
        "order",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "exam", "exam__topic"]
    search_fields = ["title", "question_text", "spoken_question", "exam__title"]
    ordering = ["order", "created_at"]
    inlines = [QuestionOptionInline]


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ["question", "label", "position", "is_correct", "order"]
    list_filter = ["position", "is_correct"]
    search_fields = ["question__title", "label"]
    ordering = ["question__exam", "question__order", "order"]


@admin.register(UserExamAttempt)
class UserExamAttemptAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "attempt_type",
        "title",
        "exam",
        "score",
        "total_questions",
        "is_completed",
        "started_at",
        "completed_at",
    ]
    list_filter = ["is_completed", "started_at", "exam"]
    search_fields = ["user__email", "exam__title"]
    ordering = ["-started_at"]


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = [
        "attempt",
        "question",
        "selected_option",
        "is_correct",
        "answered_at",
    ]
    list_filter = ["is_correct", "answered_at"]
    search_fields = [
        "attempt__user__email",
        "question__title",
        "selected_option__label",
    ]
    ordering = ["-answered_at"]


@admin.register(ExamRecommendation)
class ExamRecommendationAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "recommended_exam",
        "score_basis",
        "confidence",
        "created_at",
    ]
    list_filter = ["recommended_exam__topic", "created_at"]
    search_fields = ["user__email", "recommended_exam__title", "reason"]
    ordering = ["-confidence", "-created_at"]
