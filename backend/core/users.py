"""
The union view over the two user tables.

Patients and physicians are separate tables because they are separate things
in the product, but the UI consumes a single flat list keyed by id.
"""

from __future__ import annotations

from core.dto import ApiUser, UserRole
from core.patients import get_patient_by_id, list_patients
from core.physicians import get_physician_by_id, list_physicians


def list_all_users() -> list[ApiUser]:
    """Every patient and physician, unioned as a flat ApiUser list."""
    return [*list_patients(), *list_physicians()]


def resolve_role(user_id: str) -> UserRole:
    """
    Resolve a user id to its role by checking patients, then physicians.

    Raises:
        ValueError: if the id belongs to neither table.
    """
    if get_patient_by_id(user_id):
        return "patient"
    if get_physician_by_id(user_id):
        return "physician"
    raise ValueError(f"unknown user id: {user_id}")
