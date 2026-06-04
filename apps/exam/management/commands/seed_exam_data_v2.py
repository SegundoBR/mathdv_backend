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
    "Números racionales",
    "Números reales y notación",
    "Sucesiones con números reales",
    "Ecuaciones de primer grado",
    "Porcentajes e IGV",
    "Conversión de unidades",
    "Medidas de tendencia central",
]

# 2. SE ANCLAN LOS PLANES DE EXÁMENES DIRECTAMENTE A LAS CAPACIDADES EXIGIDAS
EXAM_BLUEPRINTS = {
    "Números racionales": [
        {
            "title": "Comparación de fracciones",
            "description": "Identifica relaciones y comparaciones conceptuales entre fracciones.",
            "difficulty": Exam.Difficulty.EASY,
            "grade_level": "2do secundaria",
            "competency_type": "cognitiva",  # Actividad de Comprensión
            "generator": lambda: _fraction_comparison_questions(),
        },
        {
            "title": "Operaciones con fracciones",
            "description": "Resuelve operaciones básicas de cálculo mental con fracciones.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",  # Actividad de Aplicación
            "generator": lambda: _fraction_operations_questions(),
        },
    ],
    "Números reales y notación": [
        {
            "title": "Identificación de números reales",
            "description": "Reconoce números racionales e irracionales.",
            "difficulty": Exam.Difficulty.EASY,
            "grade_level": "2do secundaria", # Corregido a 2do de secundaria según CENEB
            "competency_type": "cognitiva",
            "generator": lambda: _real_number_identification_questions(),
        },
        {
            "title": "Operaciones y notación científica",
            "description": "Resuelve operaciones básicas e interpreta expresiones de potencias y notación científica.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "grade_level": "2do secundaria", # Corregido a 2do de secundaria
            "competency_type": "procedimental",
            "generator": lambda: _real_number_operations_questions(),
        },
    ],
    "Sucesiones con números reales": [
        {
            "title": "Patrones y Sucesiones Reales",
            "description": "Descubre el término faltante en progresiones aritméticas y geométricas.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "grade_level": "2do secundaria", # Ajustado a Ciclo VI
            "competency_type": "cognitiva",
            "generator": lambda: _real_sequences_questions(),
        }
    ],
    "Ecuaciones de primer grado": [
        {
            "title": "Resolución de Ecuaciones Lineales",
            "description": "Despeja la incógnita en problemas lineales simples.",
            "difficulty": Exam.Difficulty.EASY,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",
            "generator": lambda: _linear_equations_questions(),
        },
        {
            "title": "Casos Cotidianos con Ecuaciones Lineales",
            "description": "Plantea y resuelve situaciones de compras y préstamos basados en casos reales cotidianos.",
            "difficulty": Exam.Difficulty.HARD,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",
            "generator": lambda: _everyday_linear_problems_questions(),
        }
    ],
    "Porcentajes e IGV": [
        {
            "title": "Aumentos, descuentos e IGV",
            "description": "Resuelve problemas comerciales aplicando el impuesto general a las ventas (IGV) y descuentos.",
            "difficulty": Exam.Difficulty.HARD,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",
            "generator": lambda: _percentage_questions(),
        }
    ],
    "Conversión de unidades": [
        {
            "title": "Conversión de masa, tiempo y divisas",
            "description": "Mapea y convierte unidades de temperatura, pesos y monedas de diferentes países.",
            "difficulty": Exam.Difficulty.MEDIUM,
            "grade_level": "2do secundaria",
            "competency_type": "procedimental",
            "generator": lambda: _unit_conversion_questions(),
        }
    ],
    "Medidas de tendencia central": [
        {
            "title": "Cálculo de tendencia estadística",
            "description": "Analiza e identifica la media, la mediana y la moda en lotes de datos numéricos.",
            "difficulty": Exam.Difficulty.EASY,
            "grade_level": "2do secundaria",
            "competency_type": "cognitiva",
            "generator": lambda: _statistics_questions(),
        }
    ]
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

def _fraction_comparison_questions() -> list[QuestionPayload]:
    return [
        ("¿Qué fracción es mayor?", "Tres Cuartos", "Dos Tercios", True),
        ("¿Cuál fracción representa una cantidad menor?", "Un Octavo", "Un Cuarto", True),
        ("¿Cuál número racional es negativo?", "Menos Dos Tercios", "Tres Quintos", True),
        ("¿Cuál fracción es equivalente a Un Medio?", "Dos Cuartos", "Tres Cuartos", True),
        ("¿Cuál fracción está más cerca del número entero uno?", "Siete Octavos", "Un Cuarto", True),
    ]

def _real_number_identification_questions() -> list[QuestionPayload]:
    return [
        ("¿Cuál pertenece a los números enteros?", "Menos Cuatro", "Dos Tercios", True),
        ("¿Cuál es un número decimal exacto?", "Cero Coma Veinticinco", "Raíz de Once", True),
        ("¿Cuál pertenece a los números racionales?", "Tres Novenos", "Pi", True),
        ("¿Cuál es un número natural?", "Ocho", "Menos Dos", True),
    ]

def _fraction_operations_questions() -> list[QuestionPayload]:
    return [
        # Corrección fonética del dictado de las operaciones para evitar el error barra (/)
        ("¿Cuánto resulta al sumar un medio más un cuarto?", "Tres cuartos", "Dos sextos", True),
        ("¿Cuánto resulta al restar cinco sextos menos un tercio?", "Un medio", "Dos tercios", True),
        ("¿Cuánto resulta al multiplicar dos quintos por tres cuartos?", "Seis veinteavos", "Cinco novenos", True),
        ("¿Cuánto resulta al sumar tres octavos más un octavo?", "Cuatro octavos", "Cinco octavos", True),
        ("¿Cuánto resulta al restar cuatro quintos menos dos quintos?", "Dos quintos", "Tres quintos", True),
    ]

def _real_number_operations_questions() -> list[QuestionPayload]:
    return [
        ("¿Cuánto es la raíz cuadrada de nueve sumado con el número dos?", "Cinco", "Seis", True),
        ("¿Cuánto es tres coma cinco más un coma dos?", "Cuatro coma siete", "Cinco coma dos", True),
        ("¿Cuánto es diez menos tres coma ocho?", "Seis coma dos", "Siete coma dos", True),
        # Adición de Notación Exponencial solicitada por el revisor:
        ("¿Cómo se lee diez elevado al exponente tres en notación exponencial?", "Mil", "Trescientos", True),
        ("¿Cuánto es la raíz cuadrada de dieciséis?", "Cuatro", "Ocho", True),
    ]

def _real_sequences_questions() -> list[QuestionPayload]:
    return [
        ("En la sucesión aritmética: 2, 5, 8... ¿Qué número sigue?", "11", "10", True),
        ("En la sucesión geométrica: 3, 6, 12... ¿Qué número sigue?", "24", "18", True),
        ("En la sucesión: 4, 8, 12... ¿Qué número sigue?", "16", "18", True),
        ("En la sucesión: 1, 4, 7... ¿Qué número sigue?", "10", "9", True),
        ("En la sucesión: 5, 10, 20... ¿Qué número sigue?", "40", "30", True),
        ("En la sucesión: 10, 8, 6... ¿Qué número sigue?", "4", "5", True),
        ("En la sucesión: 1, 3, 9... ¿Qué número sigue?", "27", "12", True),
        ("En la sucesión: 100, 90, 80... ¿Qué número sigue?", "70", "75", True),
        ("En la sucesión: 7, 14, 21... ¿Qué número sigue?", "28", "24", True),
        ("En la sucesión: 2, 4, 8... ¿Qué número sigue?", "16", "12", True),
    ]

def _linear_equations_questions() -> list[QuestionPayload]:
    return [
        ("¿Qué número sumado con cinco da como resultado doce?", "7", "17", True),
        ("¿Qué número multiplicado por dos da como resultado diez?", "5", "20", True),
        ("¿Qué número menos cuatro da como resultado nueve?", "13", "5", True),
        ("¿Qué número multiplicado por tres da como resultado dieciocho?", "6", "9", True),
        ("¿Qué número sumado con ocho da como resultado quince?", "7", "23", True),
        ("¿Qué número menos diez da como resultado cinco?", "15", "5", True),
        ("¿Qué número multiplicado por cinco da como resultado veinticinco?", "5", "10", True),
        ("¿Qué número sumado con doce da como resultado veinte?", "8", "32", True),
        ("¿Qué número multiplicado por cuatro da como resultado dieciséis?", "4", "8", True),
        ("¿Qué número menos siete da como resultado tres?", "10", "4", True),
    ]

def _everyday_linear_problems_questions() -> list[QuestionPayload]:
    return [
        ("Juan compra 3 cuadernos iguales por 15 soles. ¿Cuánto costó cada cuaderno?", "5 soles", "3 soles", True),
        ("María tiene el doble de la edad de Luis. Si ambas edades suman 18 años, ¿cuál es la edad de Luis?", "6 años", "9 años", True),
        ("Pedro compró 4 lapiceros por 20 soles. ¿Cuánto costó cada lapicero?", "5 soles", "4 soles", True),
        ("Ana ahorra 2 soles diarios. Después de 7 días tendrá:", "14 soles", "9 soles", True),
        ("Un taxi cobra 3 soles por kilómetro. En un viaje de 4 kilómetros cobrará:", "12 soles", "7 soles", True),
        ("Luis compró 5 caramelos por 10 soles. Cada caramelo cuesta:", "2 soles", "5 soles", True),
        ("Si un cuaderno cuesta 8 soles, ¿cuánto cuestan 2 cuadernos?", "16 soles", "10 soles", True),
        ("Un alumno lee 4 páginas diarias. En un periodo de 5 días leerá:", "20 páginas", "15 páginas", True),
        ("Carlos tiene el triple de dinero que Ana. Si juntos tienen 24 soles, Ana tiene:", "6 soles", "8 soles", True),
        ("Una caja contiene 6 botellas. ¿Cuántas botellas hay en un lote de 3 cajas?", "18 botellas", "12 botellas", True),
    ]

def _percentage_questions() -> list[QuestionPayload]:
    return [
        ("Una camisa cuesta cien soles y tiene un descuento de veinte por ciento. ¿Cuál es el nuevo precio?", "ochenta soles", "noventa soles", True),
        ("Un producto cuesta cincuenta soles. Si aumenta diez por ciento, costará:", "cincuenta y cinco soles", "sesenta soles", True),
        # Casos de IGV solicitados:
        ("Un reproductor cuesta cien soles sin impuesto. Al aplicarle el dieciocho por ciento de I G V, ¿cuánto cuesta?", "ciento dieciocho soles", "ciento ocho soles", True),
        ("El veinte por ciento de cien es:", "veinte", "diez", True),
        ("El cincuenta por ciento de doscientos es:", "cien", "cincuenta", True),
        # Descuentos sucesivos solicitados por el revisor:
        ("Si un parlante de cien soles recibe dos desvíos o descuentos sucesivos del diez por ciento, ¿su precio final es ochenta soles?", "No, porque el segundo descuento opera sobre el nuevo saldo", "Sí, los porcentajes se restan directo", True),
        ("El diez por ciento de cincuenta es:", "cinco", "diez", True),
        ("Un producto de cien soles con descuento del treinta por ciento cuesta:", "setenta soles", "ochenta soles", True),
        ("El veinticinco por ciento de cien es:", "veinticinco", "quince", True),
        ("Un producto cuesta doscientos soles. Con descuento de un cuarto del total queda en:", "ciento cincuenta soles", "ciento setenta soles", True),
    ]

def _unit_conversion_questions() -> list[QuestionPayload]:
    return [
        ("¿Cuántos gramos tiene un kilogramo de masa?", "mil gramos", "cien gramos", True),
        ("¿Cuántos minutos tiene una hora de tiempo?", "sesenta minutos", "cien minutos", True),
        ("¿Cuántas horas tiene un día completo?", "veinticuatro horas", "doce horas", True),
        ("¿Cuántos centímetros tiene un metro de longitud?", "cien centímetros", "mil centímetros", True),
        ("¿Cuántos segundos tiene un minuto?", "sesenta segundos", "cien segundos", True),
        ("Dos kilogramos equivalen a:", "dos mil gramos", "doscientos gramos", True),
        ("Medio kilogramo equivale a:", "quinientos gramos", "cincuenta gramos", True),
        # Casos cotidianos de conversión de monedas y temperaturas:
        ("Si tienes diez dólares y el tipo de cambio es tres coma setenta soles por dólar, obtendrás:", "treinta y siete soles", "treinta soles", True),
        ("Si el agua hierve a cien grados Celsius, ¿un clima de treinta y siete grados representa congelación?", "No, es una temperatura ambiental cálida", "Sí, el agua se hace hielo", True),
        ("Mililitros y litros son unidades de:", "capacidad", "temperatura", True),
    ]

def _statistics_questions() -> list[QuestionPayload]:
    return [
        ("En la lista estadística de valores dos, cuatro y seis. ¿Cuál es la media aritmética?", "cuatro", "cinco", True),
        ("En la lista uno, dos, dos y tres. ¿Cuál es la medida de la moda?", "dos", "tres", True),
        ("En la lista ordenada uno, tres y cinco. ¿Cuál es el valor de la mediana?", "tres", "cinco", True),
        ("En la lista cinco, cinco, siete y ocho. ¿Cuál es la moda?", "cinco", "siete", True),
        ("En la lista dos, cuatro, seis y ocho. ¿Cuál es el promedio aritmético?", "cinco", "seis", True),
        ("La moda es el valor estadístico que:", "más se repite", "menos se repite", True),
        ("La mediana es el valor central que queda:", "en el centro posicional", "al final de la lista", True),
        ("La media también se conoce en la vida cotidiana como:", "promedio", "porcentaje", True),
    ]