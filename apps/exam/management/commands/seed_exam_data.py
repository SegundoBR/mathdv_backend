from __future__ import annotations

from collections.abc import Callable

from django.core.management.base import BaseCommand
from django.db import transaction

from exam.models import Exam, Question, QuestionOption, Topic

SPOKEN_INSTRUCTION = "Escucha la pregunta y desliza el dedo hacia la opción correcta."
SPOKEN_FEEDBACK_CORRECT = "Respuesta correcta. Excelente trabajo."
SPOKEN_FEEDBACK_INCORRECT = "Respuesta incorrecta. Intenta nuevamente."

QuestionPayload = tuple[str, str, str, bool]
QuestionGenerator = Callable[[str], list[QuestionPayload]]

TOPIC_NAMES = [
    "Matemática",
    "Lectura",
    "Memoria",
    "Orientación espacial",
    "Atención",
    "Comprensión verbal",
]

EXAM_BLUEPRINTS: dict[str, list[dict[str, object]]] = {
    "Matemática": [
        {
            "title": "Sumas básicas",
            "description": "Operaciones de suma con números pequeños.",
            "difficulty": Exam.Difficulty.EASY,
            "is_diagnostic": True,
            "generator": lambda title: _math_questions("sum"),
        },
        {
            "title": "Restas básicas",
            "description": "Operaciones de resta con números naturales.",
            "difficulty": Exam.Difficulty.EASY,
            "is_diagnostic": True,
            "generator": lambda title: _math_questions("sub"),
        },
        {
            "title": "Multiplicación básica",
            "description": "Multiplicación de una cifra y tablas frecuentes.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": False,
            "generator": lambda title: _math_questions("mul"),
        },
    ],
    "Lectura": [
        {
            "title": "Comprensión lectora nivel 1",
            "description": "Identificación de ideas simples y vocabulario cotidiano.",
            "difficulty": Exam.Difficulty.EASY,
            "is_diagnostic": True,
            "generator": lambda title: _reading_level_1_questions(),
        },
        {
            "title": "Comprensión lectora nivel 2",
            "description": "Comprensión de textos breves y relaciones causa-efecto.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": False,
            "generator": lambda title: _reading_level_2_questions(),
        },
        {
            "title": "Identificación de palabras",
            "description": "Reconocimiento de categorías y significado de palabras.",
            "difficulty": Exam.Difficulty.EASY,
            "is_diagnostic": False,
            "generator": lambda title: _word_identification_questions(),
        },
    ],
    "Memoria": [
        {
            "title": "Memoria secuencial",
            "description": "Recordar el orden correcto de secuencias numéricas.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": True,
            "generator": lambda title: _memory_sequence_questions(),
        },
        {
            "title": "Recordar patrones",
            "description": "Identificación y retención de patrones visuales simples.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": False,
            "generator": lambda title: _memory_pattern_questions(),
        },
        {
            "title": "Memoria inmediata",
            "description": "Evocación rápida de datos presentados previamente.",
            "difficulty": Exam.Difficulty.EASY,
            "is_diagnostic": False,
            "generator": lambda title: _memory_immediate_questions(),
        },
    ],
    "Orientación espacial": [
        {
            "title": "Ubicación izquierda/derecha",
            "description": "Discriminación de posición espacial básica.",
            "difficulty": Exam.Difficulty.EASY,
            "is_diagnostic": True,
            "generator": lambda title: _spatial_left_right_questions(),
        },
        {
            "title": "Posición relativa",
            "description": "Comprender relaciones como arriba, abajo y entre.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": False,
            "generator": lambda title: _spatial_relative_position_questions(),
        },
        {
            "title": "Reconocimiento espacial",
            "description": "Identificación de figuras y ubicaciones en contextos simples.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": False,
            "generator": lambda title: _spatial_recognition_questions(),
        },
    ],
    "Atención": [
        {
            "title": "Atención sostenida",
            "description": "Mantener foco en tareas repetitivas por varios ítems.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": True,
            "generator": lambda title: _attention_sustained_questions(),
        },
        {
            "title": "Atención selectiva",
            "description": "Seleccionar información relevante entre distractores.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": False,
            "generator": lambda title: _attention_selective_questions(),
        },
        {
            "title": "Detección rápida",
            "description": "Reconocimiento veloz de estímulos correctos.",
            "difficulty": Exam.Difficulty.HARD,
            "is_diagnostic": False,
            "generator": lambda title: _attention_fast_detection_questions(),
        },
    ],
    "Comprensión verbal": [
        {
            "title": "Sinónimos básicos",
            "description": "Reconocimiento de palabras con significado similar.",
            "difficulty": Exam.Difficulty.EASY,
            "is_diagnostic": True,
            "generator": lambda title: _verbal_synonyms_questions(),
        },
        {
            "title": "Relación de palabras",
            "description": "Comprender relaciones lógicas entre términos.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": False,
            "generator": lambda title: _verbal_relation_questions(),
        },
        {
            "title": "Asociación verbal",
            "description": "Asociar términos por categoría y contexto de uso.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "is_diagnostic": False,
            "generator": lambda title: _verbal_association_questions(),
        },
    ],
}


class Command(BaseCommand):
    help = "Puebla datos iniciales del módulo exam (topics, exams, questions, options)."

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
                        "recommended_age_min": 6,
                        "recommended_age_max": 12,
                        "is_diagnostic": bool(spec["is_diagnostic"]),
                        "is_active": True,
                    },
                )
                exams_by_title[exam.title] = exam
                if created:
                    self.exams_created += 1
                    self.stdout.write(f"✓ Exam creado: {exam.title}")
        return exams_by_title

    def seed_questions(self, exams: dict[str, Exam]) -> None:
        for topic_name, exam_specs in EXAM_BLUEPRINTS.items():
            _ = topic_name
            for spec in exam_specs:
                exam = exams[str(spec["title"])]
                generator = spec["generator"]
                question_items = generator(exam.title)

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
                        self.stdout.write(f"✓ Question creada: {exam.title} (#{idx})")

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
        left_option, left_created = QuestionOption.objects.get_or_create(
            question=question,
            position=QuestionOption.Position.LEFT,
            defaults={
                "label": left_label,
                "is_correct": is_left_correct,
                "order": 1,
            },
        )
        if left_created:
            self.options_created += 1
            self.stdout.write(f"✓ Option creada: {left_option.label} (LEFT)")

        right_option, right_created = QuestionOption.objects.get_or_create(
            question=question,
            position=QuestionOption.Position.RIGHT,
            defaults={
                "label": right_label,
                "is_correct": not is_left_correct,
                "order": 2,
            },
        )
        if right_created:
            self.options_created += 1
            self.stdout.write(f"✓ Option creada: {right_option.label} (RIGHT)")


def _math_questions(kind: str) -> list[QuestionPayload]:
    if kind == "sum":
        return [
            ("¿Cuánto es 5 + 3?", "8", "6", True),
            ("¿Cuánto es 7 + 2?", "10", "9", False),
            ("¿Cuánto es 4 + 4?", "8", "9", True),
            ("¿Cuánto es 9 + 1?", "10", "11", True),
            ("¿Cuánto es 6 + 5?", "12", "11", False),
            ("¿Cuánto es 3 + 7?", "10", "9", True),
            ("¿Cuánto es 2 + 8?", "11", "10", False),
            ("¿Cuánto es 1 + 6?", "7", "8", True),
            ("¿Cuánto es 8 + 2?", "9", "10", False),
            ("¿Cuánto es 5 + 4?", "9", "8", True),
        ]
    if kind == "sub":
        return [
            ("¿Cuánto es 9 - 4?", "5", "6", True),
            ("¿Cuánto es 10 - 3?", "6", "7", False),
            ("¿Cuánto es 8 - 2?", "5", "6", False),
            ("¿Cuánto es 7 - 5?", "2", "3", True),
            ("¿Cuánto es 6 - 1?", "5", "4", True),
            ("¿Cuánto es 12 - 4?", "7", "8", False),
            ("¿Cuánto es 15 - 6?", "9", "8", True),
            ("¿Cuánto es 11 - 2?", "10", "9", False),
            ("¿Cuánto es 14 - 7?", "6", "7", False),
            ("¿Cuánto es 13 - 5?", "8", "9", True),
        ]
    return [
        ("¿Cuánto es 8 × 7?", "54", "56", False),
        ("¿Cuánto es 6 × 4?", "24", "26", True),
        ("¿Cuánto es 9 × 3?", "27", "24", True),
        ("¿Cuánto es 5 × 5?", "20", "25", False),
        ("¿Cuánto es 7 × 2?", "15", "14", False),
        ("¿Cuánto es 4 × 8?", "32", "30", True),
        ("¿Cuánto es 3 × 6?", "18", "16", True),
        ("¿Cuánto es 2 × 9?", "17", "18", False),
        ("¿Cuánto es 10 × 2?", "22", "20", False),
        ("¿Cuánto es 11 × 3?", "33", "31", True),
    ]


def _reading_level_1_questions() -> list[QuestionPayload]:
    return [
        ("¿Qué palabra es un animal?", "perro", "mesa", True),
        ("¿Cuál palabra sirve para leer?", "libro", "zapato", True),
        ("En la frase 'Ana corre', ¿quién corre?", "Ana", "Corre", True),
        ("¿Qué objeto usamos para escribir?", "lápiz", "ventana", True),
        ("¿Cuál es una fruta?", "manzana", "silla", True),
        ("¿Qué palabra nombra un color?", "azul", "camino", True),
        ("¿Qué usamos para comer sopa?", "cuchara", "almohada", True),
        ("¿Qué palabra representa una acción?", "saltar", "pelota", True),
        ("¿Cuál se puede beber?", "agua", "piedra", True),
        ("¿Qué palabra nombra una parte del cuerpo?", "mano", "cuaderno", True),
    ]


def _reading_level_2_questions() -> list[QuestionPayload]:
    return [
        ("Si llueve, ¿qué es mejor usar?", "paraguas", "sombrero de fiesta", True),
        (
            "En 'Luis estudia porque mañana hay examen', ¿cuál es la causa?",
            "Mañana hay examen",
            "Luis estudia",
            True,
        ),
        (
            "Si una planta no recibe agua, ¿qué puede pasar?",
            "Se marchita",
            "Crece más rápido",
            True,
        ),
        ("¿Qué palabra completa mejor: 'El niño ___ la puerta'?", "abre", "nube", True),
        ("Si termina una carrera en primer lugar, ¿qué hizo?", "Ganó", "Perdió", True),
        (
            "¿Qué ocurre primero para hacer jugo?",
            "Lavar la fruta",
            "Servir en vaso",
            True,
        ),
        (
            "En 'Marta apagó la luz para dormir', ¿para qué apagó la luz?",
            "Para dormir",
            "Para correr",
            True,
        ),
        (
            "¿Cuál palabra pertenece a la misma categoría que 'camisa'?",
            "pantalón",
            "tenedor",
            True,
        ),
        (
            "Si un texto dice 'hace mucho frío', ¿qué clima describe?",
            "invierno",
            "verano intenso",
            True,
        ),
        (
            "¿Qué idea resume mejor: 'Cepillarse los dientes evita caries'?",
            "La higiene cuida la salud",
            "Dormir tarde es saludable",
            True,
        ),
    ]


def _word_identification_questions() -> list[QuestionPayload]:
    return [
        ("¿Cuál palabra es un transporte?", "autobús", "almohada", True),
        ("¿Cuál palabra es un alimento?", "arroz", "ladrillo", True),
        ("¿Cuál palabra es una emoción?", "alegría", "martillo", True),
        ("¿Cuál palabra es una profesión?", "médico", "colina", True),
        ("¿Cuál palabra es una prenda de vestir?", "casaca", "botella", True),
        ("¿Cuál palabra es un lugar?", "escuela", "paraguas", True),
        ("¿Cuál palabra es una acción?", "correr", "cuaderno", True),
        ("¿Cuál palabra es un instrumento musical?", "guitarra", "sartén", True),
        ("¿Cuál palabra es un medio de comunicación?", "radio", "almacén", True),
        ("¿Cuál palabra es un mueble?", "sofá", "naranja", True),
    ]


def _memory_sequence_questions() -> list[QuestionPayload]:
    return [
        ("Recuerda la secuencia: 4, 2, 7. ¿Cuál apareció primero?", "4", "7", True),
        ("Recuerda la secuencia: 9, 1, 5. ¿Cuál apareció al final?", "1", "5", False),
        ("Recuerda la secuencia: 3, 8, 6. ¿Cuál está en medio?", "8", "3", True),
        (
            "Recuerda la secuencia: rojo, azul, verde. ¿Cuál fue segundo?",
            "azul",
            "verde",
            True,
        ),
        (
            "Recuerda la secuencia: sol, luna, estrella. ¿Cuál fue primero?",
            "sol",
            "luna",
            True,
        ),
        ("Recuerda la secuencia: A, C, B. ¿Cuál fue último?", "C", "B", False),
        ("Recuerda la secuencia: 2, 4, 9. ¿Cuál número fue mayor?", "9", "4", True),
        (
            "Recuerda la secuencia: casa, árbol, río. ¿Cuál va en medio?",
            "árbol",
            "río",
            True,
        ),
        ("Recuerda la secuencia: 5, 1, 8. ¿Cuál fue primero?", "8", "5", False),
        (
            "Recuerda la secuencia: gato, perro, ave. ¿Cuál fue último?",
            "perro",
            "ave",
            False,
        ),
    ]


def _memory_pattern_questions() -> list[QuestionPayload]:
    return [
        (
            "Patrón: círculo, cuadrado, círculo, cuadrado. ¿Qué sigue?",
            "círculo",
            "triángulo",
            True,
        ),
        ("Patrón: 2, 4, 2, 4. ¿Qué sigue?", "4", "2", False),
        (
            "Patrón: rojo, rojo, azul, rojo, rojo, azul. ¿Qué sigue?",
            "rojo",
            "azul",
            True,
        ),
        ("Patrón: 1, 3, 5. ¿Qué número continúa?", "7", "8", True),
        (
            "Patrón: grande, pequeño, grande, pequeño. ¿Qué sigue?",
            "grande",
            "mediano",
            True,
        ),
        ("Patrón: A, B, A, B. ¿Qué letra sigue?", "A", "C", True),
        ("Patrón: 10, 8, 6. ¿Qué sigue?", "4", "5", True),
        ("Patrón: luna, sol, luna, sol. ¿Qué sigue?", "estrella", "luna", False),
        ("Patrón: 3, 6, 9. ¿Qué número continúa?", "12", "11", True),
        (
            "Patrón: triángulo, triángulo, cuadrado. ¿Qué sigue?",
            "triángulo",
            "cuadrado",
            True,
        ),
    ]


def _memory_immediate_questions() -> list[QuestionPayload]:
    return [
        (
            "Escucha: manzana, libro. ¿Cuál palabra escuchaste?",
            "manzana",
            "camisa",
            True,
        ),
        ("Escucha: 8 y 3. ¿Cuál número fue mayor?", "3", "8", False),
        ("Escucha: perro, gato. ¿Cuál se dijo primero?", "perro", "gato", True),
        ("Escucha: azul, verde. ¿Cuál color se mencionó?", "verde", "mesa", True),
        ("Escucha: lunes, martes. ¿Cuál fue segundo?", "martes", "lunes", True),
        ("Escucha: 5, 9. ¿Cuál fue primero?", "9", "5", False),
        ("Escucha: casa, escuela. ¿Cuál palabra apareció?", "escuela", "lluvia", True),
        ("Escucha: 2, 2, 7. ¿Qué número se repitió?", "2", "7", True),
        ("Escucha: sol, nube. ¿Cuál fue último?", "sol", "nube", False),
        ("Escucha: taza, plato. ¿Cuál fue mencionado?", "plato", "árbol", True),
    ]


def _spatial_left_right_questions() -> list[QuestionPayload]:
    return [
        (
            "Si el lápiz está a la izquierda del cuaderno, ¿qué está a la izquierda?",
            "lápiz",
            "cuaderno",
            True,
        ),
        (
            "Si la pelota está a la derecha de la caja, ¿qué está a la derecha?",
            "pelota",
            "caja",
            True,
        ),
        (
            "Si Ana está a la izquierda de Luis, ¿quién está a la izquierda?",
            "Ana",
            "Luis",
            True,
        ),
        (
            "Si el árbol está a la derecha de la casa, ¿qué está a la izquierda?",
            "árbol",
            "casa",
            False,
        ),
        (
            "Si el gato está a la izquierda del perro, ¿quién está a la derecha?",
            "gato",
            "perro",
            False,
        ),
        (
            "Si el vaso está a la derecha del plato, ¿qué está a la derecha?",
            "vaso",
            "plato",
            True,
        ),
        (
            "Si el reloj está a la izquierda de la puerta, ¿qué está a la izquierda?",
            "reloj",
            "puerta",
            True,
        ),
        (
            "Si la silla está a la derecha de la mesa, ¿qué está a la izquierda?",
            "silla",
            "mesa",
            False,
        ),
        (
            "Si el libro está a la izquierda del lapicero, ¿qué está a la derecha?",
            "lapicero",
            "libro",
            True,
        ),
        (
            "Si la flor está a la derecha del árbol, ¿qué está a la derecha?",
            "flor",
            "árbol",
            True,
        ),
    ]


def _spatial_relative_position_questions() -> list[QuestionPayload]:
    return [
        (
            "Si la pelota está encima de la mesa, ¿dónde está la pelota?",
            "encima de la mesa",
            "debajo de la mesa",
            True,
        ),
        (
            "Si el gato está debajo de la silla, ¿dónde está el gato?",
            "sobre la silla",
            "debajo de la silla",
            False,
        ),
        (
            "Si el libro está entre el lápiz y la goma, ¿dónde está el libro?",
            "entre ambos",
            "afuera",
            True,
        ),
        (
            "Si la nube está arriba de la montaña, ¿dónde está la nube?",
            "arriba",
            "abajo",
            True,
        ),
        (
            "Si la mochila está detrás de la puerta, ¿dónde está?",
            "delante",
            "detrás",
            False,
        ),
        (
            "Si el carro está delante del bus, ¿qué vehículo va primero?",
            "carro",
            "bus",
            True,
        ),
        (
            "Si la taza está al lado del plato, ¿cómo se relacionan?",
            "están separados por una pared",
            "están uno al lado del otro",
            False,
        ),
        (
            "Si el perro está frente al niño, ¿dónde está el perro?",
            "frente al niño",
            "lejos del niño",
            True,
        ),
        (
            "Si la caja está debajo de la cama, ¿dónde está la caja?",
            "debajo",
            "encima",
            True,
        ),
        (
            "Si la lámpara está encima de la mesa, ¿qué está debajo?",
            "lámpara",
            "mesa",
            False,
        ),
    ]


def _spatial_recognition_questions() -> list[QuestionPayload]:
    return [
        ("¿Cuál figura tiene tres lados?", "triángulo", "círculo", True),
        ("¿Cuál figura tiene cuatro lados iguales?", "cuadrado", "rectángulo", True),
        ("¿Cuál figura no tiene esquinas?", "círculo", "triángulo", True),
        ("¿Cuál objeto suele ser redondo?", "pelota", "cuaderno", True),
        ("¿Qué figura se parece a una puerta?", "rectángulo", "círculo", True),
        ("¿Qué figura tiene forma de rueda?", "círculo", "cuadrado", True),
        (
            "¿Qué figura tiene cuatro lados pero no todos iguales?",
            "rectángulo",
            "triángulo",
            True,
        ),
        (
            "¿Qué figura usarías para dibujar una señal de alto?",
            "octágono",
            "línea recta",
            True,
        ),
        ("¿Cuál de estas es una forma espacial?", "cubo", "número", True),
        ("¿Qué forma tiene la punta de un lápiz?", "triángulo", "círculo", True),
    ]


def _attention_sustained_questions() -> list[QuestionPayload]:
    return [
        ("Selecciona el número mayor: 7 o 5.", "7", "5", True),
        ("Selecciona la letra que se repite: A, B, A.", "A", "B", True),
        ("Selecciona el día que viene después de lunes.", "martes", "domingo", True),
        ("Selecciona el número menor: 3 o 8.", "8", "3", False),
        ("Selecciona la palabra más corta: sol o mariposa.", "sol", "mariposa", True),
        ("Selecciona el color primario: rojo o marrón.", "rojo", "marrón", True),
        ("Selecciona el número par: 9 o 10.", "9", "10", False),
        (
            "Selecciona la figura con esquinas: círculo o cuadrado.",
            "círculo",
            "cuadrado",
            False,
        ),
        (
            "Selecciona la estación más fría: verano o invierno.",
            "invierno",
            "verano",
            True,
        ),
        (
            "Selecciona la acción correcta para dormir: correr o descansar.",
            "correr",
            "descansar",
            False,
        ),
    ]


def _attention_selective_questions() -> list[QuestionPayload]:
    return [
        (
            "Entre estas palabras, elige un animal: silla o gato.",
            "silla",
            "gato",
            False,
        ),
        ("Elige un número impar: 4 o 5.", "4", "5", False),
        ("Elige un medio de transporte: avión o cuchara.", "avión", "cuchara", True),
        ("Elige la fruta: manzana o zapato.", "manzana", "zapato", True),
        ("Elige la letra vocal: M o A.", "M", "A", False),
        (
            "Elige la palabra relacionada con escuela: pizarra o martillo.",
            "pizarra",
            "martillo",
            True,
        ),
        ("Elige el objeto que da luz: foco o almohada.", "foco", "almohada", True),
        ("Elige el número mayor: 14 o 9.", "14", "9", True),
        (
            "Elige la palabra que es una acción: correr o ventana.",
            "correr",
            "ventana",
            True,
        ),
        (
            "Elige la estación lluviosa en muchas regiones: verano o otoño.",
            "verano",
            "otoño",
            False,
        ),
    ]


def _attention_fast_detection_questions() -> list[QuestionPayload]:
    return [
        ("Detecta rápidamente el número que falta: 2, 4, 6, __.", "8", "7", True),
        ("Detecta la palabra diferente: perro, gato, mesa.", "mesa", "gato", True),
        ("Detecta el resultado correcto: 3 + 4.", "8", "7", False),
        ("Detecta la letra distinta: A, A, B, A.", "A", "B", False),
        ("Detecta cuál no es color: azul o bicicleta.", "azul", "bicicleta", False),
        ("Detecta el número mayor: 19 o 13.", "19", "13", True),
        (
            "Detecta la palabra mal escrita: casa o caza (si se refiere a vivienda).",
            "caza",
            "casa",
            True,
        ),
        (
            "Detecta la figura con lados: círculo o triángulo.",
            "círculo",
            "triángulo",
            False,
        ),
        (
            "Detecta el día del fin de semana: miércoles o sábado.",
            "miércoles",
            "sábado",
            False,
        ),
        ("Detecta el objeto escolar: cuaderno o tenedor.", "cuaderno", "tenedor", True),
    ]


def _verbal_synonyms_questions() -> list[QuestionPayload]:
    return [
        ("¿Cuál es un sinónimo de feliz?", "contento", "triste", True),
        ("¿Cuál es un sinónimo de rápido?", "veloz", "lento", True),
        ("¿Cuál es un sinónimo de grande?", "enorme", "pequeño", True),
        ("¿Cuál es un sinónimo de bonito?", "hermoso", "feo", True),
        ("¿Cuál es un sinónimo de iniciar?", "comenzar", "terminar", True),
        ("¿Cuál es un sinónimo de ayudar?", "apoyar", "ignorar", True),
        ("¿Cuál es un sinónimo de escuchar?", "oír", "callar", True),
        ("¿Cuál es un sinónimo de aprender?", "estudiar", "olvidar", True),
        ("¿Cuál es un sinónimo de tranquilo?", "calmado", "nervioso", True),
        ("¿Cuál es un sinónimo de fuerte?", "resistente", "débil", True),
    ]


def _verbal_relation_questions() -> list[QuestionPayload]:
    return [
        ("Pájaro es a volar como pez es a...", "nadar", "caminar", True),
        ("Libro es a leer como lápiz es a...", "escribir", "saltar", True),
        ("Sol es a día como luna es a...", "noche", "tarde", True),
        ("Zapato es a pie como guante es a...", "mano", "codo", True),
        ("Cuchara es a sopa como tenedor es a...", "ensalada", "agua", True),
        ("Profesor es a escuela como médico es a...", "hospital", "estadio", True),
        ("Invierno es a frío como verano es a...", "calor", "hielo", True),
        ("Semilla es a planta como huevo es a...", "pollo", "piedra", True),
        ("Reloj es a hora como balanza es a...", "peso", "color", True),
        (
            "Biblioteca es a libros como farmacia es a...",
            "medicinas",
            "herramientas",
            True,
        ),
    ]


def _verbal_association_questions() -> list[QuestionPayload]:
    return [
        ("¿Qué palabra se asocia con hospital?", "enfermera", "tractor", True),
        ("¿Qué palabra se asocia con cocina?", "sartén", "pelota", True),
        ("¿Qué palabra se asocia con playa?", "arena", "semáforo", True),
        ("¿Qué palabra se asocia con escuela?", "cuaderno", "martillo", True),
        ("¿Qué palabra se asocia con lluvia?", "paraguas", "guitarra", True),
        ("¿Qué palabra se asocia con música?", "melodía", "martes", True),
        ("¿Qué palabra se asocia con dormir?", "almohada", "bicicleta", True),
        ("¿Qué palabra se asocia con jardín?", "flor", "computadora", True),
        ("¿Qué palabra se asocia con escribir?", "lapicero", "botella", True),
        ("¿Qué palabra se asocia con invierno?", "abrigo", "sombrero de playa", True),
    ]
