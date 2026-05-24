from django.db import transaction

from exam.models import Exam


@transaction.atomic
def create_exam(*, validated_data):
    return Exam.objects.create(**validated_data)


@transaction.atomic
def update_exam(*, exam: Exam, validated_data):
    for field, value in validated_data.items():
        setattr(exam, field, value)
    exam.save(update_fields=list(validated_data.keys()) + ["updated_at"])
    return exam


@transaction.atomic
def update_exam_status(*, exam: Exam, is_active: bool):
    exam.is_active = is_active
    exam.save(update_fields=["is_active", "updated_at"])
    return exam
