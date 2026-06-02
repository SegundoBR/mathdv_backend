from __future__ import annotations

from collections.abc import Callable

from django.core.management.base import BaseCommand
from django.db import transaction

from exam.models import Exam, Question, QuestionOption, Topic

SPOKEN_INSTRUCTION = "Escucha la pregunta y desliza el dedo hacia la opción correcta. Lleve el dedo a la parte inferior del dispositivo y deslice a la opción correspondiente. Instrucción. Puede responder arrastrando a la izquierda o derecha, o diciendo izquierda o derecha."
SPOKEN_FEEDBACK_CORRECT = "Respuesta correcta. Excelente trabajo."
SPOKEN_FEEDBACK_INCORRECT = "Respuesta incorrecta. Intenta nuevamente."

QuestionPayload = tuple[str, str, str, bool]
QuestionGenerator = Callable[[], list[QuestionPayload]]

TOPIC_NAMES = [
    "Números racionales",
    "Números reales",
]

EXAM_BLUEPRINTS = {
    "Números racionales": [
        {
            "title": "Comparación de fracciones",
            "description": (
                "Identifica relaciones y comparaciones entre fracciones."
            ),
            "difficulty": Exam.Difficulty.EASY,
            #"grade_level": "2do secundaria",
            #"competency_type": "cognitiva",
            "generator": lambda: _fraction_comparison_questions(),
        },
        {
            "title": "Operaciones con fracciones",
            "description": (
                "Resuelve operaciones básicas con fracciones."
            ),
            "difficulty": Exam.Difficulty.MEDIUM,
            #"grade_level": "2do secundaria",
            #"competency_type": "procedimental",
            "generator": lambda: _fraction_operations_questions(),
        },
    ],

    "Números reales": [
        {
            "title": "Identificación de números reales",
            "description": (
                "Reconoce números racionales e irracionales."
            ),
            "difficulty": Exam.Difficulty.EASY,
            #"grade_level": "3ro secundaria",
            #"competency_type": "cognitiva",
            "generator": lambda: _real_number_identification_questions(),
        },
        {
            "title": "Operaciones con números reales",
            "description": (
                "Resuelve operaciones básicas con números reales."
            ),
            "difficulty": Exam.Difficulty.MEDIUM,
            #"grade_level": "3ro secundaria",
            #"competency_type": "procedimental",
            "generator": lambda: _real_number_operations_questions(),
        },
    ],
}


class Command(BaseCommand):

    help = (
        "Puebla datos iniciales del módulo exam "
        "(topics, exams, questions y options)."
    )

    def __init__(self) -> None:
        super().__init__()

        self.topics_created = 0
        self.exams_created = 0
        self.questions_created = 0
        self.options_created = 0

    def handle(self, *args, **options) -> None:

        with transaction.atomic():
            self.main()

        self.stdout.write(self.style.SUCCESS("\nResumen de seed:"))
        self.stdout.write(f"Topics creados: {self.topics_created}")
        self.stdout.write(f"Exams creados: {self.exams_created}")
        self.stdout.write(f"Questions creadas: {self.questions_created}")
        self.stdout.write(f"Options creadas: {self.options_created}")

    def main(self) -> None:

        topics = self.seed_topics()
        exams = self.seed_exams(topics)
        self.seed_questions(exams)

    def seed_topics(self) -> dict[str, Topic]:

        topics: dict[str, Topic] = {}

        for name in TOPIC_NAMES:

            topic, created = Topic.objects.get_or_create(name=name)

            topics[name] = topic

            if created:
                self.topics_created += 1
                self.stdout.write(f"✓ Topic creado: {name}")

        return topics

    def seed_exams(self, topics: dict[str, Topic]) -> dict[str, Exam]:

        exams_by_title: dict[str, Exam] = {}

        for topic_name, exam_specs in EXAM_BLUEPRINTS.items():

            topic = topics[topic_name]

            for spec in exam_specs:

                exam, created = Exam.objects.get_or_create(
                    topic=topic,
                    title=str(spec["title"]),
                    defaults={
                        "description": str(spec["description"]),
                        "difficulty": str(spec["difficulty"]),
                        "recommended_age_min": 12,
                        "recommended_age_max": 16,
                        "is_diagnostic": True,
                        "is_active": True,

                        # NUEVOS CAMPOS
                        #"grade_level": str(spec["grade_level"]),
                        #"competency_type": str(
                        #    spec["competency_type"]
                        #),
                    },
                )

                exams_by_title[exam.title] = exam

                if created:
                    self.exams_created += 1
                    self.stdout.write(
                        f"✓ Exam creado: {exam.title}"
                    )

        return exams_by_title

    def seed_questions(self, exams: dict[str, Exam]) -> None:

        for _, exam_specs in EXAM_BLUEPRINTS.items():

            for spec in exam_specs:

                exam = exams[str(spec["title"])]

                generator = spec["generator"]

                question_items = generator()

                for idx, item in enumerate(question_items, start=1):

                    (
                        question_text,
                        left_label,
                        right_label,
                        is_left_correct,
                    ) = item

                    spoken_question = (
                        f"{question_text} "
                        f"Opción izquierda: {left_label}. "
                        f"Opción derecha: {right_label}."
                    )

                    question, created = Question.objects.get_or_create(
                        exam=exam,
                        order=idx,
                        defaults={
                            "title": (
                                f"{exam.title} - Pregunta {idx}"
                            ),
                            "question_text": question_text,
                            "spoken_instruction":
                                SPOKEN_INSTRUCTION,
                            "spoken_question":
                                spoken_question,
                            "spoken_feedback_correct":
                                SPOKEN_FEEDBACK_CORRECT,
                            "spoken_feedback_incorrect":
                                SPOKEN_FEEDBACK_INCORRECT,
                            "is_active": True,
                        },
                    )

                    if created:

                        self.questions_created += 1

                        self.stdout.write(
                            f"✓ Question creada: "
                            f"{exam.title} (#{idx})"
                        )

                    self.seed_options(
                        question=question,
                        left_label=left_label,
                        right_label=right_label,
                        is_left_correct=is_left_correct,
                    )

    def seed_options(
        self,
        *,
        question: Question,
        left_label: str,
        right_label: str,
        is_left_correct: bool,
    ) -> None:

        left_option, left_created = (
            QuestionOption.objects.get_or_create(
                question=question,
                position=QuestionOption.Position.LEFT,
                defaults={
                    "label": left_label,
                    "is_correct": is_left_correct,
                    "order": 1,
                },
            )
        )

        if left_created:

            self.options_created += 1

            self.stdout.write(
                f"✓ Option creada: "
                f"{left_option.label} (LEFT)"
            )

        right_option, right_created = (
            QuestionOption.objects.get_or_create(
                question=question,
                position=QuestionOption.Position.RIGHT,
                defaults={
                    "label": right_label,
                    "is_correct": not is_left_correct,
                    "order": 2,
                },
            )
        )

        if right_created:

            self.options_created += 1

            self.stdout.write(
                f"✓ Option creada: "
                f"{right_option.label} (RIGHT)"
            )


# =========================================================
# PREGUNTAS COGNITIVAS
# =========================================================

def _fraction_comparison_questions() -> list[QuestionPayload]:

    return [

        (
            "¿Qué fracción es mayor?",
            "3/4",
            "2/3",
            True,
        ),

        (
            "¿Cuál fracción representa una cantidad menor?",
            "1/8",
            "5/8",
            True,
        ),

        (
            "¿Cuál número racional es negativo?",
            "-2/5",
            "3/5",
            True,
        ),

        (
            "¿Cuál fracción es equivalente a 1/2?",
            "2/4",
            "3/4",
            True,
        ),

        (
            "¿Cuál fracción está más cerca de 1?",
            "7/8",
            "1/4",
            True,
        ),
    ]


def _real_number_identification_questions() -> list[QuestionPayload]:

    return [

        (
            "¿Cuál es un número irracional?",
            "√2",
            "0.5",
            True,
        ),

        (
            "¿Cuál pertenece a los números enteros?",
            "-4",
            "2/3",
            True,
        ),

        (
            "¿Cuál es un número decimal exacto?",
            "0.25",
            "√5",
            True,
        ),

        (
            "¿Cuál pertenece a los números racionales?",
            "3/7",
            "π",
            True,
        ),

        (
            "¿Cuál es un número natural?",
            "8",
            "-2",
            True,
        ),
    ]


# =========================================================
# PREGUNTAS PROCEDIMENTALES
# =========================================================

def _fraction_operations_questions() -> list[QuestionPayload]:

    return [

        (
            "¿Cuánto es 1/2 + 1/4?",
            "3/4",
            "2/6",
            True,
        ),

        (
            "¿Cuánto es 5/6 - 1/3?",
            "1/2",
            "2/3",
            True,
        ),

        (
            "¿Cuánto es 2/5 × 3/4?",
            "6/20",
            "5/9",
            True,
        ),

        (
            "¿Cuánto es 3/8 + 1/8?",
            "4/8",
            "5/8",
            True,
        ),

        (
            "¿Cuánto es 4/5 - 2/5?",
            "2/5",
            "3/5",
            True,
        ),
    ]


def _real_number_operations_questions() -> list[QuestionPayload]:

    return [

        (
            "¿Cuánto es √9 + 2?",
            "5",
            "6",
            True,
        ),

        (
            "¿Cuánto es 3.5 + 1.2?",
            "4.7",
            "5.2",
            True,
        ),

        (
            "¿Cuánto es 10 - 3.8?",
            "6.2",
            "7.2",
            True,
        ),

        (
            "¿Cuánto es 2² + 3?",
            "7",
            "9",
            True,
        ),

        (
            "¿Cuánto es √16?",
            "4",
            "8",
            True,
        ),
    ]
