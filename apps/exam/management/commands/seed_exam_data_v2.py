from __future__ import annotations

from collections.abc import Callable
from django.core.management.base import BaseCommand
from django.db import transaction
from exam.models import Exam, Question, QuestionOption, Topic

# Instrucción macro adaptada pedagógicamente para describir el espacio de la pantalla
SPOKEN_INSTRUCTION = (
    "Escucha la situación matemática. Lleva tu dedo a la parte inferior del dispositivo "
    "y deslice a la opción correspondiente. Puede responder arrastrando a la izquierda o derecha, "
    "o diciendo izquierda o derecha."
)
SPOKEN_FEEDBACK_CORRECT = "Respuesta correcta. Excelente trabajo."
SPOKEN_FEEDBACK_INCORRECT = "Respuesta incorrecta. Intenta nuevamente."

QuestionPayload = tuple[str, str, str, bool]
QuestionGenerator = Callable[[], list[QuestionPayload]]

# 1. TEMAS EXPANDIDOS Y REGISTRADOS PARA SEGUNDO GRADO DE SECUNDARIA
TOPIC_NAMES = [
    "Características de los triángulos",
    "Puntos de los triángulos",
    "Propiedades de los triángulos",
    "Operaciones combinadas",
    "Ecuaciones de primer grado",
    "Problemas con casos de la vida real",
]

# 2. SE ANCLAN LOS PLANES DE EXÁMENES DIRECTAMENTE A LAS CAPACIDADES EXIGIDAS
EXAM_BLUEPRINTS = {
    "Características de los triángulos": [
        {
            "title": "Características de los triángulos",
            "description": "Reconoce las principales características y elementos básicos de los triángulos.",
            "difficulty": Exam.Difficulty.EASY,
            "grade_level": "2do secundaria",
            "competency_type": "cognitiva",
            "generator": lambda: _triangle_characteristics_questions(),
        },
    ],

    "Puntos de los triángulos": [
        {
            "title": "Puntos de los triángulos",
            "description": "Identifica los principales puntos notables de un triángulo.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "grade_level": "2do secundaria",
            "competency_type": "cognitiva",
            "generator": lambda: _triangle_points_questions(),
        },
    ],

    "Propiedades de los triángulos": [
        {
            "title": "Propiedades de los triángulos",
            "description": "Aplica propiedades básicas de los triángulos para resolver situaciones matemáticas.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",
            "generator": lambda: _triangle_properties_questions(),
        },
    ],

    "Operaciones combinadas": [
        {
            "title": "Operaciones combinadas",
            "description": "Resuelve operaciones combinadas respetando el orden de las operaciones.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",
            "generator": lambda: _combined_operations_questions(),
        },
    ],

    "Ecuaciones de primer grado": [
        {
            "title": "Ecuaciones de primer grado",
            "description": "Resuelve ecuaciones de primer grado con una incógnita.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",
            "generator": lambda: _linear_equations_questions(),
        },
    ],

    "Problemas con casos de la vida real": [
        {
            "title": "Problemas con casos de la vida real",
            "description": "Plantea y resuelve ecuaciones de primer grado a partir de situaciones cotidianas.",
            "difficulty": Exam.Difficulty.HARD,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",
            "generator": lambda: _everyday_linear_problems_questions(),
        },
    ],
}

class Command(BaseCommand):
    help = "Puebla datos iniciales integrados v4 con exigencias curriculares y accesibilidad auditiva completa."

    def __init__(self) -> None:
        super().__init__()
        self.topics_created = 0
        self.exams_created = 0
        self.questions_created = 0
        self.options_created = 0

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            self.main()

        self.stdout.write(self.style.SUCCESS("\nResumen de seed unificado y corregido:"))
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
                        "recommended_age_max": 14, # Ajustado al rango de 2do de secundaria
                        "is_diagnostic": True,
                        "is_active": True,
                        "grade_level": str(spec["grade_level"]),
                        "competency_type": str(spec["competency_type"]),
                    },
                )
                exams_by_title[exam.title] = exam
                if created:
                    self.exams_created += 1
        return exams_by_title

    def seed_questions(self, exams: dict[str, Exam]) -> None:
        for _, exam_specs in EXAM_BLUEPRINTS.items():
            for spec in exam_specs:
                exam = exams[str(spec["title"])]
                generator = spec["generator"]
                question_items = generator()

                for idx, item in enumerate(question_items, start=1):
                    question_text, left_label, right_label, is_left_correct = item
                    spoken_question = f"{question_text} Opción izquierda: {left_label}. Opción derecha: {right_label}."

                    question, created = Question.objects.get_or_create(
                        exam=exam,
                        order=idx,
                        defaults={
                            "title": f"{exam.title} - Pregunta {idx}",
                            "question_text": question_text,
                            "spoken_instruction": SPOKEN_INSTRUCTION,
                            "spoken_question": spoken_question,
                            "spoken_feedback_correct": SPOKEN_FEEDBACK_CORRECT,
                            "spoken_feedback_incorrect": SPOKEN_FEEDBACK_INCORRECT,
                            "is_active": True,
                        },
                    )
                    if created:
                        self.questions_created += 1

                    self.seed_options(
                        self,
                        question=question,
                        left_label=left_label,
                        right_label=right_label,
                        is_left_correct=is_left_correct,
                    )

    def seed_options(self, self_param, *, question: Question, left_label: str, right_label: str, is_left_correct: bool) -> None:
        left_option, left_created = QuestionOption.objects.get_or_create(
            question=question,
            position=QuestionOption.Position.LEFT,
            defaults={"label": left_label, "is_correct": is_left_correct, "order": 1},
        )
        if left_created:
            self_param.options_created += 1

        right_option, right_created = QuestionOption.objects.get_or_create(
            question=question,
            position=QuestionOption.Position.RIGHT,
            defaults={"label": right_label, "is_correct": not is_left_correct, "order": 2},
        )
        if right_created:
            self_param.options_created += 1


# =========================================================
# BANCO DE PREGUNTAS MODIFICADO Y EXPANDIDO CON DICTADO FONÉTICO
# =========================================================

def _triangle_characteristics_questions() -> list[QuestionPayload]:
    return [
        (
            "Recuerda: un triángulo tiene tres lados y tres ángulos. "
            "¿Cuántos lados tiene un triángulo?",
            "Tres",
            "Cuatro",
            True,
        ),
        (
            "Recuerda: todo triángulo tiene tres ángulos internos. "
            "¿Cuántos ángulos internos tiene un triángulo?",
            "Tres",
            "Dos",
            True,
        ),
        (
            "Recuerda: la suma de los ángulos internos de un triángulo es ciento ochenta grados. "
            "¿Cuánto suman sus ángulos internos?",
            "Ciento ochenta grados",
            "Doscientos grados",
            True,
        ),
        (
            "Recuerda: un triángulo equilátero tiene sus tres lados de igual longitud. "
            "¿Cómo son sus tres lados?",
            "Iguales",
            "Diferentes",
            True,
        ),
        (
            "Recuerda: un triángulo isósceles tiene dos lados de igual longitud. "
            "¿Cuántos lados iguales tiene?",
            "Dos",
            "Tres",
            True,
        ),
    ]

def _triangle_points_questions() -> list[QuestionPayload]:
    return [
        (
            "Recuerda: el punto donde se cruzan las medianas de un triángulo se llama baricentro. "
            "¿Cómo se llama este punto?",
            "Baricentro",
            "Ortocentro",
            True,
        ),
        (
            "Recuerda: el punto donde se cruzan las alturas se llama ortocentro. "
            "¿Cómo se llama este punto?",
            "Ortocentro",
            "Baricentro",
            True,
        ),
        (
            "Recuerda: el punto donde se cruzan las bisectrices se llama incentro. "
            "¿Cómo se llama este punto?",
            "Incentro",
            "Circuncentro",
            True,
        ),
        (
            "Recuerda: el circuncentro es el punto donde se cruzan las mediatrices. "
            "¿Qué líneas se cruzan en el circuncentro?",
            "Mediatrices",
            "Medianas",
            True,
        ),
    ]

def _triangle_properties_questions() -> list[QuestionPayload]:
    return [
        (
            "Recuerda: la suma de los ángulos internos de un triángulo es ciento ochenta grados. "
            "Si dos ángulos miden sesenta y ochenta grados, ¿cuánto mide el tercero?",
            "Cuarenta grados",
            "Cincuenta grados",
            True,
        ),
        (
            "Recuerda: la suma de los ángulos internos es ciento ochenta grados. "
            "Si dos ángulos miden cincuenta y setenta grados, ¿cuánto mide el tercero?",
            "Sesenta grados",
            "Setenta grados",
            True,
        ),
        (
            "Recuerda: en un triángulo equilátero los tres ángulos internos son iguales. "
            "¿Cuánto mide cada ángulo?",
            "Sesenta grados",
            "Noventa grados",
            True,
        ),
        (
            "Recuerda: un triángulo rectángulo tiene un ángulo recto. "
            "¿Cuánto mide un ángulo recto?",
            "Noventa grados",
            "Ciento ochenta grados",
            True,
        ),
    ]

def _combined_operations_questions() -> list[QuestionPayload]:
    return [
        (
            "Recuerda: primero se resuelven las multiplicaciones y divisiones, "
            "antes que las sumas y restas. ¿Cuánto es ocho más dos por tres?",
            "Catorce",
            "Treinta",
            True,
        ),
        (
            "Recuerda: primero se resuelven las multiplicaciones y divisiones. "
            "¿Cuánto es diez menos dos por tres?",
            "Cuatro",
            "Veinticuatro",
            True,
        ),
        (
            "Recuerda: los paréntesis se resuelven primero. "
            "¿Cuánto es cinco más dos, todo multiplicado por tres?",
            "Veintiuno",
            "Once",
            True,
        ),
        (
            "Recuerda: primero se resuelven los paréntesis. "
            "¿Cuánto es diez más cuatro, dividido entre dos?",
            "Siete",
            "Doce",
            True,
        ),
    ]

def _linear_equations_questions() -> list[QuestionPayload]:
    return [
        (
            "Recuerda: para resolver una ecuación debemos encontrar el valor de la incógnita. "
            "¿Cuál es el valor de x en x más cinco igual a doce?",
            "Siete",
            "Diecisiete",
            True,
        ),
        (
            "Recuerda: una ecuación de primer grado tiene la incógnita elevada a uno. "
            "¿Cuál es el valor de x en dos x igual a diez?",
            "Cinco",
            "Veinte",
            True,
        ),
        (
            "Recuerda: para encontrar x podemos realizar la operación inversa. "
            "¿Cuál es el valor de x en x menos cuatro igual a nueve?",
            "Trece",
            "Cinco",
            True,
        ),
        (
            "Recuerda: para resolver tres x igual a dieciocho, dividimos entre tres. "
            "¿Cuál es el valor de x?",
            "Seis",
            "Nueve",
            True,
        ),
        (
            "Recuerda: para resolver cuatro x igual a veinte, dividimos entre cuatro. "
            "¿Cuál es el valor de x?",
            "Cinco",
            "Ocho",
            True,
        ),
    ]

def _everyday_linear_problems_questions() -> list[QuestionPayload]:
    return [
        (
            "Recuerda: una situación puede representarse mediante una ecuación. "
            "Juan compra tres cuadernos iguales y paga quince soles. "
            "Si x representa el precio de un cuaderno, ¿qué ecuación representa la situación?",
            "Tres x igual a quince",
            "Quince x igual a tres",
            True,
        ),
        (
            "Recuerda: una ecuación permite representar una situación cotidiana. "
            "Ana tenía cierta cantidad de soles y recibió cinco soles. "
            "Ahora tiene diecisiete soles. Si x es el dinero que tenía, ¿qué ecuación representa la situación?",
            "x más cinco igual a diecisiete",
            "x menos cinco igual a diecisiete",
            True,
        ),
        (
            "Recuerda: para representar cantidades desconocidas podemos utilizar x. "
            "Un taxi cobra tres soles por kilómetro. Si x representa los kilómetros recorridos "
            "y el viaje costó doce soles, ¿qué ecuación representa la situación?",
            "Tres x igual a doce",
            "Doce x igual a tres",
            True,
        ),
        (
            "Recuerda: una cantidad desconocida puede representarse con x. "
            "Pedro compra cuatro lapiceros iguales y paga veinte soles. "
            "Si x representa el precio de un lapicero, ¿qué ecuación representa la situación?",
            "Cuatro x igual a veinte",
            "Veinte x igual a cuatro",
            True,
        ),
    ]

