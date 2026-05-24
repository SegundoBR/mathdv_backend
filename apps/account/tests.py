from unittest.mock import MagicMock, patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User, UserProfile

# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class UserModelTest(TestCase):
    def test_create_user_sets_email_as_identifier(self) -> None:
        user = User.objects.create_user(
            email="test@example.com",
            firebase_uid="uid_model_1",
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(str(user), "test@example.com")
        self.assertFalse(user.has_usable_password())

    def test_user_profile_auto_created_via_signal(self) -> None:
        user = User.objects.create_user(
            email="profile@example.com",
            firebase_uid="uid_profile_1",
        )
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, UserProfile)

    def test_email_is_username_field(self) -> None:
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_full_name_property(self) -> None:
        user = User(first_name="Juan", last_name="Pérez")
        self.assertEqual(user.full_name, "Juan Pérez")

    def test_create_superuser(self) -> None:
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="securepassword123",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)


# ---------------------------------------------------------------------------
# View tests
# ---------------------------------------------------------------------------


class GoogleAuthViewTest(APITestCase):
    URL = "/api/account/auth/google/"

    def test_missing_id_token_returns_400(self) -> None:
        response = self.client.post(self.URL, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_id_token_returns_400(self) -> None:
        response = self.client.post(self.URL, {"id_token": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("account.views.verify_firebase_token")
    def test_invalid_firebase_token_returns_401(self, mock_verify: MagicMock) -> None:
        from account.services import FirebaseTokenError

        mock_verify.side_effect = FirebaseTokenError("Token inválido.")
        response = self.client.post(self.URL, {"id_token": "bad_token"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("account.views.get_or_create_user")
    @patch("account.views.verify_firebase_token")
    def test_valid_token_returns_jwt_and_user(
        self,
        mock_verify: MagicMock,
        mock_get_or_create: MagicMock,
    ) -> None:
        user = User.objects.create_user(
            email="auth@example.com",
            firebase_uid="uid_auth_1",
            first_name="Juan",
            last_name="Pérez",
        )
        mock_verify.return_value = {
            "uid": "uid_auth_1",
            "email": "auth@example.com",
            "name": "Juan Pérez",
            "picture": "",
        }
        mock_get_or_create.return_value = user

        response = self.client.post(
            self.URL, {"id_token": "valid_token"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("refresh_token", response.data)
        self.assertIn("user", response.data)

        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "auth@example.com")
        self.assertEqual(user_data["first_name"], "Juan")
        self.assertNotIn("password", user_data)
        self.assertNotIn("firebase_uid", user_data)
