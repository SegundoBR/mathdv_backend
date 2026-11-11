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
    
    DIAGNOSTIC_QUESTIONS_PER_TOPIC = 4

    def seed_questions(self, exams: dict[str, Exam]) -> None:
        for _, exam_specs in EXAM_BLUEPRINTS.items():
            for spec in exam_specs:
                exam = exams[str(spec["title"])]
                generator = spec["generator"]

                question_items = generator()[:DIAGNOSTIC_QUESTIONS_PER_TOPIC]

                for idx, item in enumerate(question_items, start=1):
                    question_text, left_label, right_label, is_left_correct = item

                    spoken_question = (
                        f"{question_text} "
                        f"Opción izquierda: {left_label}. "
                        f"Opción derecha: {right_label}."
                    )

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
            "Recuerda: un triángulo tiene tres lados"
            "¿Cuántos ángulos internos tiene un triángulo?",
            "Tres",
            "Dos",
            True,
        ),
        (
            "Recuerda: la suma de los ángulos internos de un triángulo es ciento ochenta grados."
            "¿Cuánto suman sus ángulos internos?",
            "Ciento ochenta grados",
            "Doscientos grados",
            True,
        ),
        (
            "Recuerda: la suma de los ángulos internos de un triángulo es ciento ochenta grados. "
            "Si un ángulo mide setenta grados y otro ochenta grados, ¿cuánto mide el tercero?",
            "Treinta grados",
            "Veinte grados",
            True,
        ),
        (
            "Recuerda: un triángulo equilátero tiene tres lados de igual longitud."
            "Si un lado mide cinco unidades, ¿cuánto miden los otros dos lados?",
            "Cinco",
            "Diez",
            True,
        ),
(
            "Recuerda: un triángulo escaleno tiene todos sus lados de diferente longitud. "
            "¿Cómo son sus ángulos?",
            "Diferentes",
            "Iguales",
            True,
        ),
        (
            "Recuerda: un triángulo equilátero tiene angulos internos iguales y la suma de sus ángulos internos es ciento ochenta grados."
            "¿Cuánto mide un ángulo de un triángulo equilátero?",
            "Sesenta grados",
            "Ochenta grados",
            True,
        ),
        (
            "¿Cómo se llama un triángulo que tiene dos lados iguales?",
            "Isósceles",
            "Escaleno",
            True,
        ),
        (
            "¿Cuál de estos triángulos tiene todos sus lados diferentes?",
            "Escaleno",
            "Equilátero",
            True,
        ),
        (
            "¿Qué característica identifica a un triángulo rectángulo?",
            "Un ángulo de noventa grados",
            "Tres ángulos de noventa grados",
            True,
        ),

    ]

def _triangle_points_questions() -> list[QuestionPayload]:
    return [
        (
            "Recuerda: la mediana une un vértice con el punto medio del lado opuesto. "
            "Si una mediana llega a un lado que mide ocho metros, "
            "¿en cuánto divide ese lado?",
            "En dos partes de cuatro metros",
            "En dos partes de cinco metros",
            True,
        ),
        (
            "Recuerda: el punto donde se cruzan las medianas de un triángulo "
            "se llama baricentro. ¿Cómo se llama este punto?",
            "Baricentro",
            "Ortocentro",
            True,
        ),
        (
            "Recuerda: el punto donde se cruzan las alturas de un triángulo "
            "se llama ortocentro. ¿Cómo se llama este punto?",
            "Ortocentro",
            "Baricentro",
            True,
        ),
        (
            "Recuerda: el punto donde se cruzan las bisectrices de un triángulo "
            "se llama incentro. ¿Cómo se llama este punto?",
            "Incentro",
            "Circuncentro",
            True,
        ),
        (
            "Recuerda: el circuncentro es el punto donde se cruzan las mediatrices "
            "de un triángulo. ¿Qué líneas se cruzan en el circuncentro?",
            "Las mediatrices",
            "Las medianas",
            True,
        ),
        (
            "Recuerda: el baricentro se forma por la intersección de las medianas. "
            "¿Qué líneas debemos trazar para encontrar el baricentro?",
            "Las medianas",
            "Las alturas",
            True,
        ),
        (
            "Recuerda: el ortocentro se obtiene al cruzar las alturas de un triángulo. "
            "¿Qué líneas debemos trazar para encontrar el ortocentro?",
            "Las alturas",
            "Las bisectrices",
            True,
        ),
        (
            "Recuerda: el incentro se obtiene al cruzar las bisectrices de los ángulos "
            "del triángulo. ¿Qué líneas debemos trazar para encontrar el incentro?",
            "Las bisectrices",
            "Las mediatrices",
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
        (
            "Recuerda: los ángulos internos de un triángulo suman ciento ochenta grados. "
            "Si dos ángulos miden noventa y treinta grados, ¿cuánto mide el tercero?",
            "Sesenta grados",
            "Treinta grados",
            True,
        ),
        (
            "Recuerda: en un triángulo equilátero todos sus lados tienen la misma longitud. "
            "Si un lado mide ocho centímetros, ¿cuánto mide otro lado?",
            "Ocho centímetros",
            "Dieciséis centímetros",
            True,
        ),
        (
            "Recuerda: en un triángulo isósceles dos lados tienen la misma longitud. "
            "Si dos lados miden siete centímetros, ¿cuánto mide el otro lado?",
            "No se puede determinar",
            "Catorce centímetros",
            True,
        ),
        (
            "Recuerda: un triángulo rectángulo tiene un ángulo de noventa grados. "
            "Si otro ángulo mide treinta grados, ¿cuánto mide el tercer ángulo?",
            "Sesenta grados",
            "Noventa grados",
            True,
        ),
        (
            "Recuerda: la suma de los ángulos internos de cualquier triángulo siempre es ciento ochenta grados. "
            "Si los ángulos miden cincuenta, cincuenta y ochenta grados, ¿forman un triángulo?",
            "Sí",
            "No",
            True,
        ),
        (
            "Recuerda: la suma de los ángulos internos de cualquier triángulo siempre es ciento ochenta grados. "
            "Si los ángulos miden sesenta, sesenta y sesenta grados, ¿forman un triángulo?",
            "Sí",
            "No",
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
            "Recuerda: primero se resuelven las multiplicaciones y divisiones. "
            "¿Cuánto es seis más cuatro dividido entre dos?",
            "Ocho",
            "Cinco",
            True,
        ),
        (
            "Recuerda: primero se resuelven las multiplicaciones y divisiones. "
            "¿Cuánto es doce menos tres por dos?",
            "Seis",
            "Dieciocho",
            True,
        ),
        (
            "Recuerda: primero se resuelve la división. "
            "¿Cuánto es doce dividido entre tres más cinco?",
            "Nueve",
            "Dos",
            True,
        ),
        (
            "Recuerda: los paréntesis tienen prioridad. "
            "¿Cuánto es nueve menos tres, todo multiplicado por dos?",
            "Doce",
            "Tres",
            True,
        ),
        (
            "Recuerda: primero se resuelve el paréntesis y después la multiplicación. "
            "¿Cuánto es cuatro más tres, multiplicado por dos?",
            "Catorce",
            "Diez",
            True,
        ),
        (
            "Recuerda: primero se resuelve la división y después la suma. "
            "¿Cuánto es dieciséis dividido entre cuatro más seis?",
            "Diez",
            "Cuatro",
            True,
        ),
        (
            "Recuerda: primero se resuelve la multiplicación y después la suma. "
            "¿Cuánto es siete más cinco por dos?",
            "Diecisiete",
            "Veinticuatro",
            True,
        ),
    ]

def _linear_equations_questions() -> list[QuestionPayload]:
    return [
        (
            "Recuerda: para resolver una ecuación debemos encontrar el valor de la incógnita. "
            "¿Cuál es el valor de x en: x más cinco igual a doce?",
            "Siete",
            "Diecisiete",
            True,
        ),
        (
            "Recuerda: una ecuación de primer grado tiene la incógnita elevada a uno. "
            "¿Cuál es el valor de x en: dos x es igual a diez?",
            "Cinco",
            "Veinte",
            True,
        ),
        (
            "Recuerda: para encontrar x podemos realizar la operación inversa. "
            "¿Cuál es el valor de x en: x menos cuatro es igual a nueve?",
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
        (
            "Recuerda: para resolver cuatro x igual a veinte, dividimos entre cuatro. "
            "¿Cuál es el valor de x?",
            "Cinco",
            "Ocho",
            True,
        ),
        ("¿Qué número multiplicado por dos da como resultado diez?", "5", "20", True), ("¿Qué número menos cuatro da como resultado nueve?", "13", "5", True), ("¿Qué número multiplicado por tres da como resultado dieciocho?", "6", "9", True), ("¿Qué número sumado con ocho da como resultado quince?", "7", "23", True), ("¿Qué número menos diez da como resultado cinco?", "15", "5", True), ("¿Qué número multiplicado por cinco da como resultado veinticinco?", "5", "10", True), ("¿Qué número sumado con doce da como resultado veinte?", "8", "32", True), ("¿Qué número multiplicado por cuatro da como resultado dieciséis?", "4", "8", True), ("¿Qué número menos siete da como resultado tres?", "10", "4", True),
    ]

def _everyday_linear_problems_questions() -> list[QuestionPayload]:
    return [
(
            "Un solo cuaderno cuesta seis soles. Si pagué dieciocho soles, ¿cuántos cuadernos compré?",
            "Tres",
            "Dos",
            True,
        ),
        (
            "Recuerda: para representar una cantidad que disminuye podemos utilizar una resta. "
            "Carlos tenía cierta cantidad de soles y gastó cinco. "
            "Ahora tiene diez soles. ¿Cuanto dinero tenía Carlos al principio?",
            "Diez",
            "Quince",
            False,
        ),
        ("Juan compra 3 cuadernos iguales por 15 soles. ¿Cuánto costó cada cuaderno?", "5 soles", "3 soles", True), ("María tiene el doble de la edad de Luis. Si ambas edades suman 18 años, ¿cuál es la edad de Luis?", "6 años", "9 años", True), ("Pedro compró 4 lapiceros por 20 soles. ¿Cuánto costó cada lapicero?", "5 soles", "4 soles", True), ("Ana ahorra 2 soles diarios. Después de 7 días tendrá:", "14 soles", "9 soles", True), ("Un taxi cobra 3 soles por kilómetro. En un viaje de 4 kilómetros cobrará:", "12 soles", "7 soles", True), ("Luis compró 5 caramelos por 10 soles. Cada caramelo cuesta:", "2 soles", "5 soles", True), ("Si un cuaderno cuesta 8 soles, ¿cuánto cuestan 2 cuadernos?", "16 soles", "10 soles", True), ("Un alumno lee 4 páginas diarias. En un periodo de 5 días leerá:", "20 páginas", "15 páginas", True), ("Carlos tiene el triple de dinero que Ana. Si juntos tienen 24 soles, Ana tiene:", "6 soles", "8 soles", True), ("Una caja contiene 6 botellas. ¿Cuántas botellas hay en un lote de 3 cajas?", "18 botellas", "12 botellas", True),
    ]

