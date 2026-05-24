from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from exam.models import Exam, Question, QuestionOption, Topic, UserExamAttempt

User = get_user_model()


@override_settings(SECURE_SSL_REDIRECT=False)
class ExamEndpointsTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="exam_user@test.com", password="test1234"
        )
        self.client.force_authenticate(self.user)

        self.topic_math = Topic.objects.create(name="Matemática")
        self.topic_memory = Topic.objects.create(name="Memoria")

        self.exam_math = Exam.objects.create(
            topic=self.topic_math,
            title="Sumas básicas",
            description="Diagnóstico de sumas",
            difficulty=Exam.Difficulty.EASY,
            is_diagnostic=True,
            is_active=True,
        )
        self.exam_memory = Exam.objects.create(
            topic=self.topic_memory,
            title="Memoria secuencial",
            description="Entrenamiento de memoria",
            difficulty=Exam.Difficulty.MEDIUM,
            is_diagnostic=False,
            is_active=True,
        )

        self.question = Question.objects.create(
            exam=self.exam_math,
            title="Pregunta 1",
            question_text="¿Cuál es la capital de Francia?",
            spoken_instruction="Escucha la pregunta y elige una opción.",
            spoken_question="¿Cuál es la capital de Francia? Opción izquierda: París. Opción derecha: Londres.",
            spoken_feedback_correct="Respuesta correcta.",
            spoken_feedback_incorrect="Respuesta incorrecta.",
            order=1,
            is_active=True,
        )
        self.option_left = QuestionOption.objects.create(
            question=self.question,
            label="París",
            position=QuestionOption.Position.LEFT,
            is_correct=True,
            order=1,
        )
        QuestionOption.objects.create(
            question=self.question,
            label="Londres",
            position=QuestionOption.Position.RIGHT,
            is_correct=False,
            order=2,
        )

        self.question_exam_2 = Question.objects.create(
            exam=self.exam_memory,
            title="Pregunta 2",
            question_text="Recuerda la secuencia: 3-2-1",
            spoken_instruction="Escucha la secuencia y elige la opción correcta.",
            spoken_question="¿Cuál fue la secuencia correcta?",
            spoken_feedback_correct="Respuesta correcta.",
            spoken_feedback_incorrect="Respuesta incorrecta.",
            order=1,
            is_active=True,
        )
        QuestionOption.objects.create(
            question=self.question_exam_2,
            label="3-2-1",
            position=QuestionOption.Position.LEFT,
            is_correct=True,
            order=1,
        )
        QuestionOption.objects.create(
            question=self.question_exam_2,
            label="1-2-3",
            position=QuestionOption.Position.RIGHT,
            is_correct=False,
            order=2,
        )

    def test_get_questions(self) -> None:
        response = self.client.get(reverse("exam:questions"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("questions", response.data)
        self.assertGreaterEqual(len(response.data["questions"]), 1)

    def test_get_topics(self) -> None:
        response = self.client.get(reverse("exam:topics"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("topics", response.data)
        self.assertGreaterEqual(len(response.data["topics"]), 2)

    def test_get_exams(self) -> None:
        response = self.client.get(reverse("exam:exam-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("exams", response.data)
        self.assertGreaterEqual(len(response.data["exams"]), 2)

    def test_get_questions_by_exam(self) -> None:
        response = self.client.get(
            reverse("exam:exam-questions", kwargs={"exam_id": self.exam_math.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["questions"]), 1)
        self.assertEqual(response.data["questions"][0]["id"], str(self.question.id))

    def test_submit_answer(self) -> None:
        response = self.client.post(
            reverse("exam:submit-answer"),
            {
                "exam_id": str(self.exam_math.id),
                "question_id": str(self.question.id),
                "selected_option_id": str(self.option_left.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_correct"])

        attempt = UserExamAttempt.objects.get(user=self.user, exam=self.exam_math)
        self.assertEqual(attempt.score, 1)

    def test_submit_batch(self) -> None:
        response = self.client.post(
            reverse("exam:submit-batch"),
            {
                "exam_id": str(self.exam_math.id),
                "answers": [
                    {
                        "question_id": str(self.question.id),
                        "selected_option_id": str(self.option_left.id),
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("score", response.data)
        self.assertIn("percentage", response.data)

    def test_get_history(self) -> None:
        self.client.post(
            reverse("exam:submit-answer"),
            {
                "exam_id": str(self.exam_math.id),
                "question_id": str(self.question.id),
                "selected_option_id": str(self.option_left.id),
            },
            format="json",
        )

        response = self.client.get(reverse("exam:history"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("history", response.data)
        self.assertEqual(len(response.data["history"]), 1)

        item = response.data["history"][0]
        self.assertEqual(item["attempt_type"], "REINFORCEMENT")
        self.assertEqual(item["title"], f"Reforzamiento: {self.exam_math.title}")
        self.assertTrue(item["completed"])

    def test_get_history_detail(self) -> None:
        self.client.post(
            reverse("exam:submit-batch"),
            {
                "exam_id": str(self.exam_math.id),
                "answers": [
                    {
                        "question_id": str(self.question.id),
                        "selected_option_id": str(self.option_left.id),
                    }
                ],
            },
            format="json",
        )

        attempt = UserExamAttempt.objects.get(user=self.user, exam=self.exam_math)

        response = self.client.get(
            reverse("exam:history-detail", kwargs={"attempt_id": attempt.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["id"]), str(attempt.id))
        self.assertIn("answers", response.data)
        self.assertEqual(len(response.data["answers"]), 1)
        self.assertEqual(
            response.data["answers"][0]["question_id"],
            str(self.question.id),
        )
