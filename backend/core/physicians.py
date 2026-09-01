"""Read access to physicians, mapped to the ApiUser DTO."""

from __future__ import annotations

from core.dto import ApiUser
from core.models import Physician


def to_user(physician: Physician) -> ApiUser:
    return {"id": physician.id, "name": physician.name, "is_physician": True}


def list_physicians() -> list[ApiUser]:
    return [to_user(p) for p in Physician.objects.all()]


def get_physician_by_id(physician_id: str) -> ApiUser | None:
    physician = Physician.objects.filter(id=physician_id).first()
    return to_user(physician) if physician else None
