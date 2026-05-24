from __future__ import annotations

from typing import Optional

from .models import User


def get_user_by_firebase_uid(firebase_uid: str) -> Optional[User]:
    """Retorna un usuario por su Firebase UID o None si no existe."""
    return User.objects.filter(firebase_uid=firebase_uid).first()


def get_user_by_email(email: str) -> Optional[User]:
    """Retorna un usuario por su email o None si no existe."""
    return User.objects.filter(email=email).first()


def get_user_by_id(user_id) -> Optional[User]:
    """Retorna un usuario por su ID (UUID) o None si no existe."""
    return User.objects.filter(id=user_id).first()
