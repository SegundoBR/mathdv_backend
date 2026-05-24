from __future__ import annotations

import logging

import firebase_admin
from django.conf import settings
from django.db import transaction
from firebase_admin import auth, credentials
from rest_framework.exceptions import AuthenticationFailed

from .models import StudentLoginActivity, User
from .selectors import get_user_by_email, get_user_by_firebase_uid

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Firebase initialization
# ---------------------------------------------------------------------------


def _get_firebase_app() -> firebase_admin.App:
    """
    Retorna la app de Firebase Admin SDK.
    La inicializa una sola vez usando las credenciales del archivo configurado.
    """
    try:
        return firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(str(settings.FIREBASE_CREDENTIALS_PATH))
        return firebase_admin.initialize_app(cred)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class FirebaseTokenError(AuthenticationFailed):
    """Excepción lanzada cuando el token de Firebase es inválido o ha expirado."""


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------


def verify_firebase_token(id_token: str) -> dict:
    """
    Verifica un Firebase ID Token enviado desde el frontend.

    Args:
        id_token: Token JWT emitido por Firebase Authentication.

    Returns:
        dict con uid, email, name y picture del usuario.

    Raises:
        FirebaseTokenError: Si el token es inválido, expirado o revocado.
    """
    _get_firebase_app()

    try:
        decoded = auth.verify_id_token(id_token, check_revoked=True)
    except auth.ExpiredIdTokenError:
        logger.warning("Firebase: token expirado.")
        raise FirebaseTokenError("El token de Firebase ha expirado.")
    except auth.RevokedIdTokenError:
        logger.warning("Firebase: token revocado.")
        raise FirebaseTokenError("El token de Firebase ha sido revocado.")
    except auth.CertificateFetchError as exc:
        logger.error("Firebase: error al obtener certificados: %s", exc)
        raise FirebaseTokenError("Error al verificar el token. Intenta de nuevo.")
    except auth.InvalidIdTokenError as exc:
        logger.warning("Firebase: token inválido: %s", exc)
        raise FirebaseTokenError("Token de Firebase inválido.")
    except Exception as exc:
        logger.exception("Firebase: error inesperado: %s", exc)
        raise FirebaseTokenError("Error al procesar la autenticación.")

    return {
        "uid": decoded["uid"],
        "email": decoded.get("email", ""),
        "name": decoded.get("name", ""),
        "picture": decoded.get("picture", ""),
    }


# ---------------------------------------------------------------------------
# User creation / retrieval
# ---------------------------------------------------------------------------


@transaction.atomic
def get_or_create_user(firebase_data: dict) -> User:
    """
    Busca un usuario por firebase_uid.
    - Si no existe: lo crea (el perfil se crea automáticamente via signal).
    - Si existe: actualiza sus datos básicos si cambiaron.

    Siempre retorna el usuario. El frontend nunca distingue si fue
    registro o login: el comportamiento es idéntico.

    Args:
        firebase_data: Diccionario con uid, email, name y picture.

    Returns:
        Instancia de User.
    """
    uid: str = firebase_data["uid"]
    email: str = firebase_data["email"]
    name: str = firebase_data.get("name", "")
    picture: str = firebase_data.get("picture", "")

    # Separar nombre y apellido
    name_parts = name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    user = get_user_by_firebase_uid(uid)

    if user is None:
        # Buscar por email por si ya existía con otro método
        user = get_user_by_email(email)

        if user is not None:
            # Vincular el firebase_uid al usuario existente
            user.firebase_uid = uid
            user.first_name = first_name
            user.last_name = last_name
            user.photo_url = picture
            user.provider = "google"
            user.set_unusable_password()
            user.save(
                update_fields=[
                    "firebase_uid",
                    "first_name",
                    "last_name",
                    "photo_url",
                    "provider",
                    "password",
                ]
            )
            logger.info("Usuario existente vinculado a Firebase: %s", email)
        else:
            # Crear usuario nuevo
            user = User(
                email=email,
                firebase_uid=uid,
                first_name=first_name,
                last_name=last_name,
                photo_url=picture,
                provider="google",
                role=User.Role.STUDENT,
            )
            user.set_unusable_password()
            user.save()
            logger.info("Nuevo usuario creado: %s", email)
    else:
        # Usuario existente: actualizar solo campos que cambiaron
        updated_fields: list[str] = []

        if user.first_name != first_name:
            user.first_name = first_name
            updated_fields.append("first_name")

        if user.last_name != last_name:
            user.last_name = last_name
            updated_fields.append("last_name")

        if picture and user.photo_url != picture:
            user.photo_url = picture
            updated_fields.append("photo_url")

        if updated_fields:
            user.save(update_fields=updated_fields)
            logger.debug("Usuario actualizado: %s — campos: %s", email, updated_fields)

    return user


def register_student_login_activity(*, user: User) -> None:
    if user.role != User.Role.STUDENT:
        return

    StudentLoginActivity.objects.create(
        user=user,
        source=StudentLoginActivity.Source.MOBILE_APP,
    )
